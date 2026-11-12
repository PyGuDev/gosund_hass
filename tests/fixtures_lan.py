"""Independent known-good Tuya LAN 3.3 frame vectors.

Ciphertexts were produced with OpenSSL AES-128-ECB (not the Integration client).
Plaintext expectations are literals from the protocol exchange shape.
"""

from __future__ import annotations

# Synthetic fixtures — not real device identifiers or secrets.
TEST_LOCAL_KEY = "0123456789abcdef"
TEST_DEVICE_ID = "bf00000000000000000001"
TEST_HOST = "192.0.2.10"

# Request that queries DPS (encrypted "{}").
QUERY_REQ_HEX = (
    "000055aa000000010000001000000018"
    "cb70ddc25a2a2045b4c13084418a9abb"
    "b97cd9ad0000aa55"
)

# Device DP_QUERY_NEW response: Relay on.
QUERY_RESP_ON_HEX = (
    "000055aa00000001000000100000002c00000000"
    "c27ee03f8be481e63320de7dc6eb4296"
    "eaa232ae24f922bc7c13d00b5180beaa"
    "eadd581e0000aa55"
)

# Device DP_QUERY_NEW response: Relay off.
QUERY_RESP_OFF_HEX = (
    "000055aa00000001000000100000002c00000000"
    "f24799fe0fff17cc9f964a40989b0d28"
    "7ccda3875adaa38a50474f433d13762a"
    "a1dec3da0000aa55"
)

# CONTROL_NEW requests (3.3 header + ciphertext), seq=1.
CTRL_OFF_REQ_HEX = (
    "000055aa000000010000000d00000037"
    "332e33000000000000000000000000"
    "f24799fe0fff17cc9f964a40989b0d28"
    "31836d84bd28cb4b20619eb84882ca2a"
    "f6f5b67d0000aa55"
)
CTRL_ON_REQ_HEX = (
    "000055aa000000010000000d00000037"
    "332e33000000000000000000000000"
    "c27ee03f8be481e63320de7dc6eb4296"
    "64215f365b0dad6b2ac8fab15b1d40bd"
    "8c33af570000aa55"
)

# STATUS + CONTROL_NEW ACK bundles (as a single TCP read).
STATUS_OFF_ACK_HEX = (
    "000055aa00000000000000080000003b00000000"
    "332e33000000000000000000000000"
    "f24799fe0fff17cc9f964a40989b0d28"
    "8d2a4fe78b939dbe41ed6815fd8061f0"
    "92ca6af30000aa55"
    "000055aa000000010000000d0000000c00000000"
    "302b238a0000aa55"
)
STATUS_ON_ACK_HEX = (
    "000055aa00000000000000080000003b00000000"
    "332e33000000000000000000000000"
    "c27ee03f8be481e63320de7dc6eb4296"
    "bbdeea9c517cd439d490f94c54adf71a"
    "8a9817490000aa55"
    "000055aa000000010000000d0000000c00000000"
    "302b238a0000aa55"
)

# ACK alone (retcode 0, no status body).
ACK_ONLY_HEX = "000055aa000000010000000d0000000c00000000302b238a0000aa55"

# Query response with undecryptable ciphertext.
BAD_DECRYPT_RESP_HEX = (
    "000055aa00000001000000100000001c00000000"
    "00000000000000000000000000000000"
    "39a69ab00000aa55"
)
