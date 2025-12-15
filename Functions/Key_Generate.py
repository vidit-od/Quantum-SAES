#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# S-AES S-box (nibble S-box)
SBOX = [
    0x9, 0x4, 0xA, 0xB,
    0xD, 0x1, 0x8, 0x5,
    0x6, 0x2, 0x0, 0x3,
    0xC, 0xE, 0xF, 0x7
]

# Round constants RCON(1)=10000000, RCON(2)=00110000
RCON = {
    1: 0x80,  # 1000 0000
    2: 0x30   # 0011 0000
}

def rot_nibbles(byte: int) -> int:
    return ((byte << 4) & 0xF0) | ((byte >> 4) & 0x0F)

def sub_nibbles(byte: int) -> int:
    hi = (byte >> 4) & 0xF
    lo = byte & 0xF
    return (SBOX[hi] << 4) | SBOX[lo]

def bits8(x: int) -> str:
    return format(x & 0xFF, "08b")

def generate_round_keys(secret_key_bits: str):
    """
    Input:  16-bit secret key as string, e.g. "0101010101010101"
    Output: [round0_key_16bits, round1_key_16bits, round2_key_16bits]
    """

    key = secret_key_bits.replace(" ", "")
    if len(key) != 16 or any(c not in "01" for c in key):
        raise ValueError("secret_key_bits must be a 16-bit bitstring")

    # Initial bytes
    B0 = int(key[:8],  2)
    B1 = int(key[8: ], 2)

    K = [0]*6
    K[0] = B0
    K[1] = B1

    # Generate B2..B5
    for i in range(2, 6):
        if i % 2 == 0:  # even
            rc = RCON[i // 2]
            temp = sub_nibbles(rot_nibbles(K[i-1]))
            K[i] = K[i-2] ^ rc ^ temp
        else:  # odd
            K[i] = K[i-2] ^ K[i-1]

    # Construct the 16-bit round keys
    round0 = bits8(K[0]) + bits8(K[1])
    round1 = bits8(K[2]) + bits8(K[3])
    round2 = bits8(K[4]) + bits8(K[5])

    return [round0, round1, round2]

