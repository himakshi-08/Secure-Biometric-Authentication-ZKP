"""
Secure Fingerprint Authentication System
Module: crypto/ecc.py
Author: Antigravity AI
Description:
    Implements Hadamard-128 Maximum Likelihood Error-Correcting Code.
    Encodes an 8-byte (64-bit) cryptographic secret key into a 1024-bit codeword.
    Each byte is mapped to a 128-bit Walsh-Hadamard codeword with minimum distance 64.
    Decodes using Fast Walsh-Hadamard correlation, capable of correcting up to
    31 bit errors per 128-bit block (24.2% bit error rate).
"""

import numpy as np
import scipy.linalg
from typing import Tuple, List


# Construct 128x128 Hadamard Matrix
HADAMARD_128 = scipy.linalg.hadamard(128).astype(np.float32)


def encode_byte_hadamard(byte_val: int) -> np.ndarray:
    """
    Encodes an 8-bit byte value (0..255) into a 128-bit codeword.
    Values 0..127 use rows of H_128 directly (+1 -> 0, -1 -> 1).
    Values 128..255 use the inverted rows (-H_128).
    """
    row_idx = byte_val % 128
    is_inverted = (byte_val >= 128)
    vector = HADAMARD_128[row_idx].copy()
    if is_inverted:
        vector = -vector
    # Map {+1, -1} to {0, 1}
    return ((1.0 - vector) / 2.0).astype(np.uint8)


def decode_byte_hadamard(received_128: np.ndarray) -> Tuple[int, float]:
    """
    Decodes 128 received noisy bits to an 8-bit byte (0..255)
    using maximum likelihood correlation.
    Returns:
        (decoded_byte, correlation_peak)
    """
    # Map {0, 1} to {+1, -1}
    v = 1.0 - 2.0 * received_128.astype(np.float32)
    # Correlation with all 128 Hadamard basis rows
    corr = np.dot(HADAMARD_128, v)
    max_idx = int(np.argmax(np.abs(corr)))
    peak_val = corr[max_idx]
    
    if peak_val >= 0:
        byte_out = max_idx
    else:
        byte_out = max_idx + 128
        
    return byte_out, float(np.abs(peak_val))


def ecc_encode(secret_bytes: bytes) -> np.ndarray:
    """
    Encodes an 8-byte secret key (64 bits) into a 1024-bit codeword.
    Output: np.ndarray of shape (1024,) with dtype uint8.
    """
    if len(secret_bytes) != 8:
        raise ValueError(f"Secret key must be exactly 8 bytes (64 bits), got {len(secret_bytes)} bytes.")
    
    codeword_blocks = [encode_byte_hadamard(b) for b in secret_bytes]
    return np.concatenate(codeword_blocks).astype(np.uint8)


def ecc_decode(codeword_bits: np.ndarray) -> Tuple[bytes, List[float]]:
    """
    Decodes a 1024-bit noisy codeword into an 8-byte secret key.
    Returns:
        recovered_secret: 8 bytes
        correlations: List of correlation peaks for each of the 8 blocks
    """
    if len(codeword_bits) != 1024:
        raise ValueError(f"Expected 1024 codeword bits, got {len(codeword_bits)} bits.")
    
    blocks = codeword_bits.reshape(8, 128)
    recovered_bytes = []
    correlations = []
    
    for i in range(8):
        byte_val, corr = decode_byte_hadamard(blocks[i])
        recovered_bytes.append(byte_val)
        correlations.append(corr)
        
    return bytes(recovered_bytes), correlations

