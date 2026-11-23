import json
import random
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

now = datetime.now(timezone.utc).isoformat()
records = []

# Simulate one clinic uploading doses for five different synthetic children.
for child_number in random.sample(range(1_000_000), 5):
    record = {
        "record_id": str(uuid4()),
        "child_id": f"SYN-{child_number:010d}",
        "facility_id": "F0002",
        "district_id": "D002",
        "vaccine_code": "BCG",
        "dose_no": 1,
        "batch_no": "SYN-LOT-002",
        "device_id": "SYN-TABLET-002",
        "administered_at": now,
        "device_ts": now,
        "payload": "",
    }

    # Annex B calls for approximately 1 KB per vaccination record.
    size = len(json.dumps(record).encode("utf-8"))
    record["payload"] = "x" * max(0, 1024 - size)
    records.append(record)

batch = {"batch_id": str(uuid4()), "records": records}
output = Path(__file__).with_name("demo-batch.json")
output.write_text(json.dumps(batch, indent=2), encoding="utf-8")
print(f"Created {output.name} with {len(records)} synthetic vaccinations for D002.")