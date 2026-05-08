#!/usr/bin/env python
# coding: utf-8

# In[1]:


from Sbox    import quantum_s_layer, classical_s_layer, quantum_s_layer_inv, classical_s_layer_inv
from Mbox    import quantum_m_layer, classical_m_layer, quantum_m_layer_inv, classical_m_layer_inv
from Helpers import xor_constant_into_register, xor_register_into_register


# In[2]:


def quantum_round(Round_Number, qc, state, anc, qk1, RC_i):
    qc.barrier(label=f"Round {Round_Number} Sbox")
    quantum_s_layer(qc, state, anc)
    qc.barrier(label=f"Round {Round_Number} Mbox")
    quantum_m_layer(qc, state)
    qc.barrier(label=f"Round {Round_Number} AddRC")
    xor_constant_into_register(qc, state, RC_i)
    qc.barrier(label=f"Round {Round_Number} AddK1")
    xor_register_into_register(qc, qk1, state)


# In[3]:


def classical_round(Round_Number, state, k1, RC_i):
    state = classical_s_layer(state)
    state = classical_m_layer(state)
    state ^= RC_i
    state ^= k1
    return state


# In[4]:


def quantum_inverse_round(Round_Number, qc, state, anc, qk1, RC_i):
    qc.barrier(label=f"Round {Round_Number} AddK1")
    xor_register_into_register(qc, qk1, state)
    qc.barrier(label=f"Round {Round_Number} AddRC")
    xor_constant_into_register(qc, state, RC_i)
    qc.barrier(label=f"Round {Round_Number} Mbox inverse")
    quantum_m_layer_inv(qc, state)
    qc.barrier(label=f"Round {Round_Number} Sbox")
    quantum_s_layer_inv(qc, state, anc)


# In[5]:


def classical_inverse_round(Round_Number, state, k1, RC_i):
    state ^= k1
    state ^= RC_i
    state = classical_m_layer_inv(state)
    state = classical_s_layer_inv(state)
    return state


# In[ ]:




