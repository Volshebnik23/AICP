# Playbook: Agent Media and Brand Feeds

## Purpose
Describe governed channels/subscriptions/publications patterns for brand-to-agent and agent-to-agent feed distribution.

## Actor map
- Publisher/brand agent
- Mediator/channel host
- Subscriber agents
- Moderation/enforcement operators

## What runs where
- Channel governance and moderation run on host/platform side.
- Publication production may run on brand/content systems.
- AICP content-layer artifacts carry publication metadata, integrity references, and moderation-compatible records.

## Recommended AICP profile(s)
- Primary: `AICP-AGENT-MEDIA@0.1`
- Complementary: `AICP-BAZAAR-RECEPTION@0.1` for intake-heavy environments

## Required / optional extensions
- Required: per selected profile
- Optional: `EXT-CHANNELS`, `EXT-SUBSCRIPTIONS`, `EXT-PUBLICATIONS`, `EXT-INBOX`, `EXT-ALERTS`

## Adjacent protocols/services required
- Distribution infrastructure/CDN/notification systems
- Identity and channel access control systems
- Moderation and abuse-monitoring services

## Trust/privacy assumptions
- Publication correction/retraction handling must be auditable.
- Subscriber privacy and subscription metadata handling must follow platform policy.

## Out of scope for AICP
- CDN protocol design
- Ad-tech/recommendation engine internals
- Consumer identity provider internals

## Canonical flow references
- [AICP canonical flows](../flows/AICP_Canonical_Flows.md)
- [Enforcement models](../architecture/Enforcement_Models.md)

## Failure/rollback notes
- Maintain correction/retraction traceability in transcript artifacts.
- Preserve deterministic publication IDs/hashes across retries.
