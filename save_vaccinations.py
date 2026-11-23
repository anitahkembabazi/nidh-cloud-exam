from hashlib import sha256

import pika
import psycopg
from pydantic import ValidationError

from clinic_queues import QUEUE_NAMES
from ingest_api import Vaccination


DATABASE_URL = "postgresql://root@127.0.0.1:26257/nidh?sslmode=disable"


class WorkerVaccination(Vaccination):
    district_id: str | None = None
    facility_id: str | None = None


class VaccinationConflict(ValueError):
    pass


def store_dose(db, record):
    dose = (
        record.child_id,
        record.vaccine_code,
        record.dose_no,
        record.district_id,
        record.facility_id,
    )

    inserted = db.execute(
        """
        INSERT INTO vaccination_dose
            (record_id, child_id, vaccine_code, dose_no, district_id, facility_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING record_id
        """,
        (record.record_id, *dose),
    ).fetchone()

    if inserted is not None:
        return "Saved"

    existing = db.execute(
        """
        SELECT child_id, vaccine_code, dose_no, district_id, facility_id
        FROM vaccination_dose
        WHERE record_id = %s
        """,
        (record.record_id,),
    ).fetchone()

    if existing == dose:
        return "Already saved"

    if existing is None:
        raise VaccinationConflict(
            f"Dose for {record.child_id}, {record.vaccine_code}, "
            f"dose {record.dose_no} already exists under another record ID."
        )

    raise VaccinationConflict(
        f"Record ID {record.record_id} already exists with different vaccination data."
    )


def save_rejection(db, queue, body, reason):
    # Redelivery of the same rejected message should create only one rejection.
    reject_key = sha256(queue.encode("utf-8") + b"\0" + body).hexdigest()

    db.execute(
        """
        INSERT INTO rejected_message (reject_key, source_queue, raw_body, reason)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (reject_key) DO NOTHING
        """,
        (reject_key, queue, body, reason),
    )


def main():
    with (
        psycopg.connect(DATABASE_URL, autocommit=True) as db,
        pika.BlockingConnection(pika.ConnectionParameters("127.0.0.1")) as broker,
    ):
        channel = broker.channel()

        for queue in QUEUE_NAMES:
            while True:
                delivery, _, body = channel.basic_get(queue=queue, auto_ack=False)
                if delivery is None:
                    break

                with db.transaction():
                    try:
                        record = WorkerVaccination.model_validate_json(body)
                        outcome = store_dose(db, record)
                        message = f"{outcome} {record.record_id}"
                    except (ValidationError, VaccinationConflict) as error:
                        save_rejection(db, queue, body, str(error))
                        message = f"Rejected from {queue}: {error}"

                # CockroachDB has committed the dose or the rejection.
                channel.basic_ack(delivery_tag=delivery.delivery_tag)
                print(message)


if __name__ == "__main__":
    main()