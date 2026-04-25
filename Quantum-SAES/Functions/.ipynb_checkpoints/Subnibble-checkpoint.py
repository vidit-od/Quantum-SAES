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
                           draw_mode=None):

    def process_nibble(nibble_index):
        nibble_start = state_base + 4*nibble_index

        # state nibble
        a = [nibble_start + i for i in range(4)]

        # workspace registers (16 qubits total)
        W0 = [workspace_base + i for i in range(4)]        # a2
        W1 = [workspace_base + 4 + i for i in range(4)]    # a4
        W2 = [workspace_base + 8 + i for i in range(4)]    # a8
        W3 = [workspace_base + 12 + i for i in range(4)]   # out1 / inverse

        # --- compute a^2 → W0 ---
        gf4_square(qc, a, W0)

        # --- compute a^4 → W1 ---
        gf4_square(qc, W0, W1)

        # --- compute a^8 → W2 ---
        gf4_square(qc, W1, W2)

        # --- compute out1 = a^8 * a^4 → W3 ---
        gf4_multiply(qc, W2, W1, W3)

        # --- compute inverse = out1 * a^2 → W1 ---
        for i in range(4): qc.reset(W1[i])     # ensure W1 is clean
        gf4_multiply(qc, W3, W0, W1)           # W1 = a^14

        # --- affine transform: W1 → W0 ---
        for q in W0: qc.reset(q)
        affine_transform(qc, W1, W0)           # W0 = SubNibble(a)

        # --- write substituted nibble back into state ---
        for i in range(4):
            qc.reset(a[i])
            qc.cx(W0[i], a[i])

        # --- cleanup workspace ---
        for q in W0 + W1 + W2 + W3:
            qc.reset(q)

    # 4 nibbles
    for k in range(4):
        process_nibble(k)
