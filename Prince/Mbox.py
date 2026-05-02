#!/usr/bin/env python
# coding: utf-8

# In[1]:


"""
============================================================
 PRINCE Block Cipher — M-Layer (Linear / MixColumns Layer)
============================================================

This module implements the PRINCE M-layer as a reversible
quantum circuit of CNOT gates only.

Public API
----------
    quantum_m_layer(qc, state)          — apply M  (forward)
    quantum_m_layer_inv(qc, state)      — apply M⁻¹ (inverse)
    classical_m_layer(state_64bit)      — classical reference for M
    classical_m_layer_inv(state_64bit)  — classical reference for M⁻¹

Calling convention (mirrors Sbox.py):
    quantum_m_layer(qc, state)
    ↑ exactly how you call quantum_s_layer(qc, state, anc)

Background — what the M-layer is
---------------------------------
PRINCE's linear layer multiplies the 64-bit state by a
64×64 binary matrix M over GF(2).  The matrix has a
"hat-like" α structure:

    M = M̂  where  M̂ = diag(M0, M1, M2, M3)
                        for the four 16-bit sub-blocks,

and each 16×16 sub-matrix is built from two 4×4 blocks
(called M0_hat and M1_hat in the spec):

    M0_hat = [[0,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]  (SR rows)
    M1_hat = [[1,0,0,0], [0,0,0,0], [0,0,1,0], [0,0,0,1]]

The 16-bit sub-matrices used in rounds are:
    SR_row0 = M0_hat   SR_row1 = M1_hat
    SR_row2 = M1_hat   SR_row3 = M0_hat

(For the precise definition and the α-hat structure see
Borghoff et al., ASIACRYPT 2012, §2.2 and Table 1.)

Because M is a binary matrix (entries 0/1) and arithmetic
is over GF(2), each output bit is the XOR of some subset
of input bits → each output bit is computed by a fan-in
CNOT tree with NO ancilla qubits needed.

Bit convention (same as rest of the project)
--------------------------------------------
    state[0]  ↔  bit 0  (LSB) of the 64-bit integer
    state[63] ↔  bit 63 (MSB)

The 64-bit state is viewed as a 4×4 array of 4-bit nibbles
laid out column-major (PRINCE convention):

    nibble 0  = bits  3.. 0   (state[ 0.. 3])
    nibble 1  = bits  7.. 4   (state[ 4.. 7])
    ...
    nibble 15 = bits 63..60   (state[60..63])

Invertibility
-------------
M is an involution (M = M⁻¹) on the 4×4 nibble grid ONLY
within each 16-bit row group under the α-hat construction.
For Grover's oracle the inverse circuit is simply the same
CNOT network applied again — but we provide explicit
`_inv` variants for clarity and future flexibility.
"""

from qiskit import QuantumCircuit, QuantumRegister


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — 64×64 GF(2) MATRIX DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

def _build_prince_M_matrix():
    """
    Construct the 64×64 binary M matrix for PRINCE over GF(2).

    The PRINCE M-layer operates on the state as four 16-bit rows.
    Within each 16-bit row, a 16×16 binary sub-matrix is applied.
    The four sub-matrices are SR0, SR1, SR2, SR3 (one per row of the
    4×4 nibble grid).

    Each 16×16 sub-matrix is built from four 4×4 blocks arranged as:
        [[A, B],
         [C, D]]
    where A,B,C,D are 4×4 binary matrices chosen according to the
    PRINCE spec (Table 1, M̂ construction).

    The four 4×4 primitive matrices are:
        M0 = [[0,1,1,1],   (used for SR0 and SR3)
               [1,0,1,1],
               [1,1,0,1],
               [1,1,1,0]]

        M1 = [[1,0,0,0],   (used for SR1 and SR2, off-diagonal blocks)
               [0,1,0,0],
               [0,0,1,0],
               [0,0,0,1]]  (i.e. identity)

    Sub-matrix layout (column-major nibble indexing):
        Row 0 (nibbles 0,4,8,12)  → SR0  uses M0 on diagonal, 0 elsewhere
        Row 1 (nibbles 1,5,9,13)  → SR1  uses M1 on diagonal
        Row 2 (nibbles 2,6,10,14) → SR2  uses M1 on diagonal
        Row 3 (nibbles 3,7,11,15) → SR3  uses M0 on diagonal

    Returns
    -------
    M : list[list[int]]   64×64 binary matrix (list of 64 rows,
                           each row a list of 64 ints ∈ {0,1})
    """

    # ── 4×4 primitive matrices ────────────────────────────────────────────────
    # M0: every off-diagonal entry is 1 (the "all-ones minus identity" matrix)
    M0 = [
        [0, 1, 1, 1],
        [1, 0, 1, 1],
        [1, 1, 0, 1],
        [1, 1, 1, 0],
    ]

    # M1: identity
    M1 = [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]

    # Zero 4×4 block
    Z4 = [[0]*4 for _ in range(4)]

    # ── Build the four 16×16 sub-matrices ─────────────────────────────────────
    # Each sub-matrix acts on one "row" of the 4×4 nibble grid.
    # Row r contains nibbles r, r+4, r+8, r+12  (column-major order).
    #
    # The M̂ (hat) construction from the PRINCE spec:
    #   SR0 and SR3 use M0 on the block-diagonal, zeros elsewhere.
    #   SR1 and SR2 use M1 on the block-diagonal, zeros elsewhere.
    #
    # Concretely each 16×16 sub-matrix is block-diagonal:
    #   diag(A, A, A, A)  where A is either M0 or M1.

    def block_diag_16(A):
        """Build a 16×16 matrix from four copies of 4×4 block A on the diagonal."""
        mat = [[0]*16 for _ in range(16)]
        for block in range(4):
            for r in range(4):
                for c in range(4):
                    mat[block*4 + r][block*4 + c] = A[r][c]
        return mat

    SR = [
        block_diag_16(M0),   # row 0 → M0
        block_diag_16(M1),   # row 1 → M1  (identity → no-op, but kept for structure)
        block_diag_16(M1),   # row 2 → M1
        block_diag_16(M0),   # row 3 → M0
    ]

    # ── Assemble the 64×64 matrix ─────────────────────────────────────────────
    # State bit layout (column-major nibble order):
    #   bits  0.. 3 = nibble  0  (row 0, col 0)
    #   bits  4.. 7 = nibble  1  (row 1, col 0)
    #   bits  8..11 = nibble  2  (row 2, col 0)
    #   bits 12..15 = nibble  3  (row 3, col 0)
    #   bits 16..19 = nibble  4  (row 0, col 1)
    #   ...
    #   bits 60..63 = nibble 15  (row 3, col 3)
    #
    # Nibble n is in row  (n % 4)  and column  (n // 4).
    # Its bits occupy state positions [4n .. 4n+3].
    #
    # The M-layer applies SR[row_of_nibble] to the 16-bit group that
    # consists of the four nibbles in that row.
    #
    # The four nibbles in row r are: r, r+4, r+8, r+12
    # Their 16 bits are at positions: [4r, 4r+1, 4r+2, 4r+3,
    #                                   4r+16, ..., 4r+18,
    #                                   4r+32, ..., 4r+34,
    #                                   4r+48, ..., 4r+50]
    # i.e. for column c ∈ {0,1,2,3}: bits 4*(r + 4*c) .. 4*(r+4*c)+3

    # Start with 64×64 zero matrix
    M_full = [[0]*64 for _ in range(64)]

    for row_r in range(4):          # nibble row (0..3)
        # Collect the 16 bit-indices that belong to this nibble row
        bit_indices = []
        for col_c in range(4):      # nibble column (0..3)
            nibble_n = row_r + 4 * col_c
            base = 4 * nibble_n
            bit_indices.extend([base, base+1, base+2, base+3])
        # bit_indices[0..15] are the 16 state bits for this row,
        # ordered as (col0_bit0, col0_bit1, col0_bit2, col0_bit3,
        #             col1_bit0, ..., col3_bit3)

        sub = SR[row_r]  # 16×16 sub-matrix for this row

        for out_i in range(16):
            for in_j in range(16):
                if sub[out_i][in_j]:
                    M_full[bit_indices[out_i]][bit_indices[in_j]] = 1

    return M_full


# Build once at import time
_M_MATRIX = _build_prince_M_matrix()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CLASSICAL REFERENCE
# ══════════════════════════════════════════════════════════════════════════════

def classical_m_layer(state_64bit: int) -> int:
    """
    Apply the PRINCE M-layer to a 64-bit integer (classical, GF(2) matrix-vec).

    Parameters
    ----------
    state_64bit : int   64-bit input state

    Returns
    -------
    int   64-bit output state after M
    """
    M = _M_MATRIX
    result = 0
    for out_bit in range(64):
        val = 0
        for in_bit in range(64):
            if M[out_bit][in_bit] and ((state_64bit >> in_bit) & 1):
                val ^= 1
        result |= (val << out_bit)
    return result


def classical_m_layer_inv(state_64bit: int) -> int:
    """
    Apply the PRINCE M⁻¹-layer to a 64-bit integer.

    In PRINCE the M-layer is NOT a global involution (M ≠ M⁻¹ over
    the full 64 bits), so we compute M⁻¹ explicitly via Gaussian
    elimination over GF(2) at import time.

    Parameters
    ----------
    state_64bit : int   64-bit input state

    Returns
    -------
    int   64-bit output state after M⁻¹
    """
    M_inv = _M_INV_MATRIX
    result = 0
    for out_bit in range(64):
        val = 0
        for in_bit in range(64):
            if M_inv[out_bit][in_bit] and ((state_64bit >> in_bit) & 1):
                val ^= 1
        result |= (val << out_bit)
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — GF(2) MATRIX INVERSE (computed once at import)
# ══════════════════════════════════════════════════════════════════════════════

def _gf2_matrix_inverse(M):
    """
    Compute the inverse of a binary (GF(2)) square matrix via
    Gaussian elimination with full pivoting.

    Parameters
    ----------
    M : list[list[int]]   n×n binary matrix

    Returns
    -------
    list[list[int]]   n×n binary inverse matrix

    Raises
    ------
    ValueError if M is singular.
    """
    n = len(M)
    # Augment [M | I]
    aug = [list(M[i]) + [1 if i == j else 0 for j in range(n)]
           for i in range(n)]

    for col in range(n):
        # Find pivot
        pivot = None
        for row in range(col, n):
            if aug[row][col] == 1:
                pivot = row
                break
        if pivot is None:
            raise ValueError("Matrix is singular over GF(2) — no M-layer inverse.")
        aug[col], aug[pivot] = aug[pivot], aug[col]

        # Eliminate column in all other rows
        for row in range(n):
            if row != col and aug[row][col] == 1:
                aug[row] = [(aug[row][k] ^ aug[col][k]) for k in range(2 * n)]

    return [aug[i][n:] for i in range(n)]


_M_INV_MATRIX = _gf2_matrix_inverse(_M_MATRIX)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — CNOT-NETWORK BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _apply_gf2_matrix_as_cnots(qc, state_reg, M):
    """
    Apply a GF(2) matrix M to `state_reg` in-place using CNOT gates only,
    WITHOUT any ancilla qubits.

    Algorithm  (in-place GF(2) matrix application via LUP decomposition)
    -----------------------------------------------------------------------
    A naive approach would read input bit j and CNOT it into output bit i
    for every (i,j) pair where M[i][j]=1.  However, this is NOT in-place:
    it reads the original input bits while writing new output bits, which
    would require a scratch register.

    Instead we use the fact that any invertible GF(2) matrix can be
    decomposed as a product of elementary row-operation matrices — each of
    which is a single CNOT.  We perform Gaussian elimination on M,
    recording each pivot step as a CNOT, and then apply those CNOTs to
    the qubit register.

    Concretely:
        1. Forward elimination (lower-triangular form):
           For each pivot column c, eliminate all rows r > c that have
           a 1 in column c by XOR-ing row c into row r  →  CNOT(c, r).
        2. Back-substitution (diagonal form):
           For each pivot row c (bottom to top), eliminate all rows r < c
           by XOR-ing row c into row r  →  CNOT(c, r).
        3. At this point M should be the identity, and the recorded
           CNOT sequence implements the original M in-place.

    This is the standard technique used in quantum circuit synthesis for
    linear reversible circuits (Patel, Markov, Hayes 2003).

    The CNOT count is at most O(n²/log n) for an n×n matrix.

    Parameters
    ----------
    qc        : QuantumCircuit
    state_reg : QuantumRegister   n-qubit register (modified in place)
    M         : list[list[int]]   n×n invertible GF(2) matrix

    Side effects
    ------------
    Appends CNOT gates (cx) to `qc`.
    """
    n = len(M)
    # Work on a mutable copy so we don't modify the global matrix
    mat = [list(row) for row in M]
    cnot_ops = []   # list of (control_qubit, target_qubit) tuples

    # ── Forward elimination ───────────────────────────────────────────────────
    for col in range(n):
        # Find pivot row (first row >= col with mat[row][col] == 1)
        pivot = None
        for row in range(col, n):
            if mat[row][col] == 1:
                pivot = row
                break

        if pivot is None:
            # Column is all-zero below diagonal — matrix may be singular or
            # the column was already cleared by earlier operations.
            # (For the PRINCE M-matrix this should not happen.)
            continue

        if pivot != col:
            # Swap rows: implement as three XOR-swaps (CNOT pairs)
            # CNOT(pivot→col), CNOT(col→pivot), CNOT(pivot→col)
            cnot_ops.append((pivot, col))
            cnot_ops.append((col, pivot))
            cnot_ops.append((pivot, col))
            # Reflect swap in the working matrix
            for k in range(n):
                mat[col][k], mat[pivot][k] = mat[pivot][k], mat[col][k]

        # Eliminate all rows below the pivot
        for row in range(col + 1, n):
            if mat[row][col] == 1:
                cnot_ops.append((col, row))          # CNOT(col → row)
                for k in range(n):
                    mat[row][k] ^= mat[col][k]

    # ── Back substitution ─────────────────────────────────────────────────────
    for col in range(n - 1, -1, -1):
        if mat[col][col] != 1:
            continue   # degenerate column (skip for robustness)
        for row in range(col - 1, -1, -1):
            if mat[row][col] == 1:
                cnot_ops.append((col, row))          # CNOT(col → row)
                for k in range(n):
                    mat[row][k] ^= mat[col][k]

    # ── Emit CNOT gates to the circuit ────────────────────────────────────────
    for ctrl, tgt in cnot_ops:
        qc.cx(state_reg[ctrl], state_reg[tgt])


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — PUBLIC QUANTUM INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def quantum_m_layer(qc: QuantumCircuit, state: QuantumRegister) -> None:
    """
    Apply the PRINCE M-layer to `state` in-place (no ancilla qubits).

    This appends a network of CNOT gates implementing the 64×64 GF(2)
    matrix multiplication  state ← M · state.

    Usage (drop-in, just like quantum_s_layer):
        qc.barrier(label="M-layer")
        quantum_m_layer(qc, state)

    Parameters
    ----------
    qc    : QuantumCircuit    circuit to append gates to
    state : QuantumRegister   64-qubit state register (modified in-place)
    """
    _apply_gf2_matrix_as_cnots(qc, state, _M_MATRIX)


def quantum_m_layer_inv(qc: QuantumCircuit, state: QuantumRegister) -> None:
    """
    Apply the PRINCE M⁻¹-layer to `state` in-place (no ancilla qubits).

    Used in the second half of PRINCE (rounds 6–10 use M⁻¹ instead of M).

    Usage:
        qc.barrier(label="M-inv-layer")
        quantum_m_layer_inv(qc, state)

    Parameters
    ----------
    qc    : QuantumCircuit    circuit to append gates to
    state : QuantumRegister   64-qubit state register (modified in-place)
    """
    _apply_gf2_matrix_as_cnots(qc, state, _M_INV_MATRIX)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — SELF-TEST  (run this file directly to verify)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from qiskit_aer import AerSimulator
    from qiskit import ClassicalRegister, transpile

    sim = AerSimulator(method="matrix_product_state")

    def run_circuit(qc):
        result = sim.run(qc, shots=1).result()
        counts = result.get_counts()
        return int(list(counts.keys())[0], 2)

    def load_state(qc, state_reg, value):
        """Initialise state_reg to |value⟩ via X gates."""
        for bit in range(64):
            if (value >> bit) & 1:
                qc.x(state_reg[bit])

    MASK64 = (1 << 64) - 1

    print("=" * 62)
    print("  Mbox.py  —  self-test")
    print("=" * 62)

    test_vectors = [
        0x0000000000000000,
        0xFFFFFFFFFFFFFFFF,
        0x0123456789ABCDEF,
        0xFEDCBA9876543210,
        0xDEADBEEFCAFEBABE,
        0xA5A5A5A5A5A5A5A5,
    ]

    all_pass = True

    for tv in test_vectors:
        # ── Test 1: quantum M vs classical M ─────────────────────────────────
        state = QuantumRegister(64, name="state")
        creg  = ClassicalRegister(64, name="out")
        qc    = QuantumCircuit(state, creg)
        load_state(qc, state, tv)
        quantum_m_layer(qc, state)
        qc.measure(state, creg)

        q_out   = run_circuit(qc)
        ref_out = classical_m_layer(tv)
        ok1     = (q_out == ref_out)

        # ── Test 2: quantum M⁻¹ vs classical M⁻¹ ────────────────────────────
        state2 = QuantumRegister(64, name="state")
        creg2  = ClassicalRegister(64, name="out")
        qc2    = QuantumCircuit(state2, creg2)
        load_state(qc2, state2, tv)
        quantum_m_layer_inv(qc2, state2)
        qc2.measure(state2, creg2)

        q_out2   = run_circuit(qc2)
        ref_out2 = classical_m_layer_inv(tv)
        ok2      = (q_out2 == ref_out2)

        # ── Test 3: M then M⁻¹ = identity ────────────────────────────────────
        state3 = QuantumRegister(64, name="state")
        creg3  = ClassicalRegister(64, name="out")
        qc3    = QuantumCircuit(state3, creg3)
        load_state(qc3, state3, tv)
        quantum_m_layer(qc3, state3)
        quantum_m_layer_inv(qc3, state3)
        qc3.measure(state3, creg3)

        q_out3 = run_circuit(qc3)
        ok3    = (q_out3 == tv)

        status = "✅ PASS" if (ok1 and ok2 and ok3) else "❌ FAIL"
        if not (ok1 and ok2 and ok3):
            all_pass = False
        print(f"  Input  : 0x{tv:016X}")
        print(f"    M  quantum vs classical : {'✅' if ok1 else '❌'}  "
              f"(0x{q_out:016X} vs 0x{ref_out:016X})")
        print(f"    M⁻¹ quantum vs classical: {'✅' if ok2 else '❌'}  "
              f"(0x{q_out2:016X} vs 0x{ref_out2:016X})")
        print(f"    M then M⁻¹ = identity  : {'✅' if ok3 else '❌'}  "
              f"(got 0x{q_out3:016X})")
        print()

    print("=" * 62)
    print("  Overall:", "✅ ALL PASS" if all_pass else "❌ SOME FAILURES")
    print("=" * 62)

    # ── Gate count report ─────────────────────────────────────────────────────
    state_r = QuantumRegister(64, name="state")
    qc_r    = QuantumCircuit(state_r)
    quantum_m_layer(qc_r, state_r)
    ops = dict(qc_r.count_ops())
    print(f"\n  M-layer gate count  : {ops.get('cx', 0)} CNOT gates")

    state_i = QuantumRegister(64, name="state")
    qc_i    = QuantumCircuit(state_i)
    quantum_m_layer_inv(qc_i, state_i)
    ops_i = dict(qc_i.count_ops())
    print(f"  M⁻¹-layer gate count: {ops_i.get('cx', 0)} CNOT gates")
    print()


# In[ ]:




