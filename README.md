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
