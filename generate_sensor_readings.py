import json
from datetime import datetime, timedelta, timezone

import pika


SENSOR_QUEUE = "sensors.temperature"


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    readings = [(now - timedelta(minutes=1), 4.0), (now, 9.0)]

    with pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as connection:
        channel = connection.channel()
        channel.queue_declare(
            queue=SENSOR_QUEUE,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        channel.confirm_delivery()

        for timestamp, temperature in readings:
            reading = {
                "sensor_id": "SYN-FRIDGE-0002",
                "facility_id": "F0002",
                "ts": timestamp.isoformat(),
                "temp_c": temperature,
            }
            channel.basic_publish(
                exchange="",
                routing_key=SENSOR_QUEUE,
                body=json.dumps(reading).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
                mandatory=True,
            )
            print(f"Confirmed {temperature} C for {reading['sensor_id']}")


if __name__ == "__main__":
    main()
