"""
Unified DTLBA Computational-Cost Benchmark Including T_E/D and T_FE
========================================================

This standalone Python program generates all required variables internally,
executes 22 distinct DTLBA-related operations, and reports their execution
costs separately.

Reference basis:
- MLWR-style polynomial arithmetic / rounding / reconciliation benchmark.
- Module-lattice authentication benchmark with A_sig, t_i, w_i, c_i, z_i.
- Fuzzy extractor benchmark uses a simple repetition-code secure-sketch-style
  Gen/Rep demonstrator plus SHA3-256 extraction. It is for operation-cost
  benchmarking, not a claim of a production biometric fuzzy extractor.

Outputs:
  DTLBA_22_operation_costs.csv
  DTLBA_22_operation_costs.txt

Requirements:
  pip install numpy cryptography
"""

import csv
import hashlib
import platform
import statistics
import time
import numpy as np

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    raise SystemExit("Please install dependency: pip install cryptography")

# ============================================================
# 1. GLOBAL PARAMETERS
# ============================================================
SEED = 20260919
REPETITIONS = 30
INNER_LOOPS = 5

# MLWR notation
N = 512
k = 3
q = 12289
p = 256
eta = 3

# Module-lattice authentication notation
N_s = 256
q_s = 8380417
k_s = 4
l_s = 5
eta_s = 2
tau_s = 39
gamma_1 = 2**17
B_z = gamma_1 - tau_s * eta_s

# Batch parameters
B = 100
r_B = 4
Q_B = 65537

rng = np.random.default_rng(SEED)

# ============================================================
# 2. COMMON HELPERS
# ============================================================
def H(data: bytes) -> bytes:
    """SHA3-256 hash."""
    return hashlib.sha3_256(data).digest()

def centered(a, modulus):
    x = np.remainder(a, modulus).astype(np.int64)
    return np.where(x > modulus // 2, x - modulus, x)

def encode_polyvec(v):
    return np.remainder(v, q_s).astype("<u4").tobytes()

# ============================================================
# OPERATION 1: POLYNOMIAL MULTIPLICATION  T_pm
# ============================================================
def polynomial_multiplication(a, b, modulus):
    """Negacyclic multiplication in Z_modulus[x]/(x^n+1)."""
    a = np.asarray(a, dtype=np.int64)
    b = np.asarray(b, dtype=np.int64)
    n = len(a)
    c = np.convolve(a, b)
    out = c[:n].copy()
    if len(c) > n:
        out[:len(c)-n] -= c[n:]
    return np.remainder(out, modulus).astype(np.int64)

# ============================================================
# OPERATION 2: POLYNOMIAL ADDITION/SUBTRACTION  T_add
# ============================================================
def polynomial_addition(a, b, modulus):
    return np.remainder(a + b, modulus).astype(np.int64)

def polynomial_subtraction(a, b, modulus):
    return np.remainder(a - b, modulus).astype(np.int64)

# ============================================================
# OPERATION 3: MLWR ROUNDING  T_rnd
# ============================================================
def mlwr_rounding(a):
    """Coefficient-wise q -> p rounding."""
    x = np.remainder(a, q).astype(np.int64)
    return ((p * x + q // 2) // q) % p

# ============================================================
# OPERATION 4: SCALAR MULTIPLICATION  T_sm
# ============================================================
def scalar_multiplication(alpha, a, modulus):
    return np.remainder(int(alpha) * a, modulus).astype(np.int64)

# ============================================================
# OPERATION 5: SHARE POLYNOMIAL GENERATION  T_spg
# ============================================================
def share_polynomial_generation(secret_poly, random_poly):
    """
    Benchmark share construction:
       Sh(x) = [s(x) + r(x)]_q.
    This gives a distinct polynomial-share generation workload.
    """
    return np.remainder(secret_poly + random_poly, q).astype(np.int64)

# ============================================================
# OPERATION 6: Cha FUNCTION  T_cha
# ============================================================
def cha_function(v):
    """
    Reconciliation characteristic function.
    Cha(v)=1 for coefficients in the middle half of Z_q, else 0.
    """
    x = np.remainder(v, q)
    return ((x >= q // 4) & (x < 3*q // 4)).astype(np.uint8)

# ============================================================
# OPERATION 7: Mod2 FUNCTION  T_mod2
# ============================================================
def mod2_function(v, hint):
    """
    Reconciliation-bit extraction benchmark:
       Mod2(v,h) = (round(2v/q) + h) mod 2.
    """
    bit = ((2 * np.remainder(v, q) + q // 2) // q) & 1
    return np.bitwise_xor(bit.astype(np.uint8), hint.astype(np.uint8))

# ============================================================
# OPERATION 8: HASH COMPUTATION  T_h
# ============================================================
def hash_computation(message):
    return H(message)

# ============================================================
# OPERATION 9: ENCRYPTION/DECRYPTION  T_E/D
# ============================================================
AES_KEY = bytes(range(32))
AES_NONCE = bytes(range(12))
AES_AAD = b"DTLBA-AAD"
AES_PLAINTEXT = b"DTLBA secure vehicular authentication payload" * 4
AES = AESGCM(AES_KEY)

def aes_gcm_enc_dec():
    ciphertext = AES.encrypt(AES_NONCE, AES_PLAINTEXT, AES_AAD)
    plaintext = AES.decrypt(AES_NONCE, ciphertext, AES_AAD)
    if plaintext != AES_PLAINTEXT:
        raise RuntimeError("AES-GCM verification failed")
    return plaintext

# ============================================================
# OPERATION 10: FUZZY EXTRACTOR Gen/Rep  T_FE
# ============================================================
# Simple Hamming-noise demonstrator:
# Each source bit is repetition encoded 3 times. Helper data stores
# codeword XOR biometric reading. Rep uses majority decoding.
FE_BITS = 128

def repetition_encode(bits):
    return np.repeat(bits, 3).astype(np.uint8)

def repetition_decode(codeword):
    blocks = codeword.reshape(-1, 3)
    return (np.sum(blocks, axis=1) >= 2).astype(np.uint8)

def fuzzy_gen(w):
    """Gen(w) -> extracted key R and helper P."""
    source = rng.integers(0, 2, FE_BITS, dtype=np.uint8)
    codeword = repetition_encode(source)
    helper = np.bitwise_xor(w, codeword)
    R = H(source.tobytes())
    return R, helper

def fuzzy_rep(w_noisy, helper):
    """Rep(w',P) -> recovered key R'."""
    noisy_codeword = np.bitwise_xor(w_noisy, helper)
    source_hat = repetition_decode(noisy_codeword)
    return H(source_hat.tobytes())

FE_W = rng.integers(0, 2, FE_BITS*3, dtype=np.uint8)
FE_R, FE_HELPER = fuzzy_gen(FE_W)
FE_W_NOISY = FE_W.copy()
# One error in selected repetition blocks, correctable by majority decoding.
for j in range(0, 30, 3):
    FE_W_NOISY[j] ^= 1

def fuzzy_extractor_gen_rep():
    recovered = fuzzy_rep(FE_W_NOISY, FE_HELPER)
    if recovered != FE_R:
        raise RuntimeError("Fuzzy extractor recovery failed")
    return recovered

# ============================================================
# OPERATION 11: XOR OPERATION  T_xor
# ============================================================
def xor_operation(a, b):
    return np.bitwise_xor(a, b)

# ============================================================
# MODULE-LATTICE AUTHENTICATION VARIABLES
# ============================================================
A_sig = rng.integers(0, q_s, size=(k_s, l_s, N_s), dtype=np.int64)

def matrix_vector_multiplication(A, v):
    out = np.zeros((A.shape[0], N_s), dtype=np.int64)
    for row in range(A.shape[0]):
        for col in range(A.shape[1]):
            out[row] = (
                out[row] +
                polynomial_multiplication(A[row, col], v[col], q_s)
            ) % q_s
    return out

def challenge_times_vector(c, v):
    return np.stack([
        polynomial_multiplication(c, v_j, q_s)
        for v_j in v
    ])


# ============================================================
# ADDITIONAL SIGNATURE PRIMITIVES
# ============================================================
def challenge_vector_multiplication(c, v):
    """Sparse challenge-polynomial times polynomial-vector multiplication."""
    return challenge_times_vector(c, v)

def vector_addition(a, b):
    """Coefficient-wise polynomial-vector addition modulo q_s."""
    return np.remainder(a + b, q_s).astype(np.int64)

def vector_comparison(a, b):
    """Exact equality comparison of two module/polynomial vectors modulo q_s."""
    return bool(np.array_equal(np.remainder(a, q_s),
                               np.remainder(b, q_s)))

def complete_signature_generation(M_i, s_i, local_rng):
    """
    Complete vehicle-side signature generation:
      y_i <- short mask
      w_i = A_sig y_i
      c_i = H_c(M_i || w_i)
      z_i = y_i + c_i s_i
      accept only if ||z_i||_inf < B_z
    """
    for _ in range(1000):
        y_i = local_rng.integers(
            -(B_z - 256), B_z - 256,
            size=(l_s, N_s), dtype=np.int64
        )
        w_i = module_lattice_matvec(A_sig, y_i % q_s)
        c_i = sparse_challenge_generation(M_i + encode_polyvec(w_i))
        cs_i = centered(
            challenge_vector_multiplication(c_i, s_i % q_s), q_s
        )
        z_i = vector_addition(y_i, cs_i)
        if response_norm_verification(z_i):
            return {"M": M_i, "w": w_i, "c": c_i, "z": z_i}
    raise RuntimeError("Signature-generation rejection sampling exhausted")

# ============================================================
# OPERATION 12: MODULE-LATTICE MATRIX-VECTOR MULTIPLICATION T_mv
# ============================================================
def module_lattice_matvec(A, v):
    return matrix_vector_multiplication(A, v)

# ============================================================
# OPERATION 13: SPARSE CHALLENGE GENERATION T_ch
# ============================================================
def sparse_challenge_generation(message):
    seed = int.from_bytes(H(b"Hc|" + message)[:8], "big")
    local_rng = np.random.default_rng(seed)
    positions = local_rng.choice(N_s, tau_s, replace=False)
    c = np.zeros(N_s, dtype=np.int64)
    c[positions] = local_rng.choice(np.array([-1, 1]), tau_s)
    return c

# ============================================================
# OPERATION 14: RESPONSE/NORM VERIFICATION T_norm
# ============================================================
def response_norm_verification(z):
    return bool(np.max(np.abs(centered(z, q_s))) < B_z)

def authentication_keygen(local_rng):
    s_i = local_rng.integers(
        -eta_s, eta_s + 1, size=(l_s, N_s), dtype=np.int64
    )
    t_i = module_lattice_matvec(A_sig, s_i % q_s)
    return s_i, t_i

def authentication_sign(i, local_rng):
    s_i, t_i = authentication_keygen(local_rng)
    M_i = H(f"PID_{i}|Y_{i}|RSU|timestamp".encode()) + encode_polyvec(t_i)

    # Rejection loop ensures ||z_i||_inf < B_z.
    for ctr in range(1000):
        # Leave margin for c_i*s_i.
        y_i = local_rng.integers(
            -(B_z - 256), B_z - 256,
            size=(l_s, N_s), dtype=np.int64
        )
        w_i = module_lattice_matvec(A_sig, y_i % q_s)
        c_i = sparse_challenge_generation(M_i + encode_polyvec(w_i))
        cs_i = centered(challenge_times_vector(c_i, s_i % q_s), q_s)
        z_i = (y_i + cs_i) % q_s

        if response_norm_verification(z_i):
            return {
                "M": M_i, "t": t_i, "w": w_i,
                "c": c_i, "z": z_i
            }

    raise RuntimeError("Authentication rejection sampling exhausted")

# ============================================================
# OPERATION 15: INDIVIDUAL SIGNATURE VERIFICATION T_ind
# ============================================================
def individual_signature_verification(req):
    if not response_norm_verification(req["z"]):
        return False

    c_check = sparse_challenge_generation(req["M"] + encode_polyvec(req["w"]))
    if not np.array_equal(c_check, req["c"]):
        return False

    lhs = (
        module_lattice_matvec(A_sig, req["z"])
        - challenge_times_vector(req["c"], req["t"])
    ) % q_s

    return np.array_equal(lhs, req["w"] % q_s)

# ============================================================
# OPERATION 16: RANDOMIZED BATCH AGGREGATION T_agg
# ============================================================
def randomized_batch_aggregation(requests, local_rng):
    alpha = local_rng.integers(
        1, Q_B, size=len(requests), dtype=np.int64
    )

    Z = np.zeros((l_s, N_s), dtype=np.int64)
    T = np.zeros((k_s, N_s), dtype=np.int64)
    W = np.zeros((k_s, N_s), dtype=np.int64)

    for alpha_i, req in zip(alpha, requests):
        Z = (Z + int(alpha_i) * req["z"]) % q_s
        c_t = challenge_times_vector(req["c"], req["t"])
        T = (T + int(alpha_i) * c_t) % q_s
        W = (W + int(alpha_i) * req["w"]) % q_s

    return Z, T, W

# ============================================================
# OPERATION 17: BATCH VERIFICATION T_batch
# ============================================================
def batch_verification(requests, local_rng, repetitions=r_B):
    # Cheap per-request checks
    for req in requests:
        if not response_norm_verification(req["z"]):
            return False
        c_check = sparse_challenge_generation(req["M"] + encode_polyvec(req["w"]))
        if not np.array_equal(c_check, req["c"]):
            return False

    # r_B randomized aggregate checks
    for _ in range(repetitions):
        Z, T, W = randomized_batch_aggregation(requests, local_rng)
        lhs = (module_lattice_matvec(A_sig, Z) - T) % q_s
        if not np.array_equal(lhs, W):
            return False

    return True

def corrupt_request(req):
    bad = {}
    for key, value in req.items():
        bad[key] = value.copy() if isinstance(value, np.ndarray) else value
    bad["z"][0, 0] = (bad["z"][0, 0] + 1) % q_s
    return bad

# ============================================================
# OPERATION 18: RECURSIVE INVALID-REQUEST LOCALIZATION T_loc
# ============================================================
def recursive_invalid_localization(
        requests, local_rng, offset=0, depth=0, stats=None):
    if stats is None:
        stats = {"batch_calls": 0, "max_depth": 0, "invalid": []}

    stats["batch_calls"] += 1
    stats["max_depth"] = max(stats["max_depth"], depth)

    if batch_verification(requests, local_rng):
        return stats

    if len(requests) == 1:
        if not individual_signature_verification(requests[0]):
            stats["invalid"].append(offset)
        return stats

    mid = len(requests) // 2
    recursive_invalid_localization(
        requests[:mid], local_rng, offset, depth + 1, stats)
    recursive_invalid_localization(
        requests[mid:], local_rng, offset + mid, depth + 1, stats)
    return stats

# ============================================================
# BENCHMARK ENGINE
# ============================================================
def benchmark(name, notation, function, inner=INNER_LOOPS):
    samples_us = []

    # warm-up
    function()

    for _ in range(REPETITIONS):
        start = time.perf_counter_ns()
        for _ in range(inner):
            function()
        stop = time.perf_counter_ns()
        samples_us.append((stop - start) / 1000.0 / inner)

    return {
        "No": 0,
        "Operation": name,
        "Notation": notation,
        "Mean_us": statistics.mean(samples_us),
        "SD_us": statistics.stdev(samples_us) if len(samples_us) > 1 else 0.0,
        "Median_us": statistics.median(samples_us),
        "Min_us": min(samples_us),
        "Max_us": max(samples_us)
    }

# ============================================================
# MAIN
# ============================================================
def main():
    # MLWR test variables
    a = rng.integers(0, q, N, dtype=np.int64)
    b = rng.integers(0, q, N, dtype=np.int64)
    r = rng.integers(0, q, N, dtype=np.int64)
    hint = cha_function(a)

    xor_a = rng.integers(0, 256, 1024, dtype=np.uint8)
    xor_b = rng.integers(0, 256, 1024, dtype=np.uint8)

    # One valid authentication request
    req = authentication_sign(0, np.random.default_rng(SEED + 1000))

    # Inputs for additional signature-operation benchmarks
    sig_secret = rng.integers(
        -eta_s, eta_s + 1, size=(l_s, N_s), dtype=np.int64
    )
    sig_public = module_lattice_matvec(A_sig, sig_secret % q_s)
    sig_message = H(b"DTLBA-signature-benchmark") + encode_polyvec(sig_public)
    sig_challenge = sparse_challenge_generation(
        sig_message + encode_polyvec(req["w"])
    )
    sig_cv_rhs = challenge_vector_multiplication(
        sig_challenge, sig_secret % q_s
    )
    sig_vec_a = rng.integers(0, q_s, size=(l_s, N_s), dtype=np.int64)
    sig_vec_b = rng.integers(0, q_s, size=(l_s, N_s), dtype=np.int64)

    # Batch generated OUTSIDE timed verification
    requests = [
        authentication_sign(i, np.random.default_rng(SEED + 2000 + i))
        for i in range(B)
    ]

    # Five invalid requests for localization benchmark
    invalid_requests = []
    for req_i in requests:
        invalid_requests.append({
            key: (value.copy() if isinstance(value, np.ndarray) else value)
            for key, value in req_i.items()
        })
    invalid_indices = [5, 25, 50, 75, 95]
    for idx in invalid_indices:
        invalid_requests[idx] = corrupt_request(invalid_requests[idx])

    rows = []

    rows.append(benchmark(
        "Polynomial Multiplication", "T_pm",
        lambda: polynomial_multiplication(a, b, q)))

    rows.append(benchmark(
        "Polynomial Addition/Subtraction", "T_add",
        lambda: (
            polynomial_addition(a, b, q),
            polynomial_subtraction(a, b, q))))

    rows.append(benchmark(
        "MLWR Rounding", "T_rnd",
        lambda: mlwr_rounding(a)))

    rows.append(benchmark(
        "Scalar Multiplication", "T_sm",
        lambda: scalar_multiplication(31337, a, q)))

    rows.append(benchmark(
        "Share Polynomial Generation", "T_spg",
        lambda: share_polynomial_generation(a, r)))

    rows.append(benchmark(
        "Cha Function", "T_cha",
        lambda: cha_function(a)))

    rows.append(benchmark(
        "Mod2 Function", "T_mod2",
        lambda: mod2_function(a, hint)))

    rows.append(benchmark(
        "Hash Computation", "T_h",
        lambda: hash_computation(a.tobytes())))

    rows.append(benchmark(
        "AES-GCM Encryption/Decryption", "T_E/D",
        aes_gcm_enc_dec, inner=1))

    rows.append(benchmark(
        "Fuzzy Extractor Gen/Rep", "T_FE",
        fuzzy_extractor_gen_rep, inner=1))

    rows.append(benchmark(
        "XOR Operation", "T_xor",
        lambda: xor_operation(xor_a, xor_b)))

    rows.append(benchmark(
        "Module-Lattice Matrix-Vector Multiplication", "T_mv",
        lambda: module_lattice_matvec(A_sig, req["z"]), inner=1))

    rows.append(benchmark(
        "Sparse Challenge Generation", "T_ch",
        lambda: sparse_challenge_generation(
            req["M"] + encode_polyvec(req["w"]))))

    rows.append(benchmark(
        "Response/Norm Verification", "T_norm",
        lambda: response_norm_verification(req["z"])))

    rows.append(benchmark(
        "Individual Signature Verification", "T_ind",
        lambda: individual_signature_verification(req), inner=1))

    agg_counter = {"i": 0}
    def timed_aggregation():
        agg_counter["i"] += 1
        rr = np.random.default_rng(SEED + 300000 + agg_counter["i"])
        return randomized_batch_aggregation(requests, rr)

    rows.append(benchmark(
        f"Randomized Batch Aggregation (B={B})", "T_agg(B)",
        timed_aggregation, inner=1))

    batch_counter = {"i": 0}
    def timed_batch():
        batch_counter["i"] += 1
        rr = np.random.default_rng(SEED + 400000 + batch_counter["i"])
        return batch_verification(requests, rr, r_B)

    rows.append(benchmark(
        f"Batch Verification (B={B}, r_B={r_B})", "T_batch(B,r_B)",
        timed_batch, inner=1))

    loc_counter = {"i": 0}
    def timed_localization():
        loc_counter["i"] += 1
        rr = np.random.default_rng(SEED + 500000 + loc_counter["i"])
        return recursive_invalid_localization(invalid_requests, rr)

    rows.append(benchmark(
        f"Recursive Invalid-Request Localization (B={B}, invalid=5)",
        "T_loc(B,m)", timed_localization, inner=1))


    # ------------------------------------------------------------
    # Operations 19--22: signature-specific measurements
    # ------------------------------------------------------------
    rows.append(benchmark(
        "Challenge-Vector Multiplication", "T_cv",
        lambda: challenge_vector_multiplication(
            sig_challenge, sig_secret % q_s), inner=1))

    rows.append(benchmark(
        "Polynomial-Vector Addition", "T_vadd",
        lambda: vector_addition(sig_vec_a, sig_vec_b)))

    rows.append(benchmark(
        "Module/Vector Equality Comparison", "T_cmp",
        lambda: vector_comparison(req["w"], req["w"])))

    sig_counter = {"i": 0}
    def timed_signature_generation():
        sig_counter["i"] += 1
        rr = np.random.default_rng(SEED + 800000 + sig_counter["i"])
        return complete_signature_generation(sig_message, sig_secret, rr)

    rows.append(benchmark(
        "Complete Signature Generation", "T_sig",
        timed_signature_generation, inner=1))

    # numbering
    for i, row in enumerate(rows, start=1):
        row["No"] = i

    # correctness checks
    if not individual_signature_verification(req):
        raise RuntimeError("Individual authentication self-test failed")
    if not batch_verification(
            requests, np.random.default_rng(SEED + 600000), r_B):
        raise RuntimeError("Batch authentication self-test failed")

    loc = recursive_invalid_localization(
        invalid_requests, np.random.default_rng(SEED + 700000))
    if sorted(loc["invalid"]) != invalid_indices:
        raise RuntimeError(
            f"Localization self-test failed: {loc['invalid']}")

    # CSV
    csv_name = "DTLBA_22_operation_costs.csv"
    with open(csv_name, "w", newline="", encoding="utf-8") as f:
        fields = [
            "No", "Operation", "Notation", "Mean_us", "SD_us",
            "Median_us", "Min_us", "Max_us"
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Text report
    txt_name = "DTLBA_22_operation_costs.txt"
    with open(txt_name, "w", encoding="utf-8") as f:
        f.write("DTLBA Unified 22-Operation Cost Benchmark Including T_E/D and T_FE\n")
        f.write("=" * 88 + "\n")
        f.write(f"Python: {platform.python_version()}\n")
        f.write(f"NumPy: {np.__version__}\n")
        f.write(f"Platform: {platform.platform()}\n")
        f.write(f"Seed: {SEED}\n")
        f.write(f"Repetitions: {REPETITIONS}\n")
        f.write(f"Batch size B: {B}\n")
        f.write(f"Randomized batch repetitions r_B: {r_B}\n\n")

        f.write(
            f"{'No':<4}{'Notation':<17}{'Operation':<51}"
            f"{'Mean (us)':>13}{'SD (us)':>13}\n")
        f.write("-" * 98 + "\n")
        for x in rows:
            f.write(
                f"{x['No']:<4}{x['Notation']:<17}"
                f"{x['Operation'][:50]:<51}"
                f"{x['Mean_us']:>13.4f}{x['SD_us']:>13.4f}\n")

        f.write("\nSELF-TEST\n")
        f.write("Individual verification: PASS\n")
        f.write("Batch verification: PASS\n")
        f.write(
            "Invalid localization: PASS; detected "
            + str(sorted(loc["invalid"])) + "\n")

        f.write("\nIMPORTANT INTERPRETATION\n")
        f.write(
            "Operations 15-18 and 22 are composite operations. Their measured "
            "times already contain lower-level operations and must not be "
            "added again to primitive-operation totals.\n")
        f.write(
            "The fuzzy extractor is a self-contained Gen/Rep benchmark "
            "demonstrator based on Hamming-noise correction and SHA3-256; "
            "it is not a claim of a standardized biometric FE.\n")
        f.write(
            "Cha, Mod2 and share generation are explicitly defined reference "
            "operations for this computational benchmark.\n")

    # Console
    print("\nDTLBA - ALL 22 COMPUTATIONAL OPERATIONS")
    print("=" * 100)
    print(
        f"{'No':<4}{'Notation':<17}{'Operation':<51}"
        f"{'Mean (us)':>13}{'SD (us)':>13}")
    print("-" * 100)
    for x in rows:
        print(
            f"{x['No']:<4}{x['Notation']:<17}"
            f"{x['Operation'][:50]:<51}"
            f"{x['Mean_us']:>13.4f}{x['SD_us']:>13.4f}")
    print("=" * 100)
    print("Individual verification self-test: PASS")
    print("Batch verification self-test: PASS")
    print("Localization self-test: PASS ->", sorted(loc["invalid"]))
    print("Saved:", csv_name)
    print("Saved:", txt_name)

if __name__ == "__main__":
    main()
