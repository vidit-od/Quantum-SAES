# PRINCE Resource Estimation Summary

This document summarizes the resource estimates produced from the notebooks in this repository.

## 1. Results Table

### PRINCE Cipher

| Circuit / Notebook | Qubits | X | H | Z | CNOT | Toffoli / RCCX | Raw Total Gates | Raw Depth | Clifford Gates | T Gates | T-depth | Clifford+T Depth |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal PRINCE, `Main.ipynb` | 480 | 1282 | 0 | 0 | 13920 | 7680 Toffoli | 22882 | 10712 | - | - | - | - |
| PRINCE with Clifford decomposition, `main_clifford.ipynb` | 480 | 1282 | - | - | 13920 | 7680 Toffoli | 22882 | 10712 | 76642 | 53760 | 24960 | 66488 |
| Efficient PRINCE, `main_efficient.ipynb` | 480 | 1218 | 0 | 0 | 13920 | 7680 Toffoli | 22818 | 815 | 69218 | 53760 | 1560 | 4269 |
| Efficient PRINCE aggressive, `main_efficient.ipynb` | 480 | 1218 | - | - | 36960 after decomposition | 7680 RCCX | 69538 after decomposition | - | 46178 | 23360 | 626 | 1857 |

### One Grover Iteration

| Circuit / Notebook | Qubits | X | H | Z | CNOT | Toffoli / RCCX | Raw Total Gates | Raw Depth | Clifford Gates | T Gates | T-depth | Clifford+T Depth |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| One Grover iteration, exact raw, `main_grover_one_iteration.ipynb` | 607 | 2710 | 384 | 2 | 27970 | 15740 Toffoli | 46806 | 2015 | - | - | - | - |
| One Grover iteration with Clifford decomposition, exact Toffoli | 607 | - | - | - | - | 15740 Toffoli | - | - | 141820 | 110180 | 4452 | 11963 |
| One Grover iteration aggressive relative-phase decomposition | 607 | - | - | - | - | RCCX based | - | - | 94782 | 47790 | 2010 | 5617 |

Note: Clifford+T totals can differ slightly across Qiskit versions and optimization settings. The raw counts are the most direct circuit-level counts.

## 2. Mathematical Calculation

### One PRINCE S-box

From the implemented reversible S-box:

| Component | X | CNOT | Toffoli |
|---|---:|---:|---:|
| 1 S-box | 5 | 55 | 40 |

### One S-layer

PRINCE applies 16 S-boxes per S-layer:

```text
1 S-layer = 16 * S-box
```

Therefore:

| Component | X | CNOT | Toffoli |
|---|---:|---:|---:|
| 1 S-layer | 80 | 880 | 640 |

### One M-layer

The M-layer is linear and implemented only with CNOT gates:

| Component | X | CNOT | Toffoli |
|---|---:|---:|---:|
| 1 M-layer | 0 | 224 | 0 |

### One Forward Round

A forward round is:

```text
Round_i = S-layer + M-layer + AddRC_i + AddK1
```

So:

```text
X        = 80 + popcount(RC_i)
CNOT     = 880 + 224 + 64 = 1168
Toffoli  = 640
```

For rounds 1 to 5:

```text
sum popcount(RC1..RC5) = 140
```

Therefore:

```text
X        = 5 * 80 + 140 = 540
CNOT     = 5 * 1168 = 5840
Toffoli  = 5 * 640 = 3200
```

### Middle Layer

The middle layer is:

```text
Middle = S-layer + M-layer + inverse S-layer
```

Therefore:

```text
X        = 80 + 80 = 160
CNOT     = 880 + 224 + 880 = 1984
Toffoli  = 640 + 640 = 1280
```

### Inverse Rounds

Each inverse round is:

```text
InverseRound_i = AddK1 + AddRC_i + M^-1-layer + inverse S-layer
```

This has the same count as a forward round:

```text
X        = 80 + popcount(RC_i)
CNOT     = 64 + 224 + 880 = 1168
Toffoli  = 640
```

For rounds 6 to 10:

```text
sum popcount(RC6..RC10) = 150
```

Therefore:

```text
X        = 5 * 80 + 150 = 550
CNOT     = 5 * 1168 = 5840
Toffoli  = 5 * 640 = 3200
```

### Full PRINCE Encryption

Extra whitening:

```text
pre-whitening  = k0 xor + k1 xor = 128 CNOT
post-whitening = RC11 xor + k1 xor + k0' xor = 32 X + 128 CNOT
```

So full PRINCE encryption:

```text
X        = 540 + 160 + 550 + 32 = 1282
CNOT     = 128 + 5840 + 1984 + 5840 + 128 = 13920
Toffoli  = 3200 + 1280 + 3200 = 7680
```

Total raw gates:

```text
1282 + 13920 + 7680 = 22882
```

### One Grover Iteration

One Grover iteration contains:

```text
key superposition
compute k0'
PRINCE encryption
ciphertext phase check
PRINCE uncompute
uncompute k0'
128-bit diffuser
```

For the notebook example:

```text
plaintext = 0x1111111111111111
popcount(plaintext) = 16

target ciphertext = 0x44FBFF21F4BA60E1
popcount(ciphertext) = 35
```

Key superposition:

```text
H = 128
```

Compute and uncompute `k0'`:

```text
compute k0'   = 65 CNOT
uncompute k0' = 65 CNOT
total         = 130 CNOT
```

PRINCE encryption plus uncomputation:

```text
X        = 2 * 1282 = 2564
CNOT     = 2 * 13920 = 27840
Toffoli  = 2 * 7680 = 15360
```

Ciphertext phase marker:

```text
target XOR twice              = 2 * popcount(ciphertext) = 70 X
zero-to-one conversion        = 2 * 64 = 128 X
64-control phase construction = 126 Toffoli + 1 Z
```

Diffuser on 128 key qubits:

```text
H gates               = 2 * 128 = 256
X gates               = 2 * 128 = 256
128-control phase     = 254 Toffoli + 1 Z
```

Plaintext loading:

```text
X = popcount(plaintext) = 16
```

Now summing:

```text
H = 128 + 256 = 384

X = 16 + 2564 + 70 + 128 + 256 = 3034

CNOT = 27840 + 130 = 27970

Toffoli = 15360 + 126 + 254 = 15740

Z = 1 + 1 = 2
```

Mathematical total:

```text
384 + 3034 + 2 + 27970 + 15740 = 47130
```

## 3. Mathematical vs Actual Implementation

### PRINCE Cipher

| Metric | Mathematical | Actual Normal PRINCE | Actual Efficient PRINCE |
|---|---:|---:|---:|
| Qubits | 480 | 480 | 480 |
| X | 1282 | 1282 | 1218 |
| CNOT | 13920 | 13920 | 13920 |
| Toffoli | 7680 | 7680 | 7680 |
| Total gates | 22882 | 22882 | 22818 |
| Depth | - | 10712 | 815 |

The efficient version has the same logical gate structure, but Qiskit cancels 64 redundant X gates:

```text
1282 - 1218 = 64
```

The main improvement is depth:

```text
10712 -> 815
```

### One Grover Iteration

| Metric | Mathematical / Direct Construction | Actual Optimized Notebook |
|---|---:|---:|
| Qubits | 607 | 607 |
| H | 384 | 384 |
| X | 3034 | 2710 |
| Z | 2 | 2 |
| CNOT | 27970 | 27970 |
| Toffoli | 15740 | 15740 |
| Total gates | 47130 | 46806 |
| Depth | 2019 | 2015 |

The difference is caused by Qiskit optimization cancelling redundant X gates:

```text
3034 - 2710 = 324 X gates cancelled
```

Everything else matches exactly:

```text
CNOT     = 27970
Toffoli  = 15740
H        = 384
Z        = 2
```

