# National Immunisation Data Hub

This Milestone 3 prototype processes synthetic vaccination batches and fridge
temperature readings on a single PC using FastAPI, RabbitMQ, and CockroachDB.

## Verified behaviour

- Replaying a five-record vaccination batch left the district total at five doses.
- A conflicting record was saved to the reject table. The worker then processed
  the next valid record.
- Each of the three vaccination queues had an online replica on all three brokers.
- The vaccination table had voting replicas on all three database nodes.
- The sensor worker stored a 4 °C reading and recorded a mock alert for a 9 °C
  reading. The assumed temperature range for the demo was 2–8 °C.

Replication and resource measurements are in the `evidence` folder.

## Start on Windows

Open Docker Desktop with Linux containers and install Python 3.12 or 3.13 with the Windows py launcher. In PowerShell at the repository root run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

The launcher installs requirements in the local nidh-venv, starts three brokers and three database nodes and initializes their shared configuration, tables and partitions. Keep the terminal open for the API and workers. Reuse the same folder and Compose project name to retain your data. To stop, press Ctrl+C and run `docker compose stop --timeout 60`.

In a second PowerShell terminal run:

```powershell
$py = "$env:LOCALAPPDATA\nidh-venv\Scripts\python.exe"
& $py .\generate_batch.py
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/batch-sync -ContentType application/json -InFile .\demo-batch.json
& $py .\generate_sensor_readings.py
& $py .\monitor.py
```

Visit http://127.0.0.1:8000/dashboard with national / analyst-demo for all districts or district01 / clinic-demo for D001. The cached totals refresh within about 30 seconds after processing. Replay the same JSON file to demonstrate idempotency. Monitor reports confirmed records per second since API startup, successful acknowledgement latency, HTTP errors, ready queue depth and stored rejects. Use --interval 10 for repeated measurements.

## Durability and scale choices

HTTP 202 follows broker publisher confirms for every persistent record routed to a replicated quorum queue. Storage in CockroachDB follows asynchronously. Retry an unconfirmed batch with the same record IDs. Consumers acknowledge only after transaction commit. The database enforces uniqueness of both record ID and logical dose. Conflicting edits are recorded for review. The prototype uses the default SERIALIZABLE isolation. Eight primary-index ranges use a computed hash of child ID. Startup runs verify_partition.sql to check the range boundaries and constraints.

All six services share one PC for the small demo. Three vaccination queues replace the larger design's proposed sixteen. Node replication shares one physical failure domain. The local dashboard uses an in-process cache. Its synthetic coverage denominator is assumed to be 1,000 eligible children in each demonstration district. Only mock credentials and synthetic data belong here. Local traffic uses plaintext and database nodes run in insecure mode. Production would require TLS, authenticated services, separate zones, encrypted disks and encrypted backups with managed keys. Host-volume encryption depends on the Windows device configuration.

See CONTRIBUTIONS.md, AI_USE.md and THIRD_PARTY.md for authorship and attribution.
