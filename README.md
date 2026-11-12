# Gosund EP8

Home Assistant Integration for local Relay control of a Gosund EP8 over Tuya
LAN 3.3. No GHome cloud and no LocalTuya dependency.

## Install (HACS)

1. HACS → Integrations → Custom repositories
2. Add this repository as category **Integration**
3. Install **Gosund EP8**
4. Restart Home Assistant
5. Settings → Devices & services → Add Integration → **Gosund EP8**

## Setup

Enter:

- Host (EP8 LAN IP)
- Device id
- Local Key (kept as a secret field)
- Poll interval seconds (default `30`)

Setup queries the Relay once. If the EP8 does not answer, Config Entry creation
fails with a clear error.

## What you get

- Device Registry name: **Gosund EP8**
- One `switch` entity for the Relay (DPS 1)
- Polling on the configured interval
- Options Flow to change host / device id / Local Key / poll interval later

Local Key must never be committed to git. Keep it in the Home Assistant Config
Entry (or operator secrets outside the repo).

## Requirements

Home Assistant 2024.1.0 or newer.
