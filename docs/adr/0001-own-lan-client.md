# ADR 0001: Own LAN Client instead of LocalTuya / tinytuya

## Status

Accepted

## Context

EP8 is already reachable on the LAN with Tuya LAN 3.3. The operator wants a
Home Assistant Integration `gosund_ep8` that owns a short Direct LAN Session per
operation for Relay control (DPS 1 only). LocalTuya and tinytuya both speak the
same protocol, but pull in broader device/DPS abstractions and (for tinytuya) a
sync-oriented runtime that is not a natural fit for Home Assistant’s async path.

## Decision

Ship a minimal first-party LAN Client inside the Integration. It implements only
query Relay and set Relay over Tuya LAN 3.3 on TCP 6668. Do not depend on
tinytuya or LocalTuya at runtime.

## Consequences

- Home Assistant owns framing, AES-128-ECB, CRC32, and session lifecycle for this
  one device shape.
- Protocol regressions are caught by unit tests at the LAN Client seam using
  known-good capture vectors, without a live EP8.
- Extra DPS entities, discovery, and multi-device maps stay out of scope until a
  later ADR revisits the boundary.
- Contributors should not “fix” LocalTuya/tinytuya into this Integration without
  revisiting this decision.
