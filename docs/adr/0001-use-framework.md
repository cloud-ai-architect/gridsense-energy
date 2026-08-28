# ADR-0001: Use LangGraph as the primary agent framework

## Status: Accepted

## Context

GridSense is a multi-agent system. We need:
- Easy multi-agent orchestration
- Tool-calling
- AWS-native integration
- Cost-effective

## Decision

Use **LangGraph** as the primary orchestration framework, with Strands Agents / Bedrock AgentCore for AWS-native integration.

## Consequences

- Best multi-agent patterns in the industry
- AWS-native via Bedrock
- Easy to swap models
- Tool-calling built-in

## References

- [LangGraph docs](https://docs.LangGraph.com/)
- [Strands Agents](https://strandsagents.com/)
