#!/usr/bin/env python
# coding: utf-8

# In[3]:


def xor_constant_into_register(circuit, target_reg, constant_64bit):
    """
    Implement:  target_reg  ^=  constant_64bit

    For a *fixed* classical constant we simply flip every qubit whose
    corresponding bit in the constant is 1.  This is a plain Pauli-X gate,
    which is its own inverse (X² = I), so the operation is reversible.

    Bit mapping:
        constant bit 0   →  target_reg[0]   (LSB)
        constant bit 63  →  target_reg[63]  (MSB)

    Parameters
    ----------
    circuit        : QuantumCircuit   circuit to append gates to
    target_reg     : QuantumRegister  64-qubit register to be modified
    constant_64bit : int              64-bit constant to XOR in
    """
    for bit_index in range(64):
        if (constant_64bit >> bit_index) & 1:
            circuit.x(target_reg[bit_index])


def xor_register_into_register(circuit, source_reg, target_reg):
    """
    Implement:  target_reg  ^=  source_reg   (bit-wise, for all 64 bits)

    Each bit position uses one CNOT gate:
        CNOT(control=source[i], target=target[i])
    which flips target[i] when source[i] == |1⟩.

    CNOT is its own inverse (CNOT² = I), so the operation is reversible.
    The source register is left unchanged (it is the control).

    Parameters
    ----------
    circuit    : QuantumCircuit   circuit to append gates to
    source_reg : QuantumRegister  64-qubit control register (unchanged)
    target_reg : QuantumRegister  64-qubit target register (modified)
    """
    for i in range(64):
        circuit.cx(source_reg[i], target_reg[i])


# In[ ]:




