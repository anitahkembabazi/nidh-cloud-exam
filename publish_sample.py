import json
import pika

record = {
    "record_id": "2efc793b-5194-4fc2-a5a8-8b3ff6d72a91",
    "child_id": "SYN-0000000002",
    "vaccine_code": "OPV",
    "dose_no": 1,
}

with pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as connection:
    channel = connection.channel()
    channel.confirm_delivery()

    channel.basic_publish(
        exchange="",
        routing_key="smoke.vaccinations",
        body=json.dumps(record).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
            message_id=record["record_id"],
        ),
        mandatory=True,
    )

    print(f"RabbitMQ confirmed record {record['record_id']}")