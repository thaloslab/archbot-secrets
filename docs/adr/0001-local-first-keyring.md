# ADR 0001: Local-First Keyring with Manifest Pointers

## Status
Accepted

## Context
The tool must be cross-platform, low-dependency, and avoid plaintext secret files while supporting agentic runtime routing.

## Decision
Store secret values only in OS key vault via `keyring`.
Store metadata and secret pointers in `~/.config/ai/ai_agents/manifest.json`.

## Consequences

### Positive

- Minimal ops complexity
- Works offline
- Native secure storage integration

### Negative

- Limited centralized audit in MVP
- Team-scale governance deferred to post-MVP phase
