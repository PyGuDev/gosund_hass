# Local control: Gosund EP8

## Credentials

Private device values live only in the local (gitignored) file:

```text
.secrets/ep8.env
```

Expected keys: `DEVICE_ID`, `LOCAL_KEY`, `HOST`, `PORT`, `PROTOCOL`, `NAME`,
`MAC`, `PRODUCT_ID`. Do not commit that file or paste its values into docs.

| Field | Notes |
|---|---|
| Device ID | from `.secrets/ep8.env` |
| Host | EP8 LAN IP from `.secrets/ep8.env` |
| Port | `6668/TCP` |
| Protocol | `3.3` |
| MAC / Product ID | from `.secrets/ep8.env` |
| Local key | from `.secrets/ep8.env` |

## DPS map (from decrypted PCAP + live query)

| DPS | Type | Meaning |
|---:|---|---|
| `1` | bool | Main relay. `true` = ON, `false` = OFF |
| `9` | int | Countdown timer (seconds remaining; `0` = off) |
| `38` | enum/string | Observed `"memory"` (power-on behavior) |
| `39` | enum/string | Observed `"relay"` |
| `40` | bool | Observed `false` |
| `41`–`43` | string | Observed empty |

Captured session polarity:

1. `CONTROL_NEW` with `{"dps":{"1":false}}` → OFF  
2. `CONTROL_NEW` with `{"dps":{"1":true}}` → ON  

## Live verification

TinyTuya successfully read status and toggled DPS `1` on the EP8 LAN endpoint
using protocol 3.3 and the extracted `local_key`. Status after toggle matched the
command; the prior OFF state was restored.

```sh
set -a
source .secrets/ep8.env
set +a
python3 - <<'PY'
import json, tinytuya
d = tinytuya.OutletDevice(
    DEVICE_ID := __import__('os').environ['DEVICE_ID'],
    __import__('os').environ['HOST'],
    __import__('os').environ['LOCAL_KEY'],
    version=3.3,
)
print(json.dumps(d.status(), indent=2))
PY
```

## Home Assistant: LocalTuya (custom / HACS)

Example entity mapping (paste values from `.secrets/ep8.env`):

```yaml
localtuya:
  - host: "<HOST>"
    device_id: "<DEVICE_ID>"
    local_key: "<LOCAL_KEY>"
    friendly_name: EP8
    protocol_version: "3.3"
    entities:
      - platform: switch
        friendly_name: EP8
        id: 1
        # optional countdown sensor if desired:
      - platform: sensor
        friendly_name: EP8 Countdown
        id: 9
        scaling: 1
```

If using the UI-based LocalTuya integration instead of YAML:

1. Add device → IP, device id, local key, version `3.3` (from `.secrets/ep8.env`)
2. Add switch entity for DPS `1`
3. Optionally add sensor for DPS `9`

## tinytuya one-shot toggle

```sh
set -a; source .secrets/ep8.env; set +a
python3 - <<'PY'
import os, tinytuya
d = tinytuya.OutletDevice(
    os.environ['DEVICE_ID'], os.environ['HOST'], os.environ['LOCAL_KEY'], version=3.3
)
print(d.turn_on() if False else d.turn_off())  # flip as needed
print(d.status())
PY
```
