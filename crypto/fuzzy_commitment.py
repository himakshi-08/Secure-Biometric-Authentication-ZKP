"""
Secure Fingerprint Authentication System
Module: crypto/fuzzy_commitment.py
Author: Antigravity AI
Description:
    Implements the Juels-Wattenberg Fuzzy Commitment Scheme:
    - Enrollment:
        C <- {0, 1}^64 (Secret Key)
        Codeword(C) = ECC_Encode(C) in {0, 1}^1024
        W = B XOR Codeword(C) (Helper Data)
        H = SHA-256(C) (Commitment Hash)
        Y = g^C mod p (Public Key for Schnorr ZKP)
        Store only (W, H, Y) in database.
    - Authentication / Recovery:
        Noisy Codeword = B' XOR W
        C' = ECC_Decode(Noisy Codeword)
        Check if SHA-256(C') == H.
"""

import os
import hashlib
import numpy as np
from typing import Tuple, Optional, Dict, Any

from .ecc import ecc_encode, ecc_decode
from .schnorr_zkp import secret_to_private_key, compute_public_key

# Public bit interleaver. A fixed permutation (not a secret) spreads a
# localized fingerprint change across the eight Hadamard blocks so the
# code can correct a burst instead of failing one block.
_interleave_rng = np.random.RandomState(20241120)
INTERLEAVE_INDEX = _interleave_rng.permutation(1024).astype(np.int32)


def interleave_bits(bits: np.ndarray) -> np.ndarray:
    """Applies the public interleaver to a 1024-bit template."""
    ordered = np.asarray(bits, dtype=np.uint8).reshape(-1)
    if ordered.size != 1024:
        raise ValueError(f"Expected 1024 bits, got {ordered.size}.")
    return ordered[INTERLEAVE_INDEX]


def deinterleave_bits(bits: np.ndarray) -> np.ndarray:
    """Inverts interleave_bits."""
    ordered = np.asarray(bits, dtype=np.uint8).reshape(-1)
    if ordered.size != 1024:
        raise ValueError(f"Expected 1024 bits, got {ordered.size}.")
    restored = np.empty(1024, dtype=np.uint8)
    restored[INTERLEAVE_INDEX] = ordered
    return restored


def reconstruct_template(helper_data_w: np.ndarray, secret_key_c: bytes) -> np.ndarray:
    """
    Rebuilds enrolled template B from helper data and a recovered secret.
    B is not stored; it is one-time-padded by the codeword.
    """
    codeword = ecc_encode(secret_key_c)
    interleaved = np.asarray(helper_data_w, dtype=np.uint8) ^ codeword
    return deinterleave_bits(interleaved)


def generate_secret_key(length_bytes: int = 8) -> bytes:
    """Generates a cryptographically secure random secret key C."""
    return os.urandom(length_bytes)


def compute_sha256(data: bytes) -> str:
    """Computes SHA-256 hex digest of input bytes."""
    return hashlib.sha256(data).hexdigest()


def fuzzy_commit(
    binary_template_b: np.ndarray,
    secret_key_c: Optional[bytes] = None
) -> Tuple[np.ndarray, str, int, bytes]:
    """
    Enrollment Phase (Step 5 in Architecture Diagram):
    Inputs:
        binary_template_b: Enrolled binary template B in {0, 1}^1024
        secret_key_c: Optional 8-byte secret key C (generated randomly if None)
    Outputs:
        helper_data_w: W = B XOR Codeword(C) in {0, 1}^1024
        commitment_h: H = SHA256(C) (hex string)
        public_key_y: Y = g^C mod p (integer)
        secret_key_c: Secret key C (kept private, NOT stored in DB)
    """
    if len(binary_template_b) != 1024:
        raise ValueError(f"Template B must have length 1024, got {len(binary_template_b)}.")

    if secret_key_c is None:
        secret_key_c = generate_secret_key(8)
    elif len(secret_key_c) != 8:
        raise ValueError(f"Secret key C must be 8 bytes, got {len(secret_key_c)}.")

    # 1. ECC Encode C -> Codeword(C)
    codeword = ecc_encode(secret_key_c)

    # 2. Helper data W = Interleave(B) XOR Codeword(C)
    helper_data_w = (interleave_bits(binary_template_b) ^ codeword).astype(np.uint8)

    # 3. Commitment H = SHA-256(C)
    commitment_h = compute_sha256(secret_key_c)

    # 4. Public Key Y = g^C mod p
    private_x = secret_to_private_key(secret_key_c)
    public_key_y = compute_public_key(private_x)

    return helper_data_w, commitment_h, public_key_y, secret_key_c


def fuzzy_recover(
    query_template_b_prime: np.ndarray,
    helper_data_w: np.ndarray,
    commitment_h: str
) -> Tuple[bool, Optional[bytes], str, Dict[str, Any]]:
    """
    Authentication Phase (Step 5 in Architecture Diagram):
    Inputs:
        query_template_b_prime: Query binary template B' in {0, 1}^1024
        helper_data_w: Stored helper data W in {0, 1}^1024
        commitment_h: Stored SHA-256 commitment hash H
    Outputs:
        is_matched: True if SHA-256(C') == H, False otherwise
        recovered_c: Recovered secret key C' (or None if invalid)
        candidate_h: SHA-256(C')
        diagnostics: Dictionary with correlation stats and bit difference count
    """
    if len(query_template_b_prime) != 1024 or len(helper_data_w) != 1024:
        raise ValueError("Templates B' and W must both be 1024 bits.")

    # 1. Noisy Codeword = Interleave(B') XOR W
    # W = Interleave(B) XOR Codeword(C), so this is
    # Interleave(B' XOR B) XOR Codeword(C).
    noisy_codeword = (interleave_bits(query_template_b_prime) ^ helper_data_w).astype(np.uint8)

    # 2. ECC Error-Correction to recover C'
    recovered_c, correlations = ecc_decode(noisy_codeword)

    # 3. Decision Diamond: Check if SHA256(C') == H
    candidate_h = compute_sha256(recovered_c)
    is_matched = (candidate_h.lower() == commitment_h.lower())

    estimated_flips = [max(0, int(round((128.0 - c) / 2.0))) for c in correlations]
    diagnostics = {
        'correlations': correlations,
        'mean_correlation': float(np.mean(correlations)),
        'min_correlation': float(np.min(correlations)),
        'estimated_bit_flips': int(sum(estimated_flips)),
        'candidate_hash': candidate_h,
        'expected_hash': commitment_h,
        'hash_match': is_matched
    }

    if is_matched:
        return True, recovered_c, candidate_h, diagnostics
    else:
        return False, None, candidate_h, diagnostics

