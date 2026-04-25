def log_gate_stats(stage_name, qc, SAES_GATE_LOG):
    """
    Record gate statistics for the current circuit stage.
    
    stage_name : str (e.g. 'SubNibble', 'ShiftRows', 'MixColumns')
    qc         : QuantumCircuit
    SAES_GATE_LOG : a global list where we save all prev gate info

    Appends a dictionary to SAES_GATE_LOG containing:
        - stage
        - total_gates
        - counts per gate type (cx, ccx, x, etc.)
        - depth
        - qubits
    """

    ops = qc.count_ops()          # per gate-type counts
    total = sum(ops.values())     # total number of gates
    depth = qc.depth()            # circuit depth

    entry = {
        "stage": stage_name,
        "total_gates": total,
        "depth": depth,
        "num_qubits": qc.num_qubits,
        "ops": dict(ops)          # store raw dictionary
    }

    SAES_GATE_LOG.append(entry)
    print(f"[LOG] Recorded stage '{stage_name}'  → total gates = {total}, depth = {depth}")


def apply_plaintext(qc, plaintext):
    """
    plaintext: string of 16 bits, e.g. '1001011011001111'
    qc: QuantumCircuit already created with at least 16 qubits (0-15)
    """
    # Remove spaces if user enters "1001 0110 ..."
    bits = plaintext.replace(" ", "")
    
    if len(bits) != 16 or any(b not in "01" for b in bits):
        raise ValueError("Plaintext must be exactly 16 bits (0 or 1).")

    # Apply Pauli-X for all 1's
    for i, bit in enumerate(bits):
        if bit == "1":
            qc.x(i)   # Flip qubit i


def add_round_key(qc, key_bits):
    """
    key_bits: string of 16 bits (the round key)
    qc: QuantumCircuit with at least 32 qubits:
        - 0–15  : plaintext/state qubits
        - 16–31 : key qubits
    """
    key_bits = key_bits.replace(" ", "")
    if len(key_bits) != 16:
        raise ValueError("Round key must be 16 bits.")

    # For each bit: state[i] = state[i] XOR key[i]
    # Implemented as CNOT(control=key, target=state)
    for i, bit in enumerate(key_bits):
        if bit == "1":
            # Flip the key qubit to 1 using X
            qc.x(16 + i)

        # Apply XOR: state[i] ^= key[i]
        qc.cx(16 + i, i)

def add_round_key_quantum(qc, key_reg_base, state_reg_base):
    """
    Quantum AddRoundKey:
        state[i] ^= key[i]

    key_reg_base   : starting index of key register (16 qubits)
    state_reg_base : starting index of state register (16 qubits)
    """

    for i in range(16):
        qc.cx(key_reg_base + i, state_reg_base + i)
