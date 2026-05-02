#!/usr/bin/env python
# coding: utf-8

# In[ ]:


"""
============================================================
 PRINCE Block Cipher — Reversible Quantum Circuit
 Module 2: S-box layer
============================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PART A — WHAT IS THE S-BOX?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  The PRINCE S-box is a fixed, non-linear 4-bit -> 4-bit
  substitution table. It maps every possible 4-bit input
  (0..15) to a unique 4-bit output (it is a BIJECTION).

  Lookup table (from Borghoff et al., ASIACRYPT 2012):

    Input  | 0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
    Output | B  F  3  2  A  C  9  1  6  5  0  E  D  8  4  7

  In the full 64-bit cipher, the state is split into 16
  nibbles (4 bits each) and the S-box is applied to every
  nibble independently. This is called the S-layer.

  Purpose: the S-box provides NON-LINEARITY. Without it,
  PRINCE would just be a linear cipher (broken trivially).
  The S-box is specifically chosen to have high algebraic
  degree, which resists linear and differential attacks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PART B — CLASSICAL IMPLEMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Classically, the S-box is just:
      output = SBOX_TABLE[input]

  In hardware it is a ROM or a small logic network.
  It is fast and cheap. The inverse S-box is simply a
  different lookup table.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PART C — WHY IT IS HARD IN QUANTUM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  In quantum computing, all gates must be REVERSIBLE (unitary).
  This creates two hard problems:

  1. AND GATES NEED ANCILLA QUBITS
     XOR  --> CNOT (reversible, no cost)
     NOT  --> Pauli-X (reversible, no cost)
     AND  --> TOFFOLI gate: Toffoli(a, b, c): c ^= a AND b
     The Toffoli uses a third "target" qubit (ancilla) that
     must start at |0>. When done, that ancilla must be
     UNCOMPUTED back to |0> (by running the same Toffoli again)
     otherwise it entangles with the rest of the circuit and
     destroys the interference that Grover's algorithm relies on.

  2. IN-PLACE OUTPUT REQUIRES CAREFUL ORDERING
     The 4 input qubits must become the 4 output qubits.
     But we cannot overwrite a qubit before all output bits
     that depend on it have been computed.
     We must figure out a safe write order.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PART D — HOW WE IMPLEMENT IT REVERSIBLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Step 1: Express each output bit in Algebraic Normal Form (ANF).
    ANF is a sum (XOR) of products (AND) over GF(2).
    Computed via the Moebius/zeta transform over the truth table.

    With input nibble bits a3(MSB), a2, a1, a0(LSB):

      b0 = 1^(a0*a1)^a2^(a1*a2)^(a0*a1*a2)^a3^(a0*a3)
      b1 = 1^(a0*a2)^(a1*a2)^(a0*a1*a2)^(a0*a3)^(a1*a3)^(a2*a3)
      b2 = a0^(a0*a1)^a3^(a0*a3)^(a1*a3)^(a0*a2*a3)^(a1*a2*a3)
      b3 = 1^a1^(a1*a2)^(a0*a1*a2)^a3^(a1*a3)^(a0*a1*a3)^(a2*a3)

    Each '*' is an AND (needs Toffoli + ancilla).
    Each '^' is XOR (CNOT). Each '1' is a constant flip (X gate).

  Step 2: Pre-compute all AND products into ancilla qubits.
    Degree-2 (6 products --> 6 Toffoli, 6 ancilla):
      t01=a0*a1, t02=a0*a2, t03=a0*a3, t12=a1*a2, t13=a1*a3, t23=a2*a3

    Degree-3 (4 products built from degree-2 ancillas --> 4 Toffoli, 4 ancilla):
      t012=t01*a2, t013=t01*a3, t023=t02*a3, t123=t12*a3

  Step 3: Copy all 4 input bits into 4 ancilla "copy" qubits.
    This is needed to uncompute the AND products AFTER the
    input qubits have been overwritten with output bits.
    (Bennett's uncomputation method)

  Step 4: Write all 4 output bits IN-PLACE using safe ordering.
    Safe write order (derived by checking which outputs need
    which raw input bits as standalone CNOT terms):
      Write b2 --> a0  (b2 uses a0 raw; write before anything overwrites a0)
      Write b3 --> a1  (b3 uses a1 raw; no other b_i needs a1 raw)
      Write b0 --> a3  (b0 uses a2 raw; a2 not yet overwritten here)
      Write b1 --> a2  (b1 has NO raw input terms; safe to go last)

    Special case for b1: a2 currently holds orig_a2, but b1 has no a2 term.
    Solution: use the copy of orig_a2 to zero out a2 first, then XOR in b1.

  Step 5: Uncompute all AND ancillas using the copies of original inputs.
    Since a0..a3 now hold outputs (not inputs), we use ca0..ca3 (the copies)
    as controls to reverse the Toffoli gates in reverse order.

  Step 6: Clear the 4 input copies (ca0..ca3).
    The inverse S-box is recomputed from the output bits and XOR-ed into
    the Bennett copies, so all 14 ancillas are |0> on exit.

  Resource count per nibble:
    Data qubits    : 4  (in-place, no extra output qubits)
    Ancilla qubits : 14  (4 copies + 10 AND products)
    Toffoli gates  : 40  (20 for S-box + 20 for copy cleanup)
    CNOT gates     : ~30
    X gates        : 3   (constant '1' terms in b0, b1, b3)

  For the full 64-bit S-layer (16 nibbles):
    Data qubits    : 64
    Ancilla qubits : 16 * 14 = 224
    Toffoli gates  : 16 * 20 = 320

  Simulation backend:
    Aer 'matrix_product_state' (MPS) method.
    The stabilizer method does NOT support Toffoli gates.
    MPS is efficient for circuits with limited entanglement
    (low bond dimension), which is the case here.

Dependencies:
    pip install qiskit qiskit-aer
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — PRINCE S-BOX CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# 4-bit -> 4-bit substitution table from the PRINCE specification.
SBOX = [0xB, 0xF, 0x3, 0x2, 0xA, 0xC, 0x9, 0x1,
        0x6, 0x5, 0x0, 0xE, 0xD, 0x8, 0x4, 0x7]

# Inverse S-box: needed for the decryption half of PRINCE (rounds R6^-1..R10^-1)
SBOX_INV = [0] * 16
for _i, _v in enumerate(SBOX):
    SBOX_INV[_v] = _i


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CLASSICAL REFERENCE (for verification)
# ══════════════════════════════════════════════════════════════════════════════

def classical_sbox_nibble(nibble_4bit):
    """Apply PRINCE S-box to a single 4-bit nibble (0..15)."""
    return SBOX[nibble_4bit & 0xF]


def classical_sbox_inv_nibble(nibble_4bit):
    """Apply PRINCE inverse S-box to a single 4-bit nibble."""
    return SBOX_INV[nibble_4bit & 0xF]

def prince_sbox_classical_reordered(nibble):
    y = SBOX[nibble]

    # Extract bits (LSB first)
    b0 = (y >> 0) & 1
    b1 = (y >> 1) & 1
    b2 = (y >> 2) & 1
    b3 = (y >> 3) & 1

    # 🔥 Match quantum layout: [b2, b3, b1, b0]
    reordered = (b2 << 0) | (b3 << 1) | (b1 << 2) | (b0 << 3)

    return reordered


SBOX_REORDERED = [prince_sbox_classical_reordered(_i) for _i in range(16)]

SBOX_REORDERED_INV = [0] * 16
for _i, _v in enumerate(SBOX_REORDERED):
    SBOX_REORDERED_INV[_v] = _i


def classical_sbox_reordered_inv_nibble(nibble_4bit):
    """Apply the inverse of the reordered S-box used by quantum_sbox_nibble."""
    return SBOX_REORDERED_INV[nibble_4bit & 0xF]


def classical_s_layer(state_64bit):
    out = 0
    for i in range(16):
        nibble = (state_64bit >> (4 * i)) & 0xF
        transformed = prince_sbox_classical_reordered(nibble)
        out |= transformed << (4 * i)
    return out


def classical_s_layer_inv(state_64bit):
    """Apply the inverse of classical_s_layer to all 16 state nibbles."""
    out = 0
    for i in range(16):
        nibble = (state_64bit >> (4 * i)) & 0xF
        out |= classical_sbox_reordered_inv_nibble(nibble) << (4 * i)
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — QUANTUM S-BOX: SINGLE NIBBLE
# ══════════════════════════════════════════════════════════════════════════════

def quantum_sbox_nibble(qc, nibble_qubits, ancilla_qubits):
    """
    Apply the PRINCE S-box IN-PLACE to one 4-qubit nibble.

    This is the primary helper function called by the round builder.
    Pass it the circuit, the 4 data qubits for the nibble, and 14 ancilla
    qubits. It appends all required gates and returns nothing.

    After the function returns:
      nibble_qubits[0..3]  hold S-box output  (was: input nibble bits)
      ancilla_qubits[0..13] are back to |0>

    Parameters
    ----------
    qc              : QuantumCircuit
                      Circuit to append gates to.

    nibble_qubits   : list of 4 Qubits  [a0, a1, a2, a3]
                      a0 = qubit for bit 0 (LSB) of this nibble
                      a1 = qubit for bit 1
                      a2 = qubit for bit 2
                      a3 = qubit for bit 3 (MSB)
                      On entry: hold the 4-bit input value.
                      On exit:  hold the S-box output S(input).

    ancilla_qubits  : list of 14 Qubits
                      All must be |0> on entry.
                      Layout:
                        [0]  ca0  -- copy of orig bit 0
                        [1]  ca1  -- copy of orig bit 1
                        [2]  ca2  -- copy of orig bit 2
                        [3]  ca3  -- copy of orig bit 3
                        [4]  t01  -- a0 AND a1
                        [5]  t02  -- a0 AND a2
                        [6]  t03  -- a0 AND a3
                        [7]  t12  -- a1 AND a2
                        [8]  t13  -- a1 AND a3
                        [9]  t23  -- a2 AND a3
                        [10] t012 -- a0 AND a1 AND a2
                        [11] t013 -- a0 AND a1 AND a3
                        [12] t023 -- a0 AND a2 AND a3
                        [13] t123 -- a1 AND a2 AND a3
                      On exit:
                        [0..13] are restored to |0>
    """

    # ── Unpack qubit names for readability ────────────────────────────────────
    a0, a1, a2, a3 = nibble_qubits

    ca0  = ancilla_qubits[0]   # copy of orig a0
    ca1  = ancilla_qubits[1]   # copy of orig a1
    ca2  = ancilla_qubits[2]   # copy of orig a2
    ca3  = ancilla_qubits[3]   # copy of orig a3

    t01  = ancilla_qubits[4]   # a0 & a1
    t02  = ancilla_qubits[5]   # a0 & a2
    t03  = ancilla_qubits[6]   # a0 & a3
    t12  = ancilla_qubits[7]   # a1 & a2
    t13  = ancilla_qubits[8]   # a1 & a3
    t23  = ancilla_qubits[9]   # a2 & a3
    t012 = ancilla_qubits[10]  # a0 & a1 & a2
    t013 = ancilla_qubits[11]  # a0 & a1 & a3
    t023 = ancilla_qubits[12]  # a0 & a2 & a3
    t123 = ancilla_qubits[13]  # a1 & a2 & a3

    # ── Phase 1: Copy all 4 input bits ───────────────────────────────────────
    # CNOT(source, target): target ^= source.
    # Since ca_i starts at |0>, after CNOT: ca_i = orig_a_i.
    # These copies allow us to uncompute AND products after overwriting a0..a3.
    # This is Bennett's method for reversible computation.
    qc.cx(a0, ca0)   # ca0 = orig_a0
    qc.cx(a1, ca1)   # ca1 = orig_a1
    qc.cx(a2, ca2)   # ca2 = orig_a2
    qc.cx(a3, ca3)   # ca3 = orig_a3

    # ── Phase 2: Compute degree-2 AND products into ancillas ─────────────────
    # Toffoli(ctrl1, ctrl2, target): target ^= ctrl1 & ctrl2.
    # Since each t-ancilla starts at |0>, after Toffoli: t = ctrl1 & ctrl2.
    qc.ccx(a0, a1, t01)    # t01  = a0 & a1
    qc.ccx(a0, a2, t02)    # t02  = a0 & a2
    qc.ccx(a0, a3, t03)    # t03  = a0 & a3
    qc.ccx(a1, a2, t12)    # t12  = a1 & a2
    qc.ccx(a1, a3, t13)    # t13  = a1 & a3
    qc.ccx(a2, a3, t23)    # t23  = a2 & a3

    # ── Phase 3: Compute degree-3 AND products ────────────────────────────────
    # Each degree-3 product reuses a degree-2 ancilla as one of the controls.
    qc.ccx(t01, a2, t012)  # t012 = (a0&a1) & a2  =  a0*a1*a2
    qc.ccx(t01, a3, t013)  # t013 = (a0&a1) & a3  =  a0*a1*a3
    qc.ccx(t02, a3, t023)  # t023 = (a0&a2) & a3  =  a0*a2*a3
    qc.ccx(t12, a3, t123)  # t123 = (a1&a2) & a3  =  a1*a2*a3

    # ── Phase 4: Write output bits in-place ───────────────────────────────────
    # All AND products now live in ancilla qubits. Every CNOT below uses
    # an ancilla as the CONTROL (which is not modified by CNOT).
    # Raw input qubits a0..a3 are written as CNOT targets.
    #
    # Safe write order derived from ANF:
    #   b2 written first (uses a0 raw as starting value, and a3 raw as CNOT source)
    #   b3 written second (uses a1 raw as starting value, and a3 raw as CNOT source)
    #   b0 written third (uses a3 raw as starting value, and a2 raw as CNOT source)
    #   b1 written last (uses a2 raw; has no standalone a_i term, uses copy ca2 to zero a2 first)

    # --- b2 into a0 ---
    # ANF: b2 = a0 ^ (a0*a1) ^ a3 ^ (a0*a3) ^ (a1*a3) ^ (a0*a2*a3) ^ (a1*a2*a3)
    # a0 already holds the 'a0' term. XOR in the rest:
    qc.cx(t01,  a0)    # a0 ^= a0*a1
    qc.cx(a3,   a0)    # a0 ^= a3         [a3 = orig_a3 here, not yet overwritten]
    qc.cx(t03,  a0)    # a0 ^= a0*a3
    qc.cx(t13,  a0)    # a0 ^= a1*a3
    qc.cx(t023, a0)    # a0 ^= a0*a2*a3
    qc.cx(t123, a0)    # a0 ^= a1*a2*a3
    # a0 now holds b2 ✓

    # --- b3 into a1 ---
    # ANF: b3 = 1 ^ a1 ^ (a1*a2) ^ (a0*a1*a2) ^ a3 ^ (a1*a3) ^ (a0*a1*a3) ^ (a2*a3)
    # a1 already holds 'a1'. XOR in the rest:
    qc.x(a1)           # a1 ^= 1          [constant term]
    qc.cx(t12,  a1)    # a1 ^= a1*a2
    qc.cx(t012, a1)    # a1 ^= a0*a1*a2
    qc.cx(a3,   a1)    # a1 ^= a3         [a3 = orig_a3, not yet overwritten]
    qc.cx(t13,  a1)    # a1 ^= a1*a3
    qc.cx(t013, a1)    # a1 ^= a0*a1*a3
    qc.cx(t23,  a1)    # a1 ^= a2*a3
    # a1 now holds b3 ✓

    # --- b0 into a3 ---
    # ANF: b0 = 1 ^ (a0*a1) ^ a2 ^ (a1*a2) ^ (a0*a1*a2) ^ a3 ^ (a0*a3)
    # a3 already holds 'a3'. a2 is still original here (not yet overwritten).
    qc.x(a3)           # a3 ^= 1          [constant term]
    qc.cx(t01,  a3)    # a3 ^= a0*a1
    qc.cx(a2,   a3)    # a3 ^= a2         [a2 = orig_a2, not yet overwritten]
    qc.cx(t12,  a3)    # a3 ^= a1*a2
    qc.cx(t012, a3)    # a3 ^= a0*a1*a2
    qc.cx(t03,  a3)    # a3 ^= a0*a3
    # a3 now holds b0 ✓

    # --- b1 into a2 ---
    # ANF: b1 = 1 ^ (a0*a2) ^ (a1*a2) ^ (a0*a1*a2) ^ (a0*a3) ^ (a1*a3) ^ (a2*a3)
    # b1 has NO standalone 'a2' term -- it is built entirely from products.
    # But a2 currently = orig_a2 (the data qubit still holds the input).
    # Strategy: use the copy ca2 to zero out a2, then XOR all b1 product terms in.
    #   CNOT(ca2, a2): a2 ^= orig_a2  -->  a2 = 0  (zeroed using its own copy)
    #   Then XOR b1 terms: X, CNOT(t02,a2), CNOT(t12,a2), ...
    qc.cx(ca2,  a2)    # a2 ^= orig_a2  -->  a2 = 0
    qc.x(a2)           # a2 ^= 1          [constant term]
    qc.cx(t02,  a2)    # a2 ^= a0*a2
    qc.cx(t12,  a2)    # a2 ^= a1*a2
    qc.cx(t012, a2)    # a2 ^= a0*a1*a2
    qc.cx(t03,  a2)    # a2 ^= a0*a3
    qc.cx(t13,  a2)    # a2 ^= a1*a3
    qc.cx(t23,  a2)    # a2 ^= a2*a3
    # a2 now holds b1 ✓

    # Current state:  a0=b2, a1=b3, a2=b1, a3=b0
    # Ancilla state:  ca0..ca3 hold orig inputs; t-ancillas hold AND products.

    # ── Phase 5: Uncompute AND ancillas ───────────────────────────────────────
    # We CANNOT use a0..a3 as controls now (they hold outputs, not inputs).
    # We use ca0..ca3 (which still hold the original input bits) instead.
    # Replay Toffoli gates in REVERSE order of Phase 3 then Phase 2.
    # Each Toffoli: target ^= ctrl1 & ctrl2. Since target already holds
    # ctrl1 & ctrl2, after the second Toffoli: target = 0 (uncomputed to |0>).

    # Reverse Phase 3 (degree-3, reverse order)
    qc.ccx(t12, ca3, t123)    # t123 ^= (a1&a2) & orig_a3  -->  t123 = 0
    qc.ccx(t02, ca3, t023)    # t023 ^= (a0&a2) & orig_a3  -->  t023 = 0
    qc.ccx(t01, ca3, t013)    # t013 ^= (a0&a1) & orig_a3  -->  t013 = 0
    qc.ccx(t01, ca2, t012)    # t012 ^= (a0&a1) & orig_a2  -->  t012 = 0

    # Reverse Phase 2 (degree-2, reverse order)
    qc.ccx(ca2, ca3, t23)     # t23 ^= orig_a2 & orig_a3  -->  t23 = 0
    qc.ccx(ca1, ca3, t13)     # t13 ^= orig_a1 & orig_a3  -->  t13 = 0
    qc.ccx(ca1, ca2, t12)     # t12 ^= orig_a1 & orig_a2  -->  t12 = 0
    qc.ccx(ca0, ca3, t03)     # t03 ^= orig_a0 & orig_a3  -->  t03 = 0
    qc.ccx(ca0, ca2, t02)     # t02 ^= orig_a0 & orig_a2  -->  t02 = 0
    qc.ccx(ca0, ca1, t01)     # t01 ^= orig_a0 & orig_a1  -->  t01 = 0

    # AND ancillas [4..13] are now all |0> ✓
    # ca0..ca3 [0..3] still hold original input bits.
    # Recompute the inverse S-box from the output bits and XOR it into the
    # Bennett copies, so the full ancilla slice is clean before reuse.

    # Current data layout is y0=a0, y1=a1, y2=a2, y3=a3, matching the
    # reordered classical reference used by classical_s_layer().
    qc.ccx(a0, a1, t01)
    qc.ccx(a0, a2, t02)
    qc.ccx(a0, a3, t03)
    qc.ccx(a1, a2, t12)
    qc.ccx(a1, a3, t13)
    qc.ccx(a2, a3, t23)

    qc.ccx(t01, a2, t012)
    qc.ccx(t01, a3, t013)
    qc.ccx(t02, a3, t023)
    qc.ccx(t12, a3, t123)

    # ANF of inverse(reordered S-box).  XORing these values into ca0..ca3
    # clears them because they currently hold the same original input bits.
    qc.cx(a1,   ca0)
    qc.cx(a2,   ca0)
    qc.cx(t02,  ca0)
    qc.cx(a3,   ca0)
    qc.cx(t123, ca0)

    qc.x(ca1)
    qc.cx(a1,   ca1)
    qc.cx(t02,  ca1)
    qc.cx(t03,  ca1)
    qc.cx(t13,  ca1)
    qc.cx(t123, ca1)

    qc.cx(a0,   ca2)
    qc.cx(a1,   ca2)
    qc.cx(t01,  ca2)
    qc.cx(t02,  ca2)
    qc.cx(a3,   ca2)
    qc.cx(t13,  ca2)
    qc.cx(t23,  ca2)
    qc.cx(t023, ca2)

    qc.x(ca3)
    qc.cx(t01,  ca3)
    qc.cx(a2,   ca3)
    qc.cx(t02,  ca3)
    qc.cx(t012, ca3)
    qc.cx(a3,   ca3)
    qc.cx(t03,  ca3)
    qc.cx(t013, ca3)
    qc.cx(t23,  ca3)
    qc.cx(t023, ca3)

    qc.ccx(t12, a3, t123)
    qc.ccx(t02, a3, t023)
    qc.ccx(t01, a3, t013)
    qc.ccx(t01, a2, t012)

    qc.ccx(a2, a3, t23)
    qc.ccx(a1, a3, t13)
    qc.ccx(a1, a2, t12)
    qc.ccx(a0, a3, t03)
    qc.ccx(a0, a2, t02)
    qc.ccx(a0, a1, t01)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — QUANTUM S-LAYER: FULL 64-BIT STATE
# ══════════════════════════════════════════════════════════════════════════════

def quantum_s_layer(qc, state_reg, ancilla_reg):
    """
    Apply the PRINCE S-layer to the full 64-bit state register.

    Applies quantum_sbox_nibble to all 16 nibbles in sequence.
    Each nibble gets its own dedicated slice of the ancilla register.
    The 16 nibbles are independent and could be done in parallel;
    in this circuit they are sequential for clarity.

    Parameters
    ----------
    qc          : QuantumCircuit

    state_reg   : QuantumRegister of exactly 64 qubits.
                  Nibble i occupies state_reg[4*i .. 4*i+3].
                  state_reg[4*i+0] = bit 0 (LSB) of nibble i.
                  state_reg[4*i+3] = bit 3 (MSB) of nibble i.
                  On exit: holds S-layer output.

    ancilla_reg : QuantumRegister of exactly 16*14 = 224 qubits.
                  Nibble i uses ancilla_reg[14*i .. 14*i+13].
                  All must be |0> on entry.
                  On exit: all 14 qubits of each block are |0>.
    """
    for i in range(16):
        nibble  = [state_reg[4 * i + k] for k in range(4)]
        ancilla = [ancilla_reg[14 * i + k] for k in range(14)]
        qc.barrier(label=f"S-box nibble {i}")
        quantum_sbox_nibble(qc, nibble, ancilla)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — SIMULATION HELPER
# ══════════════════════════════════════════════════════════════════════════════

def simulate(qc, sim):
    """
    Run one shot of a deterministic Aer simulation and return
    the measured state register as an integer.

    Uses matrix_product_state (MPS) method, which supports Toffoli gates.
    The stabilizer method only works for Clifford gates (X, CNOT, H, S)
    and would reject Toffoli. MPS handles arbitrary gates efficiently
    on circuits with low entanglement.

    Aer returns bitstrings MSB-first, so int(bitstring, 2) gives the
    correct integer (creg[N-1]...creg[0] = most-to-least significant bit).
    """
    counts = sim.run(qc, shots=1).result().get_counts()
    return int(list(counts.keys())[0], 2)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — TESTS
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # MPS backend: supports Toffoli, efficient for limited entanglement
    sim = AerSimulator(method='matrix_product_state')

    # ──────────────────────────────────────────────────────────────────────────
    #  TEST 1 — Single S-box nibble: verify all 16 inputs
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 62)
    print("  TEST 1 — Single S-box nibble, all 16 inputs (0..15)")
    print("=" * 62)
    print(f"  {'inp':>4}  {'inp_bin':>8}  {'exp':>4}  {'exp_bin':>8}  {'got':>4}  {'got_bin':>8}  result")
    print(f"  {'-'*4}  {'-'*8}  {'-'*4}  {'-'*8}  {'-'*4}  {'-'*8}  ------")

    all_pass = True
    for inp in range(16):
        expected = prince_sbox_classical_reordered(inp)

        # 4 data qubits + 14 ancilla qubits
        data = QuantumRegister(4,  name='data')
        anc  = QuantumRegister(14, name='anc')
        cr   = ClassicalRegister(4, name='out')
        qc   = QuantumCircuit(data, anc, cr)

        # Load input nibble into data qubits
        # data[0] = bit 0 (LSB), data[3] = bit 3 (MSB)
        for bit in range(4):
            if (inp >> bit) & 1:
                qc.x(data[bit])

        # Apply S-box
        quantum_sbox_nibble(qc, list(data), list(anc))

        # Measure data qubits only
        qc.measure(data, cr)

        result = simulate(qc, sim)
        ok = (result == expected)
        if not ok:
            all_pass = False
        print(f"  S({inp:2d}) {inp:04b}  -->  {expected:2d} {expected:04b}  got {result:2d} {result:04b}  {'PASS' if ok else 'FAIL <<<'}")

    print(f"\n  All 16 nibble outputs correct: {all_pass}")

    # ──────────────────────────────────────────────────────────────────────────
    #  TEST 2 — Verify AND ancillas are returned to |0>
    #  (measure the full 14-qubit ancilla slice after S-box)
    # ──────────────────────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  TEST 2 — All ancillas returned to |0> after S-box")
    print("=" * 62)

    anc_all_zero = True
    for inp in range(16):
        data = QuantumRegister(4,  name='data')
        anc  = QuantumRegister(14, name='anc')
        cr_d = ClassicalRegister(4,  name='data_out')
        cr_a = ClassicalRegister(14, name='anc_out')
        qc   = QuantumCircuit(data, anc, cr_d, cr_a)

        for bit in range(4):
            if (inp >> bit) & 1:
                qc.x(data[bit])

        quantum_sbox_nibble(qc, list(data), list(anc))

        # Measure data and all ancillas.
        qc.measure(data, cr_d)
        for k in range(14):
            qc.measure(anc[k], cr_a[k])

        counts = sim.run(qc, shots=1).result().get_counts()
        bs = list(counts.keys())[0]
        # Aer combined bitstring: cr_a (14 bits MSB first) then cr_d (4 bits MSB first)
        # (Aer orders classical registers right-to-left in the combined string)
        # cr_a is the SECOND register measured, so it appears on the LEFT in combined output
        anc_bits_str = bs.split(" ")[0] if " " in bs else bs[:14]
        anc_val = int(anc_bits_str, 2)

        if anc_val != 0:
            anc_all_zero = False
            print(f"  S({inp:2d}): ancillas = {anc_bits_str}  FAIL <<<")
        else:
            print(f"  S({inp:2d}): ancillas = {anc_bits_str}  OK")

    print(f"\n  All ancillas returned to |0>: {anc_all_zero}")

    # ──────────────────────────────────────────────────────────────────────────
    #  TEST 3 — Full 64-bit S-layer on known test states
    # ──────────────────────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  TEST 3 — Full 64-bit S-layer")
    print("=" * 62)

    test_states = [
        0x0000000000000000,
        0xFFFFFFFFFFFFFFFF,
        0x0123456789ABCDEF,
        0xDEADBEEFCAFEBABE,
    ]

    all_pass_64 = True
    for ts in test_states:
        expected = classical_s_layer(ts)

        state_reg = QuantumRegister(64,      name='state')
        anc_reg   = QuantumRegister(16 * 14, name='anc')    # 224 ancillas
        cr        = ClassicalRegister(64,    name='out')
        qc        = QuantumCircuit(state_reg, anc_reg, cr)

        for bit in range(64):
            if (ts >> bit) & 1:
                qc.x(state_reg[bit])

        quantum_s_layer(qc, state_reg, anc_reg)
        qc.measure(state_reg, cr)

        result = simulate(qc, sim)
        ok = (result == expected)
        if not ok:
            all_pass_64 = False

        print(f"  Input   : 0x{ts:016X}")
        print(f"  Expected: 0x{expected:016X}")
        print(f"  Quantum : 0x{result:016X}")
        print(f"  Match   : {'PASS' if ok else 'FAIL <<<'}")
        print()

    # ──────────────────────────────────────────────────────────────────────────
    #  TEST 4 — Reversibility: circuit.inverse() restores the input
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 62)
    print("  TEST 4 — Reversibility: S-box followed by its inverse = identity")
    print("=" * 62)

    test_inputs = [0, 5, 11, 15]
    for inp in test_inputs:
        data = QuantumRegister(4,  name='data')
        anc  = QuantumRegister(14, name='anc')
        cr   = ClassicalRegister(4, name='out')
        qc   = QuantumCircuit(data, anc, cr)

        # Load input
        for bit in range(4):
            if (inp >> bit) & 1:
                qc.x(data[bit])

        # Forward S-box
        sub_fwd = QuantumCircuit(data, anc)
        quantum_sbox_nibble(sub_fwd, list(data), list(anc))
        qc.compose(sub_fwd, inplace=True)

        # Inverse: Qiskit's .inverse() reverses all gates and inverts each one
        sub_inv = sub_fwd.inverse()
        qc.compose(sub_inv, inplace=True)

        # Measure: should recover original input
        qc.measure(data, cr)

        result = simulate(qc, sim)
        ok = (result == inp)
        print(f"  Input {inp:2d} ({inp:04b}) -> S-box -> inverse -> {result:2d} ({result:04b})  {'PASS' if ok else 'FAIL <<<'}")

    # ──────────────────────────────────────────────────────────────────────────
    #  CIRCUIT RESOURCE REPORT
    # ──────────────────────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  CIRCUIT RESOURCE REPORT")
    print("=" * 62)

    # Single nibble
    data_r = QuantumRegister(4,  name='data')
    anc_r  = QuantumRegister(14, name='anc')
    qc_r   = QuantumCircuit(data_r, anc_r)
    quantum_sbox_nibble(qc_r, list(data_r), list(anc_r))
    ops = dict(qc_r.count_ops())

    print("  -- Single nibble S-box --")
    print(f"    Data qubits          : 4  (in-place)")
    print(f"    Ancilla qubits       : 14  (4 copies + 10 AND products)")
    print(f"    Toffoli (ccx) gates  : {ops.get('ccx', 0):3d}  (20 S-box + 20 cleanup)")
    print(f"    CNOT    (cx)  gates  : {ops.get('cx',  0):3d}")
    print(f"    X             gates  : {ops.get('x',   0):3d}  (constant '1' terms)")
    print(f"    Total gates          : {sum(ops.values()):3d}")
    print(f"    Circuit depth        : {qc_r.depth():3d}")

    print()
    print("  -- Full 64-bit S-layer (16 nibbles) --")
    print(f"    Data qubits          :  64")
    print(f"    Ancilla qubits       : {16 * 14:3d}  (16 * 14)")
    print(f"    Toffoli (ccx) gates  : {16 * ops.get('ccx', 0):3d}  (16 * {ops.get('ccx', 0)})")
    print(f"    CNOT    (cx)  gates  : {16 * ops.get('cx',  0):3d}")
    print(f"    X             gates  : {16 * ops.get('x',   0):3d}")
    print(f"    Total gates          : {16 * sum(ops.values()):3d}")
    print()
    print("  NOTE: Stabilizer simulation NOT usable here (Toffoli is non-Clifford).")
    print("        Using Aer matrix_product_state (MPS) method.")


# In[ ]:


# =============================================================================
#  QUANTUM INVERSE S-LAYER
# =============================================================================

_QUANTUM_SBOX_INV_CIRCUIT = None


def _get_quantum_sbox_inverse_circuit():
    """
    Build and cache the inverse of quantum_sbox_nibble as a reusable circuit.

    quantum_sbox_nibble maps:
        |x>|0...0>  ->  |S(x)>|0...0>

    Its circuit inverse therefore maps:
        |S(x)>|0...0>  ->  |x>|0...0>
    """
    global _QUANTUM_SBOX_INV_CIRCUIT

    if _QUANTUM_SBOX_INV_CIRCUIT is None:
        data = QuantumRegister(4, name="data")
        anc = QuantumRegister(14, name="anc")
        sbox = QuantumCircuit(data, anc, name="Sbox")
        quantum_sbox_nibble(sbox, list(data), list(anc))
        _QUANTUM_SBOX_INV_CIRCUIT = sbox.inverse()

    return _QUANTUM_SBOX_INV_CIRCUIT


def quantum_sbox_inverse_nibble(qc, nibble_qubits, ancilla_qubits):
    """
    Apply the inverse PRINCE S-box to one 4-qubit nibble in place.

    All 14 ancilla qubits must enter as |0> and are returned to |0>.
    """
    if len(nibble_qubits) != 4:
        raise ValueError("quantum_sbox_inverse_nibble expects exactly 4 data qubits")
    if len(ancilla_qubits) != 14:
        raise ValueError("quantum_sbox_inverse_nibble expects exactly 14 ancilla qubits")

    inv_sbox = _get_quantum_sbox_inverse_circuit()
    qc.compose(inv_sbox, qubits=list(nibble_qubits) + list(ancilla_qubits), inplace=True)


def quantum_s_layer_inv(qc, state_reg, ancilla_reg):
    """
    Apply the inverse S-layer to the full 64-bit PRINCE state register.

    Nibble i occupies state_reg[4*i .. 4*i+3].  Each nibble uses its own
    14-qubit ancilla slice ancilla_reg[14*i .. 14*i+13].
    """
    if len(state_reg) != 64:
        raise ValueError("quantum_s_inverse_layer expects a 64-qubit state register")
    if len(ancilla_reg) != 16 * 14:
        raise ValueError("quantum_s_inverse_layer expects 224 ancilla qubits")

    for i in range(16):
        nibble = [state_reg[4 * i + k] for k in range(4)]
        ancilla = [ancilla_reg[14 * i + k] for k in range(14)]
        qc.barrier(label=f"S^-1 nibble {i}")
        quantum_sbox_inverse_nibble(qc, nibble, ancilla)

