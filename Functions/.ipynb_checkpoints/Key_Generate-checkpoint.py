#!/usr/bin/env python
# coding: utf-8

# In[ ]:
from qiskit import QuantumCircuit
from Functions.helpers import *
from Functions.Key_Generate import *
from Functions.Arithmetics import *
from Functions.Subnibble import *
from Functions.SwapRow_and_MixColumn import *

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

def compute_K1_quantum(qc, key_reg_base=0, workspace_base=32):
    """
    Correct, reversible quantum computation of K1 = B2 | B3
    using explicit nibbles and NO in-place affine transforms.
    """

    # -------------------------------
    # Key nibbles
    # -------------------------------
    B0_lo = [key_reg_base + i for i in range(0, 4)]
    B0_hi = [key_reg_base + i for i in range(4, 8)]

    B1_lo = [key_reg_base + i for i in range(8, 12)]
    B1_hi = [key_reg_base + i for i in range(12, 16)]

    # -------------------------------
    # Workspace nibbles
    # -------------------------------
    W0_lo = [workspace_base + i for i in range(0, 4)]    # will become B2_lo
    W0_hi = [workspace_base + i for i in range(4, 8)]    # will become B2_hi

    W1_lo = [workspace_base + i for i in range(8, 12)]   # affine output
    W1_hi = [workspace_base + i for i in range(12, 16)]  # affine output

    W2_lo = [workspace_base + i for i in range(16, 20)]  # inverse output
    W2_hi = [workspace_base + i for i in range(20, 24)]  # inverse output

    # =====================================================
    # Step 1: Copy B1 → W0
    # =====================================================
    for i in range(4):
        qc.cx(B1_lo[i], W0_lo[i])
        qc.cx(B1_hi[i], W0_hi[i])

    # =====================================================
    # Step 2: SubNibble(RotNibble(B1))
    # RotNibble = swap hi/lo logically
    # =====================================================

    # ---- LOW NIBBLE: input = W0_hi ----
    gf4_square(qc, W0_hi, W2_lo)
    gf4_square(qc, W2_lo, W2_hi)
    gf4_square(qc, W2_hi, W0_hi)
    gf4_multiply(qc, W0_hi, W2_hi, W2_lo)
    gf4_multiply(qc, W2_lo, W0_hi, W2_hi)   # W2_hi = inverse
    affine_transform(qc, W2_hi, W1_lo)      # affine → W1_lo

    # ---- HIGH NIBBLE: input = W0_lo ----
    gf4_square(qc, W0_lo, W2_lo)
    gf4_square(qc, W2_lo, W2_hi)
    gf4_square(qc, W2_hi, W0_lo)
    gf4_multiply(qc, W0_lo, W2_hi, W2_lo)
    gf4_multiply(qc, W2_lo, W0_lo, W2_hi)   # W2_hi = inverse
    affine_transform(qc, W2_hi, W1_hi)      # affine → W1_hi

    # =====================================================
    # Step 3: B2 = B0 ⊕ SubNibble(RotNibble(B1))
    # =====================================================
    for i in range(4):
        qc.cx(W1_lo[i], W0_lo[i])
        qc.cx(W1_hi[i], W0_hi[i])
        qc.cx(B0_lo[i], W0_lo[i])
        qc.cx(B0_hi[i], W0_hi[i])

    # =====================================================
    # Step 4: RCON1 = 1000 0000
    # =====================================================
    qc.x(W0_hi[3])  # MSB of byte

    # =====================================================
    # Step 5: B3 = B1 ⊕ B2   (stored in W1)
    # =====================================================
    for i in range(4):
        qc.cx(B1_lo[i], W1_lo[i])
        qc.cx(B1_hi[i], W1_hi[i])
        qc.cx(W0_lo[i], W1_lo[i])
        qc.cx(W0_hi[i], W1_hi[i])

    # RESULT:
    #   W0_lo | W0_hi = B2
    #   W1_lo | W1_hi = B3
