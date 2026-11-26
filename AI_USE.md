# Milestone 3 AI-use declaration

**KEMBABAZI ANITAH · 26 November 2026**

I used OpenAI ChatGPT and Codex while building the National Immunisation Data Hub prototype. ChatGPT provided code and commands for Docker Compose, RabbitMQ queues, the ingestion API, vaccination and sensor workers, synthetic data generation, and the district dashboard and its access controls. I used its guidance to run these components in VS Code and PowerShell and to troubleshoot startup, port, validation and Git errors.

Codex prepared changes for the review branch, including the startup scripts, broker configuration, database partitioning and verification SQL, monitoring code, dashboard coverage display and documentation. It also ran integration checks in a separate Linux environment. I used the review branch on my Windows PC and supplied my own terminal output to check the results.

My personal verification included starting the Windows pipeline, checking that the vaccination queues had three online RabbitMQ replicas, and measuring five additional stored doses after a batch upload. The Windows observations are recorded in my contribution statement. Codex also helped draft both declarations from the project history and the checks I reported. [Student contribution](CONTRIBUTIONS.md)
