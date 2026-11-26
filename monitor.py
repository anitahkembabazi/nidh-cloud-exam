"""Sample Milestone 3 pipeline health and counters as JSON lines."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
import time
from urllib.request import urlopen


def check_api():
    port = int(os.environ.get("NIDH_API_PORT", "8000"))
    base_url = f"http://127.0.0.1:{port}"
    with urlopen(f"{base_url}/health", timeout=3) as response:
        if response.status != 200 or json.load(response) != {"status": "ok"}:
            raise ValueError("Unexpected ingestion health response")
    with urlopen(f"{base_url}/metrics", timeout=3) as response:
        return {"batch_sync": json.load(response)}


def check_queues():
    import pika
    from clinic_queues import QUEUE_NAMES
    from generate_sensor_readings import SENSOR_QUEUE

    settings = pika.ConnectionParameters("127.0.0.1", socket_timeout=3, stack_timeout=5,
                                         blocked_connection_timeout=3)
    ready = {}
    with pika.BlockingConnection(settings) as connection:
        channel = connection.channel()
        for name in (*QUEUE_NAMES, SENSOR_QUEUE):
            result = channel.queue_declare(queue=name, passive=True)
            ready[name] = result.method.message_count
    return {"messages_ready": ready}


def check_database():
    import psycopg

    with psycopg.connect("postgresql://root@127.0.0.1:26257/nidh?sslmode=disable",
                         connect_timeout=3, options="-c statement_timeout=5000") as db:
        doses, rejects, readings, alerts = db.execute("""
            SELECT (SELECT count(*) FROM vaccination_dose),
                   (SELECT count(*) FROM rejected_message),
                   count(*), count(alert)
            FROM sensor_reading
        """).fetchone()
    return {"doses": doses, "rejected_messages": rejects,
            "sensor_readings": readings, "sensor_alerts": alerts}


def snapshot():
    sample = {"timestamp": datetime.now(timezone.utc).isoformat(), "ok": True}
    for name, check in (("api", check_api), ("rabbitmq", check_queues),
                        ("database", check_database)):
        started = time.monotonic()
        try:
            result = {"ok": True, **check()}
        except Exception as error:
            result = {"ok": False, "error": str(error) or type(error).__name__}
            sample["ok"] = False
        result["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
        sample[name] = result
    return sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, metavar="SECONDS",
                        help="wait this long after each sample and repeat until interrupted")
    interval = parser.parse_args().interval
    if interval is not None and (not math.isfinite(interval) or interval <= 0):
        parser.error("--interval must be a positive finite number")
    try:
        while True:
            sample = snapshot()
            print(json.dumps(sample), flush=True)
            if interval is None:
                return 0 if sample["ok"] else 1
            time.sleep(interval)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
