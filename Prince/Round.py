#!/usr/bin/env python
# coding: utf-8

# In[1]:


from Sbox    import quantum_s_layer, classical_s_layer
from Mbox    import quantum_m_layer, classical_m_layer
from Helpers import xor_constant_into_register, xor_register_into_register


# In[3]:


def quantum_round(Round_Number, qc, state, anc, qk1, RC_i):
    qc.barrier(label=f"Round {Round_Number} Sbox")
    quantum_s_layer(qc, state, anc)
    qc.barrier(label=f"Round {Round_Number} Mbox")
    quantum_m_layer(qc, state)
    qc.barrier(label=f"Round {Round_Number} AddRC")
    xor_constant_into_register(qc, state, RC_i)
    qc.barrier(label=f"Round {Round_Number} AddK1")
    xor_register_into_register(qc, qk1, state)


# In[ ]:




