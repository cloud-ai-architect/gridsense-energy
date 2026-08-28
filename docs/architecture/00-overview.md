# Architecture Overview

## Pipeline (high-level)

1. Input arrives (event, message, request)
2. Orchestrator Agent dispatches to specialized agents
3. Each agent uses tools to complete its task
4. Results are aggregated and returned

## Why this design

| Concern | Decision |
|---|---|
| Multi-agent | CrewAI / LangGraph for orchestration |
| AWS-native | Bedrock for inference, Lambda for compute |
| Cost-aware | S3 Vectors for embeddings, pay-per-use |
| Secure | OIDC, no long-lived credentials |

## See also

- [HLD](01-hld.md)
- [LLD](02-lld.md)
- [Security model](06-security-model.md)
