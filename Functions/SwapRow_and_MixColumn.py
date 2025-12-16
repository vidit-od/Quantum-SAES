#!/usr/bin/env python
# coding: utf-8

# In[5]:


def _mul_by_4_into(qc, src, tgt):
    """
    Compute tgt = 4 * src (GF(2^4) with modulus x^4 + x + 1)
    where:
        src: list of 4 qubit indices [a0,a1,a2,a3] (LSB = a0)
        tgt: list of 4 qubit indices [t0,t1,t2,t3] (must be |0> initially)
    Implementation of mapping:
        t0 = a2
        t1 = a3
        t2 = a0 ^ a2
        t3 = a1 ^ a2 ^ a3
    We use only CNOTs (linear transform).
    """
    a0, a1, a2, a3 = src
    t0, t1, t2, t3 = tgt

    # t0 = a2
    qc.cx(a2, t0)

    # t1 = a3
    qc.cx(a3, t1)

    # t2 = a0 ^ a2
    qc.cx(a0, t2)
    qc.cx(a2, t2)

    # t3 = a1 ^ a2 ^ a3
    qc.cx(a1, t3)
    qc.cx(a2, t3)
    qc.cx(a3, t3)


# In[6]:


def apply_mixcolumns_stage(qc,
                           state_base=0,
                           workspace_base=32,
                           reset_workspace=True,
                           draw_mode=None):
    """
    Apply paper-accurate MixColumns.
    Implements ShiftRows 'for free' by changing nibble routing:
        classical order  : N0 N1 / N2 N3
        after ShiftRows  : N0 N1 / N3 N2
    MixColumns operates column-wise on:
        Column 0 = N0, N3
        Column 1 = N1, N2
    """

    # Paper-accurate columns after ShiftRows
    shifted_columns = [
        (0, 3),  # Column 0 = (N0, N3)
        (1, 2)   # Column 1 = (N1, N2)
    ]

    def nib(i):   # nibble i => 4 qubits
        return [state_base + 4*i + j for j in range(4)]

    w_top = [workspace_base + i for i in range(4)]
    w_bot = [workspace_base + 4 + i for i in range(4)]

    for top_idx, bot_idx in shifted_columns:
        top = nib(top_idx)
        bot = nib(bot_idx)

        # compute 4*top and 4*bot into workspace
        _mul_by_4_into(qc, top, w_top)
        _mul_by_4_into(qc, bot, w_bot)

        # top ^= (4 * bot)
        for i in range(4):
            qc.cx(w_bot[i], top[i])

        # bot ^= (4 * top_original)
        for i in range(4):
            qc.cx(w_top[i], bot[i])

        # reset workspace if allowed
        if reset_workspace:
            for q in w_top + w_bot:
                qc.reset(q)

    if draw_mode == 'image':
        from qiskit.visualization import circuit_drawer
        display(qc.draw('mpl'))
    elif draw_mode == 'text':
        print(qc)

    return qc


# In[ ]:




