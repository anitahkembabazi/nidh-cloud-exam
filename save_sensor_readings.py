import pika
import psycopg
from pydantic import AwareDatetime, BaseModel, Field, FiniteFloat

from generate_sensor_readings import SENSOR_QUEUE
from save_vaccinations import DATABASE_URL, save_rejection


class Reading(BaseModel):
    sensor_id: str = Field(pattern=r"^SYN-.+")
    facility_id: str = Field(pattern=r"^F[0-9]{4}$")
    ts: AwareDatetime
    temp_c: FiniteFloat


def store(db, reading):
    alert = None
    if reading.temp_c < 2 or reading.temp_c > 8:
        alert = "MOCK ALERT: temperature outside demo range"

    key = (reading.sensor_id, reading.ts)
    inserted = db.execute(
        "INSERT INTO sensor_reading (sensor_id, ts, facility_id, temp_c, alert) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING sensor_id",
        (*key, reading.facility_id, reading.temp_c, alert),
    ).fetchone()

    if inserted:
        return alert or "Saved"

    existing = db.execute(
        "SELECT facility_id, temp_c FROM sensor_reading WHERE sensor_id=%s AND ts=%s",
        key,
    ).fetchone()
    if existing != (reading.facility_id, reading.temp_c):
        raise ValueError("Conflicting readings for the same sensor and timestamp")
    return "Already saved"


def main():
    with (
        psycopg.connect(DATABASE_URL, autocommit=True) as db,
        pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as broker,
    ):
        db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_reading (
                sensor_id STRING NOT NULL,
                ts TIMESTAMPTZ NOT NULL,
                facility_id STRING NOT NULL,
                temp_c FLOAT8 NOT NULL,
                alert STRING,
                PRIMARY KEY (sensor_id, ts)
            )
        """)

        channel = broker.channel()
        channel.queue_declare(
            queue=SENSOR_QUEUE,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )

        while True:
            delivery, _, body = channel.basic_get(SENSOR_QUEUE, auto_ack=False)
            if delivery is None:
                break

            with db.transaction():
                try:
                    reading = Reading.model_validate_json(body)
                    outcome = store(db, reading)
                    result = f"{outcome} | {reading.sensor_id} | {reading.temp_c} C"
                except ValueError as error:
                    save_rejection(db, SENSOR_QUEUE, body, str(error))
                    result = f"Rejected sensor reading: {error}"

            channel.basic_ack(delivery.delivery_tag)
            print(result)


if __name__ == "__main__":
    main()
