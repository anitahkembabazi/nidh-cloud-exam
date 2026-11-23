import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, UUID4
from clinic_queues import queue_for_child
from district_dashboard import router as dashboard_router

app = FastAPI(title="NIDH Clinic Ingestion")
app.include_router(dashboard_router)


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
def sync_batch(batch: Batch):
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

    return {"batch_id": str(batch.batch_id), "confirmed": len(batch.records)}