#!/usr/bin/env python
# coding: utf-8

# In[1]:


def gf4_multiply(qc, a, b, c):
    """
    Implements multiplication in GF(2^4) with modulus x^4 + x + 1.

    a: list of 4 qubit indices [a0, a1, a2, a3]
    b: list of 4 qubit indices [b0, b1, b2, b3]
    c: list of 4 qubit indices [c0, c1, c2, c3] (output)
    """

    # Helper: Toffoli writes AND(a,b) into target (XOR-style)
    def add_and(q1, q2, target):
        qc.ccx(q1, q2, target)

    # --- c0 = a0b0 ⊕ a1b3 ⊕ a2b2 ⊕ a3b1 ---
    add_and(a[0], b[0], c[0])
    add_and(a[1], b[3], c[0])
    add_and(a[2], b[2], c[0])
    add_and(a[3], b[1], c[0])

    # --- c1 = a0b1 ⊕ a1b0 ⊕ a2b3 ⊕ a3b2 ---
    add_and(a[0], b[1], c[1])
    add_and(a[1], b[0], c[1])
    add_and(a[2], b[3], c[1])
    add_and(a[3], b[2], c[1])

    # --- c2 = a0b2 ⊕ a1b1 ⊕ a2b0 ⊕ a3b3 ---
    add_and(a[0], b[2], c[2])
    add_and(a[1], b[1], c[2])
    add_and(a[2], b[0], c[2])
    add_and(a[3], b[3], c[2])

    # --- c3 = a0b3 ⊕ a1b2 ⊕ a2b1 ⊕ a3b0 ---
    add_and(a[0], b[3], c[3])
    add_and(a[1], b[2], c[3])
    add_and(a[2], b[1], c[3])
    add_and(a[3], b[0], c[3])


# In[2]:


def gf4_square(qc, a, out):
    """
    Squaring in GF(2^4) with modulus x^4 + x + 1.

    qc : QuantumCircuit
    a   : list of 4 qubit indices [a0, a1, a2, a3]  (LSB = a0)
    out : list of 4 qubit indices [s0, s1, s2, s3] (outputs must be initialized to |0>)
    """
    # s0 = a0 XOR a2
    qc.cx(a[0], out[0])
    qc.cx(a[2], out[0])

    # s1 = a3
    qc.cx(a[3], out[1])

    # s2 = a2
    qc.cx(a[2], out[2])

    # s3 = a1 XOR a3
    qc.cx(a[1], out[3])
    qc.cx(a[3], out[3])

