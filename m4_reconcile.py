"""Reconcile a completed vaccination run. Stop producers and leave workers running."""
import argparse
from collections import Counter, defaultdict
import csv
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parent
VACCINATION_QUEUES = {f"vaccinations.{i}" for i in range(3)}


def manifest(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if (reader.fieldnames or []).count("record_id") != 1:
            raise ValueError(f"{path.name} requires a record_id column")
        return Counter(str(UUID(row["record_id"].strip())) for row in reader)


def compose_exec(args, timeout):
    result = subprocess.run(["docker", "compose", "exec", "-T", *args], cwd=ROOT,
                            capture_output=True, encoding="utf-8", timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"{args[1]} failed ({result.returncode})")
    return result.stdout


def wait_for_drain(timeout, report):
    deadline = time.monotonic() + timeout
    while (remaining := deadline - time.monotonic()) > 0:
        output = compose_exec(["rabbit1", "rabbitmqctl", "-q", "--formatter", "json",
                               "list_queues", "name", "messages_ready",
                               "messages_unacknowledged"], remaining)
        queues = {}
        for row in json.loads(output):
            name = row["name"]
            if name in VACCINATION_QUEUES:
                counts = {key: row[key] for key in ("messages_ready", "messages_unacknowledged")}
                if name in queues or any(type(n) is not int or n < 0 for n in counts.values()):
                    raise ValueError(f"Invalid queue status for {name}")
                queues[name] = counts
        report["queues"] = queues
        if queues.keys() == VACCINATION_QUEUES and all(not any(q.values()) for q in queues.values()):
            return
        time.sleep(max(0, min(1, deadline - time.monotonic())))
    raise TimeoutError("Timed out waiting for all vaccination queues to drain")


def reconcile(directory, timeout, report):
    before = {str(UUID(line.strip())) for line in
              (directory / "before.txt").read_text(encoding="utf-8-sig").splitlines() if line.strip()}
    sent = manifest(directory / "sent.csv")
    ack = manifest(directory / "ack.csv")
    wait_for_drain(timeout, report)

    columns = ["record_id", "child_id", "vaccine_code", "dose_no"]
    output = compose_exec(["db1", "cockroach", "sql", "--insecure", "--host=db1:26257",
                           "--database=nidh", "--format=csv", "--execute",
                           "SELECT record_id, child_id, vaccine_code, dose_no FROM vaccination_dose"],
                          60)
    rows = csv.reader(io.StringIO(output, newline=""), strict=True)
    if next(rows, None) != columns:
        raise ValueError("Unexpected database result header")
    stored = Counter()
    doses = defaultdict(list)
    for record, child, vaccine, dose in rows:
        record = str(UUID(record))
        stored[record] += 1
        doses[child, vaccine, int(dose)].append(record)

    new = stored.keys() - before
    scope = new | sent.keys() | ack.keys()
    duplicates = [dict(child_id=child, vaccine_code=vaccine, dose_no=dose, record_ids=sorted(ids))
                  for (child, vaccine, dose), ids in sorted(doses.items())
                  if len(ids) > 1 and scope.intersection(ids)]
    failures = {
        "lost": sorted(ack.keys() - stored.keys()),
        "phantom": sorted(new - sent.keys()),
        "ack_without_send": sorted(ack.keys() - sent.keys()),
        "missing_baseline": sorted(before - stored.keys()),
        "duplicate_record_ids": sorted(i for i in scope if stored[i] > 1),
        "logical_duplicates": duplicates,
    }
    report.update(failures, ok=not any(failures.values()), sent=len(sent), acknowledged=len(ack),
                  send_attempts=sum(sent.values()), ack_entries=sum(ack.values()), new_stored=len(new),
                  sent_without_ack=sorted(sent.keys() - ack.keys()),
                  stored_without_ack=sorted(sent.keys() & stored.keys() - ack.keys()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--timeout", type=float, default=120, help="queue drain deadline in seconds")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive and finite")
    report = {"ok": False}
    try:
        reconcile(args.run_directory, args.timeout, report)
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError, csv.Error,
            KeyError, TypeError, AttributeError) as error:
        report["error"] = str(error)
    path = args.run_directory / "reconciliation.json"
    try:
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        print(error, file=sys.stderr)
        return 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
