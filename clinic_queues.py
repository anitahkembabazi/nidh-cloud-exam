from zlib import crc32

import pika

QUEUE_NAMES = ("vaccinations.0", "vaccinations.1", "vaccinations.2")


def queue_for_child(child_id):
    index = crc32(child_id.encode("utf-8")) % len(QUEUE_NAMES)
    return QUEUE_NAMES[index]


if __name__ == "__main__":
    with pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as connection:
        channel = connection.channel()
        for name in QUEUE_NAMES:
            channel.queue_declare(
                queue=name,
                durable=True,
                arguments={"x-queue-type": "quorum"},
            )
            print(f"Queue ready: {name}")