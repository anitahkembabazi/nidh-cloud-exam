import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pika
import psycopg

import clinic_queues
import save_sensor_readings
import save_vaccinations


COMPOSE = ["docker", "compose", "-f", "compose.yaml", "-f", "compose.override.yaml"]
SERVICES = {"db1", "db2", "db3", "rabbit1", "rabbit2", "rabbit3"}


def start_pipeline():
    os.chdir(Path(__file__).resolve().parent)

    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            sys.exit("Port 8000 is busy. Press Ctrl+C in the old Uvicorn terminal, then retry.")

    subprocess.run(COMPOSE + ["start"], check=True)
    output = subprocess.check_output(
        COMPOSE + ["ps", "--services", "--status", "running"], text=True
    )
    missing = SERVICES - set(output.split())
    if missing:
        sys.exit("Missing running containers: " + ", ".join(sorted(missing)))

    print("Waiting for CockroachDB and RabbitMQ...", flush=True)
    deadline = time.monotonic() + 120
    while True:
        try:
            with psycopg.connect(save_vaccinations.DATABASE_URL, connect_timeout=3) as db:
                db.execute("SELECT 1")
            with pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as broker:
                channel = broker.channel()
                for name in clinic_queues.QUEUE_NAMES:
                    channel.queue_declare(
                        queue=name, durable=True, arguments={"x-queue-type": "quorum"}
                    )
            break
        except (psycopg.OperationalError, pika.exceptions.AMQPConnectionError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(3)

    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "ingest_api:app", "--port", "8000"]
    )
    try:
        while api.poll() is None:
            save_vaccinations.main()
            save_sensor_readings.main()
            time.sleep(3)
        if api.returncode:
            sys.exit(api.returncode)
    finally:
        if api.poll() is None:
            api.terminate()
            api.wait()


if __name__ == "__main__":
    try:
        start_pipeline()
    except KeyboardInterrupt:
        pass
