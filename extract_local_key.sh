#!/usr/bin/env bash
# Extract Tuya local_key for EP8 from a rooted GHome emulator via heap dump.
# Real device identifiers are never hardcoded here — pass them or load from
# the local gitignored .secrets/ep8.env.
set -euo pipefail

EMU="${1:-emulator-5554}"
OUT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUMP_DIR="${OUT_DIR}/.secrets"
ENV_FILE="${DUMP_DIR}/ep8.env"
mkdir -p "$DUMP_DIR"
chmod 700 "$DUMP_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

DEVICE_ID="${2:-${DEVICE_ID:-}}"
if [[ -z "$DEVICE_ID" ]]; then
  echo "usage: $0 [emulator-serial] <device_id>" >&2
  echo "or set DEVICE_ID in .secrets/ep8.env" >&2
  exit 1
fi

HOST="${HOST:-192.0.2.10}"
MAC="${MAC:-02:00:00:00:00:01}"
MAC_COMPACT="$(printf '%s' "$MAC" | tr -d ':-' | tr '[:upper:]' '[:lower:]')"

export PATH="/opt/homebrew/share/android-commandlinetools/platform-tools:${PATH}"

adb -s "$EMU" root >/dev/null
adb -s "$EMU" wait-for-device >/dev/null

PID="$(adb -s "$EMU" shell pidof com.gosund.smart | tr -d '\r')"
if [[ -z "$PID" ]]; then
  echo "GHome is not running on $EMU" >&2
  exit 1
fi

echo "Dumping heap for pid $PID..."
adb -s "$EMU" shell "am dumpheap $PID /data/local/tmp/ghome.hprof"
adb -s "$EMU" pull /data/local/tmp/ghome.hprof "${DUMP_DIR}/ghome.hprof" >/dev/null

python3 - <<'PY' "$DUMP_DIR" "$DEVICE_ID" "$HOST" "$MAC" "$MAC_COMPACT"
import re, sys
from pathlib import Path

dump = Path(sys.argv[1])
device_id = sys.argv[2]
host = sys.argv[3]
mac = sys.argv[4]
mac_compact = sys.argv[5]
data = (dump / 'ghome.hprof').read_bytes()

# Prefer UTF-16LE JSON blobs (common in ART heaps)
u16_dev = device_id.encode('utf-16le')
keys = []
for m in re.finditer(re.escape(u16_dev), data):
    chunk = data[max(0, m.start() - 800) : m.start() + 1200]
    text = chunk.decode('utf-16le', errors='ignore')
    for km in re.finditer(r'"localKey"\s*:\s*"([^"]{8,64})"', text):
        keys.append(km.group(1))
    for km in re.finditer(r'"mac"\s*:\s*"([^"]+)"', text):
        pass

# ASCII fallback near DeviceRespBean fields
for m in re.finditer(rb'localKey!', data):
    chunk = data[m.start() : m.start() + 200]
    runs = re.findall(rb'[\x20-\x7e]{8,64}', chunk)
    for r in runs:
        s = r.decode()
        if s not in {'localKey!', 'setLocalKey!'} and 8 <= len(s) <= 32:
            keys.append(s)

# Dedup preserving order
seen, uniq = set(), []
for k in keys:
    if k not in seen:
        seen.add(k)
        uniq.append(k)

out = dump / 'local_key_candidates.txt'
out.write_text(''.join(k + '\n' for k in uniq))
if not uniq:
    print('No local_key found. Open EP8 in GHome, then rerun.')
    sys.exit(2)

print('Candidates:')
for k in uniq:
    print(' ', k)

mac_hit = (
    mac_compact.encode() in data
    or mac_compact.encode('utf-16le') in data
)
env = dump / 'ep8.env'
if len(uniq) == 1:
    env.write_text(
        f"DEVICE_ID={device_id}\n"
        f"LOCAL_KEY={uniq[0]}\n"
        f"HOST={host}\n"
        f"PORT=6668\n"
        f"PROTOCOL=3.3\n"
        f"NAME=EP8\n"
        f"MAC={mac}\n"
    )
    env.chmod(0o600)
    print(f'Wrote {env} (mac_seen={mac_hit})')
else:
    print(f'Wrote {out}; review before using.')
PY
