"""Bootstrap the local demonstration, then run its API and workers."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pika
import psycopg

from clinic_queues import QUEUE_NAMES
from generate_sensor_readings import SENSOR_QUEUE
import save_sensor_readings
import save_vaccinations

ROOT = Path(__file__).resolve().parent
BROKERS = {f"rabbit@rabbit{n}" for n in (1, 2, 3)}
COMPOSE = ["docker", "compose"]
SQL = COMPOSE + ["exec", "-T", "db1", "cockroach", "sql", "--insecure", "--host=db1:26257"]


def initialize_database():
    deadline = time.monotonic() + 120
    init = COMPOSE + ["exec", "-T", "db1", "cockroach", "init", "--insecure", "--host=db1:26257"]
    while True:
        try:
            result = subprocess.run(init, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or "already been initialized" in result.stderr:
                break
            reason = result.stderr.strip()
        except subprocess.TimeoutExpired:
            reason = "database node did not respond"
        if time.monotonic() >= deadline:
            sys.exit(f"Could not initialize CockroachDB: {reason}")
        time.sleep(2)
    for filename in ("schema.sql", "read_audit.sql", "partition.sql", "verify_partition.sql"):
        script = (ROOT / filename).read_text(encoding="utf-8-sig")
        subprocess.run(SQL, input=script.encode(), check=True)


def initialize_queues():
    status = COMPOSE + ["exec", "-T", "rabbit1", "rabbitmqctl", "-q",
                        "--formatter", "json", "cluster_status"]
    deadline = time.monotonic() + 180
    while True:
        try:
            result = subprocess.run(status, capture_output=True, text=True, timeout=12)
            if result.returncode == 0 and BROKERS == set(json.loads(result.stdout)["running_nodes"]):
                break
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        if time.monotonic() >= deadline:
            sys.exit("Three brokers did not form a cluster. Inspect: docker compose logs rabbit1 rabbit2 rabbit3")
        time.sleep(3)
    while True:
        try:
            with pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as broker:
                channel = broker.channel()
                for queue in (*QUEUE_NAMES, SENSOR_QUEUE):
                    channel.queue_declare(queue=queue, durable=True, arguments={"x-queue-type": "quorum"})
            return
        except pika.exceptions.AMQPConnectionError as error:
            if time.monotonic() >= deadline:
                raise
            print(f"Waiting for quorum queues: {error}", flush=True)
            time.sleep(3)


def start_pipeline():
    os.chdir(ROOT)
    os.environ.setdefault("COMPOSE_FILE", os.pathsep.join((
        "compose.yaml", "compose.override.yaml", "compose.rabbit-bootstrap.yaml")))
    port = int(os.environ.get("NIDH_API_PORT", "8000"))
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            sys.exit(f"Port {port} is busy. Stop the old API with Ctrl+C, then retry.")
    subprocess.run(COMPOSE + ["up", "-d"], check=True)
    initialize_database()
    initialize_queues()
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "ingest_api:app", "--port", str(port)])
    try:
        while api.poll() is None:
            try:
                save_vaccinations.main()
                save_sensor_readings.main()
            except (pika.exceptions.AMQPConnectionError, psycopg.OperationalError) as error:
                print(f"Worker connection interrupted. Retrying: {error}", flush=True)
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
