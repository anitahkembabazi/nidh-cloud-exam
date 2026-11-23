import json
import pika

with pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as connection:
    channel = connection.channel()
    delivery, _, body = channel.basic_get(
        queue="smoke.vaccinations",
        auto_ack=False,
    )

    if delivery is None:
        print("Queue is empty.")
    else:
        record = json.loads(body)
        print(f"Received {record['vaccine_code']} dose {record['dose_no']} "
              f"for {record['child_id']}")

        # Keep the message available until we have a database worker.
        channel.basic_nack(delivery_tag=delivery.delivery_tag, requeue=True)