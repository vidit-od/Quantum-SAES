#!/usr/bin/env python
# coding: utf-8

# In[5]:


from qiskit import QuantumCircuit
from .Arithmetics import *


# In[6]:


def affine_transform(qc, c, b):
    """
    Apply the S-AES affine transform:
    b = M * c  ⊕  (1,0,0,1)

    c: 4 input qubits  [c0, c1, c2, c3]
    b: 4 output qubits [b0, b1, b2, b3]
    """

    # Matrix M (rows):
    # b0 = c0 ⊕ c2 ⊕ c3
    qc.cx(c[0], b[0])
    qc.cx(c[2], b[0])
    qc.cx(c[3], b[0])

    # b1 = c0 ⊕ c1 ⊕ c3
    qc.cx(c[0], b[1])
    qc.cx(c[1], b[1])
    qc.cx(c[3], b[1])

    # b2 = c0 ⊕ c1 ⊕ c2
    qc.cx(c[0], b[2])
    qc.cx(c[1], b[2])
    qc.cx(c[2], b[2])

    # b3 = c1 ⊕ c2 ⊕ c3
    qc.cx(c[1], b[3])
    qc.cx(c[2], b[3])
    qc.cx(c[3], b[3])

    # Add constant vector (1,0,0,1)
    qc.x(b[0])  # b0 ^= 1
    qc.x(b[3])  # b3 ^= 1


# In[7]:


def apply_subnibbles_round(qc,
                           state_base=0,
                           workspace_base=32,
                           output_base=52,
                           draw_mode=None):
    """
    Applies the SubNibble layer (multiplicative inverse + affine) IN-PLACE
    on an existing circuit `qc`, for all 4 state nibbles.

    It reuses the same qubit layout as build_saes_stage1_subnibble:

      state_base .. state_base+15 : state/plaintext (4 nibbles)
      workspace_base .. workspace_base+19 : workspace (a^2, a^4, a^8, out1, affine_tmp)
      output_base .. output_base+15: temp output region for inverse (out_final)
    """

    def process_nibble(nibble_index):
        nibble_start = state_base + 4 * nibble_index

        # state nibble (LSB-first)
        a = [nibble_start + i for i in range(4)]

        # workspace slices (same as before)
        a2 = [workspace_base + i for i in range(4)]        # 32..35
        a4 = [workspace_base + 4 + i for i in range(4)]    # 36..39
        a8 = [workspace_base + 8 + i for i in range(4)]    # 40..43
        out1 = [workspace_base + 12 + i for i in range(4)] # 44..47

        # affine temporary target
        affine_tmp = [workspace_base + 16 + i for i in range(4)]  # 48..51

        # final inverse storage
        out_final = [output_base + 4*nibble_index + i for i in range(4)]  # 52..67

        # --- compute inverse into out_final ---

        gf4_square(qc, a, a2)      # a^2
        gf4_square(qc, a2, a4)     # a^4
        gf4_square(qc, a4, a8)     # a^8

        gf4_multiply(qc, a8, a4, out1)     # out1 = a^8 * a^4
        gf4_multiply(qc, out1, a2, out_final)  # out_final = out1 * a^2 = a^14

        # --- affine transform: out_final -> affine_tmp ---
        affine_transform(qc, out_final, affine_tmp)

        # --- write substituted nibble back into the state nibble ---
        for i in range(4):
            state_q = a[i]
            src_q = affine_tmp[i]
            qc.reset(state_q)          # ensure |0>
            qc.cx(src_q, state_q)      # state_q := affine_tmp[i]

        # --- clean workspace (optional but keeps ancilla reusable) ---
        for q in affine_tmp + out_final + out1 + a8 + a4 + a2:
            qc.reset(q)

    # process all four nibbles: N0, N1, N2, N3
    for nib_index in range(4):
        process_nibble(nib_index)

