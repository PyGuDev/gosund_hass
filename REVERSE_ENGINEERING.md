# Reverse engineering: GHome smart plug capture

Source capture: local PCAPdroid dump (path kept outside the repo; decrypt via
`.secrets/ep8.env`).

## Result

The GHome application is using the Tuya ecosystem and the Tuya LAN protocol.
The plug is directly reachable on the local network at `$HOST:6668/TCP`
(see `.secrets/ep8.env`). The captured LAN session uses protocol version **3.3**,
with `0x55AA` framing, AES-128-ECB payload encryption, and CRC32 integrity.

PCAPdroid captured the Android VPN-side address as `10.215.173.1`; this is the
phone/application endpoint, not the physical LAN address of the phone.

## Observed exchange

| Local time | Direction | Sequence | Command | Interpretation |
|---|---|---:|---:|---|
| 12:23:47.929 | app -> plug | `0x060b` | `0x10` | `DP_QUERY_NEW` |
| 12:23:47.939 | plug -> app | `0x060b` | `0x10` | encrypted query response |
| 12:23:48.129 | app -> plug | `0x060c` | `0x0d` | `CONTROL_NEW` |
| 12:23:48.167 | plug -> app | `0x0000` | `0x08` | updated encrypted status |
| 12:23:48.174 | plug -> app | `0x060c` | `0x0d` | success acknowledgement |
| 12:23:51.814 | app -> plug | `0x060d` | `0x0d` | `CONTROL_NEW` |
| 12:23:51.849 | plug -> app | `0x0000` | `0x08` | updated encrypted status |
| 12:23:51.857 | plug -> app | `0x060d` | `0x0d` | success acknowledgement |

Thus the capture contains two state-changing operations, most likely one ON and
one OFF action. Their exact polarity and Data Point number remain inside the
encrypted payload.

All observed CRC32 values validate. The control frames contain the clear 15-byte
`3.3` version header followed by 32 bytes of AES ciphertext. The status frames
contain 48 bytes of AES ciphertext. The acknowledgement return code is zero.

## Discovery and cloud infrastructure

The application sends a Tuya v3.5-style solicitation broadcast to
`255.255.255.255:7000/UDP` at roughly six-second intervals. The useful control
channel in this capture is nevertheless the v3.3 TCP channel above.

Observed service names include:

- `a1-eu.iot334.com` -> `165.154.143.244`
- `m1-eu.iot334.com` -> `45.195.222.93`
- `stream.tuyaeu.com` -> multiple AWS EU addresses

These cloud connections use TLS and cannot be decoded from this capture without
session keys or an application-side TLS interception setup.

## `local_key` extraction (resolved)

Tuya v3.3 uses a unique 16-byte `local_key`. It is not transmitted in cleartext
in this PCAP. It was recovered from a rooted Android 35 emulator running the
same GHome account:

1. AVD `ghome_ep8_android35` (`google_apis;arm64-v8a`) with `adb root`
2. Install GHome 5.8.5 via `adb install-multiple` (`base.apk` +
   `split_config.arm64_v8a.apk`)
3. After EP8 synced, `am dumpheap` on `com.gosund.smart`
4. Heap contained DeviceBean JSON with matching `devId` / MAC / name `EP8`

The key is stored only in `.secrets/ep8.env` (gitignored). Do not publish it.

Decrypt the capture:

```sh
set -a; source .secrets/ep8.env; set +a
python3 analyze_tuya_pcap.py \
  '<path-to-pcap>' \
  --local-key "$LOCAL_KEY"
```

## Decrypted DPS

Query response in the capture:

```json
{
  "dps": {
    "1": true,
    "9": 0,
    "38": "memory",
    "39": "relay",
    "40": false,
    "41": "",
    "42": "",
    "43": ""
  }
}
```

Control frames: DPS `1` `false` (OFF), then DPS `1` `true` (ON). Live TinyTuya
control on `$HOST:6668` confirmed the same mapping. See `LOCAL_CONTROL.md`.

## Protocol references

- [TinyTuya local protocol reference](https://github.com/jasonacox/tinytuya/blob/master/PROTOCOL.md)
- [Tuya SDK port reference](https://support.tuya.com/en/help/_detail/Kb6bjb8yyf1nf)
- [TuyaOpen LAN implementation](https://github.com/tuya/TuyaOpen/blob/master/src/tuya_cloud_service/lan/tuya_lan.c)
