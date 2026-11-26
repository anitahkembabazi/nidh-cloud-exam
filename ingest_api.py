from collections import Counter
from threading import Lock
from time import monotonic

import pika
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, UUID4
from clinic_queues import queue_for_child
from district_dashboard import router as dashboard_router

app = FastAPI(title="NIDH Clinic Ingestion")
app.include_router(dashboard_router)


class BatchMetrics:
    def __init__(self):
        self.lock = Lock()
        self.started = monotonic()
        self.records = 0
        self.successes = 0
        self.ack_seconds = 0.0
        self.errors = Counter()

    def observe(self, status, elapsed, records):
        with self.lock:
            if status == 202:
                self.records += records
                self.successes += 1
                self.ack_seconds += elapsed
            elif status >= 400:
                self.errors[status] += 1

    def snapshot(self):
        with self.lock:
            window = monotonic() - self.started
            return {
                "window": "since_process_start",
                "window_seconds": window,
                "confirmed_records": self.records,
                "records_per_second": self.records / window if window else 0.0,
                "successful_batches": self.successes,
                "mean_successful_ack_ms": (
                    1000 * self.ack_seconds / self.successes if self.successes else None
                ),
                "http_error_count": self.errors.total(),
                "http_errors_by_status": dict(self.errors),
            }


batch_metrics = BatchMetrics()


@app.middleware("http")
async def measure_batch(request: Request, call_next):
    if request.method != "POST" or request.url.path != "/batch-sync":
        return await call_next(request)

    started = monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        batch_metrics.observe(status, monotonic() - started,
                              getattr(request.state, "confirmed_records", 0))


@app.get("/metrics")
def metrics():
    return batch_metrics.snapshot()


@app.get("/health")
def health():
    return {"status": "ok"}


class Vaccination(BaseModel):
    # Keep additional clinic fields such as facility_id and timestamps.
    model_config = ConfigDict(extra="allow")

    record_id: UUID4
    child_id: str = Field(pattern=r"^SYN-[0-9]{10}$")
    vaccine_code: str
    dose_no: int = Field(ge=1, le=3)


class Batch(BaseModel):
    batch_id: UUID4
    records: list[Vaccination] = Field(min_length=1, max_length=500)


@app.post("/batch-sync", status_code=202)
def sync_batch(batch: Batch, request: Request):
    try:
        settings = pika.ConnectionParameters(
            host="127.0.0.1",
            blocked_connection_timeout=5,
        )
        with pika.BlockingConnection(settings) as connection:
            channel = connection.channel()
            channel.confirm_delivery()

            for record in batch.records:
                channel.basic_publish(
                    exchange="",
                    routing_key=queue_for_child(record.child_id),
                    body=record.model_dump_json().encode("utf-8"),
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        delivery_mode=2,
                        message_id=str(record.record_id),
                        correlation_id=str(batch.batch_id),
                    ),
                    mandatory=True,
                )
    except pika.exceptions.AMQPError as error:
        raise HTTPException(
            status_code=503,
            detail="Batch unconfirmed. Retry with the same record IDs.",
        ) from error

    request.state.confirmed_records = len(batch.records)
    return {"batch_id": str(batch.batch_id), "confirmed": len(batch.records)}
