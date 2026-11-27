"""Run one paced E1 repetition. Give each repetition its own --out directory."""
import argparse
import csv
import json
import math
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

import pika
import psycopg

from generate_sensor_readings import SENSOR_QUEUE
from save_vaccinations import DATABASE_URL

RECORD_RATE = 30.55
SENSOR_RATE = 2.65
BATCH_SIZE = 5


def now():
    return datetime.now(timezone.utc).isoformat()


def pace(deadline):
    time.sleep(max(0, deadline - time.monotonic()))


def metrics(attempted, confirmed, errors, latencies, elapsed):
    samples = sorted(latencies)
    return {
        "attempted": attempted, "confirmed": confirmed,
        "attempted_per_second": attempted / elapsed,
        "confirmed_per_second": confirmed / elapsed,
        "error_fraction": (attempted - confirmed) / attempted if attempted else None,
        "errors_by_request": dict(errors),
        "successful_request_latency_ms": {
            f"p{p}": samples[math.ceil(len(samples) * p / 100) - 1] if samples else None
            for p in (50, 95, 99)
        },
    }


def batch(children, first, count, index, hot):
    # One in five batches comes from a D001 tablet. Rotate within both pools.
    tablet = 1 + index // 5 % 22 if hot else 23 + (index - index // 5 - 1) % 90
    stamp = now()
    records = []
    for i in range(first, first + count):
        record = {
            "record_id": str(uuid4()), "child_id": children[i],
            "vaccine_code": "OPV", "dose_no": 1,
            "batch_no": f"SYN-LOT-{tablet:03d}", "device_id": f"SYN-TABLET-{tablet:03d}", "facility_id": f"F{tablet:04d}",
            "district_id": "D001" if hot else f"D{2 + (tablet - 23) % 7:03d}",
            "administered_at": stamp, "device_ts": stamp, "payload": "",
        }
        record["payload"] = "x" * (1024 - len(json.dumps(record).encode()))
        records.append(record)
    return {"batch_id": str(uuid4()), "records": records}


def vaccinations(start, seconds, children, url, sent, ack):
    errors = Counter()
    latencies = []
    confirmed = 0
    total = math.floor(seconds * RECORD_RATE)
    first = index = hot_sent = 0
    hot_target = total // 5
    def send(payload, ids):
        req = Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
        begin = time.monotonic()
        with urlopen(req, timeout=10) as response:
            reply = json.load(response)
            if (response.status != 202 or reply.get("confirmed") != len(ids)
                        or reply.get("batch_id") != payload["batch_id"]):
                raise ValueError("incomplete acknowledgement")
        return now(), (time.monotonic() - begin) * 1000

    def collect(done):
        nonlocal confirmed
        for future in done:
            ids = pending.pop(future)
            try:
                stamp, latency = future.result()
            except (OSError, HTTPException, ValueError, AttributeError) as exc:
                errors[str(exc)] += 1
                continue
            csv.writer(ack).writerows((stamp, rid) for rid in ids)
            ack.flush()
            latencies.append(latency)
            confirmed += len(ids)

    pending = {}
    with ThreadPoolExecutor(max_workers=8) as clients:
        while first < total:
            pace(start + first / RECORD_RATE)
            hot = index % 5 == 0 and hot_sent < hot_target
            available = hot_target - hot_sent if hot else total - first - (hot_target - hot_sent)
            count = min(BATCH_SIZE, available)
            payload = batch(children, first, count, index, hot)
            first += count
            index += 1
            if hot:
                hot_sent += count
            ids = [record["record_id"] for record in payload["records"]]
            if len(pending) >= 8:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                collect(done)
            stamp = now()
            csv.writer(sent).writerows((stamp, rid) for rid in ids)
            sent.flush()
            pending[clients.submit(send, payload, ids)] = ids
        collect(list(pending))
    return total, confirmed, errors, latencies


def sensors(start, seconds, channel):
    total = math.floor(seconds * SENSOR_RATE)
    errors = Counter()
    latencies = []
    for i in range(total):
        pace(start + i / SENSOR_RATE)
        facility = i % 160 + 1
        reading = {"facility_id": f"F{facility:04d}", "sensor_id": f"SYN-FRIDGE-{facility:04d}",
                   "ts": now(), "temp_c": 4.0}
        begin = time.monotonic()
        try:
            channel.basic_publish(exchange="", routing_key=SENSOR_QUEUE, mandatory=True,
                                  body=json.dumps(reading).encode(),
                                  properties=pika.BasicProperties(content_type="application/json",
                                                                  delivery_mode=2))
        except pika.exceptions.AMQPError as exc:
            errors[type(exc).__name__] += 1
        else:
            latencies.append((time.monotonic() - begin) * 1000)
    return total, len(latencies), errors, latencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--url", default="http://127.0.0.1:8000/batch-sync")
    args = parser.parse_args()
    if args.seconds <= 0 or args.seconds * RECORD_RATE >= 10**10:
        parser.error("--seconds exceeds the supported positive run duration")
    args.out.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid4())
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as db:
        used = {row[0] for row in db.execute("SELECT child_id FROM vaccination_dose WHERE vaccine_code='OPV' AND dose_no=1")}
        needed = math.floor(args.seconds * RECORD_RATE)
        children = []
        for i in range(1_000_000):
            child = f"SYN-{i:010d}"
            if child not in used:
                children.append(child)
            if len(children) == needed:
                break
        if len(children) < needed:
            parser.error("insufficient unused logical doses in the synthetic child pool")
        rows = db.execute("SELECT record_id FROM vaccination_dose ORDER BY record_id")
        with (args.out / "before.txt").open("x") as before:
            before.writelines(f"{rid}\n" for (rid,) in rows)

    with (pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1",
                                                           blocked_connection_timeout=10)) as broker,
          (args.out / "sent.csv").open("x", newline="") as sent,
          (args.out / "ack.csv").open("x", newline="") as ack,
          ThreadPoolExecutor(max_workers=1) as pool):
        channel = broker.channel()
        channel.queue_declare(queue=SENSOR_QUEUE, durable=True, arguments={"x-queue-type": "quorum"})
        channel.confirm_delivery()
        for log in (sent, ack):
            csv.writer(log).writerow(("timestamp", "record_id"))
            log.flush()
        start = time.monotonic()
        job = pool.submit(vaccinations, start, args.seconds, children, args.url, sent, ack)
        readings = sensors(start, args.seconds, channel)
        doses = job.result()
        pace(start + args.seconds)
        elapsed = time.monotonic() - start
    report = {"run_id": run_id, "seconds": args.seconds, "max_inflight_batches": 8, "elapsed_seconds": elapsed,
              "vaccinations": metrics(*doses, elapsed), "sensors": metrics(*readings, elapsed)}
    summary = json.dumps(report, indent=2)
    (args.out / "summary.json").write_text(summary + "\n")
    print(summary)


if __name__ == "__main__":
    main()
