# Milestone 4 experiment log

## E1 baseline on the Windows workstation

Start the existing Milestone 3 pipeline first. Use an otherwise idle pipeline, drain earlier messages and keep the same Docker project name. The reconciliation compares snapshots and assumes the generator is the only writer. Leave existing database volumes in place. Use a separate output directory for every run. Record the Git revision, available disk, workstation memory, Docker limits and whether the load generator shares the machine.

Selected divisor (assumed): k = 20, the lightest Annex A profile, because the student reported 7.9 GiB system memory and a 3.783 GiB Docker limit. Calculated vaccination rate: 611/20 = 30.55 records/s. Calculated sensor rate: 53/20 = 2.65 readings/s. Each ten-minute run targets 18,330 vaccinations and 1,590 sensor readings. Three runs target 54,990 vaccinations in total. Reserve space for SQL ranges and replicated queues as well as the evidence logs. Check free space between runs.

Use the short practice run to verify both streams, resource sampling, acknowledgement logs and reconciliation. For assessed E1, run three 600-second repetitions with the same settings. Record achieved rates, sample counts, p50/p95/p99 successful batch acknowledgement times, error rate, peak CPU/memory, and missing, phantom and duplicate counts for each run. Report all three values and their spread. Compare achieved throughput against offered load and examine backlog before interpreting latency. Label observations Measured, extrapolations Calculated, and hardware/scaling choices Assumed.

## Later experiments

E2 applies the 5/15/10-minute campaign profile then step-stress. E3 mixes 200 dashboard users with ingestion. E4 tests at least three faults including F1 or F5. E5 rolls a component under baseline load. E6 exercises replay and concurrent edits. Annex C also requires 20 acknowledgement-boundary durability trials. Complete reconciliation, the scaling model, the before/after optimisation and the supervised demonstration as specified in the exam.

## AI-use log for this stage

Codex drafted the baseline generator, resource sampler, reconciliation utility and experiment instructions. Record the exact revision you used, any changes you made, how you verified the outputs and your own interpretation when writing the submission.
