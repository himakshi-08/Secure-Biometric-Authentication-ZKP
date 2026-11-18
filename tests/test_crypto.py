"""Unit tests for cryptographic modules (ECC, Fuzzy Commitment, Schnorr ZKP, Database)."""
import os
import numpy as np
import pytest

from crypto.ecc import ecc_encode, ecc_decode
from crypto.fuzzy_commitment import fuzzy_commit, fuzzy_recover, compute_sha256
from crypto.schnorr_zkp import (
    SchnorrProver, SchnorrVerifier,
    secret_to_private_key, compute_public_key,
    execute_schnorr_protocol
)
from crypto.database import (
    init_database, store_enrolled_user, get_enrolled_user,
    list_enrolled_users, delete_enrolled_user, inspect_database_security
)


def test_ecc_encoding_and_error_correction():
    secret_bytes = b'TEST_SEC'  # 8 bytes
    cw = ecc_encode(secret_bytes)
    assert len(cw) == 1024
    assert set(np.unique(cw)).issubset({0, 1})

    # Exact decode
    rec, corrs = ecc_decode(cw)
    assert rec == secret_bytes

    # Add 20% random error
    noise = np.random.binomial(1, 0.20, size=1024).astype(np.uint8)
    noisy_cw = cw ^ noise
    rec_noisy, corrs_noisy = ecc_decode(noisy_cw)
    assert rec_noisy == secret_bytes


def test_fuzzy_commitment_genuine_and_impostor():
    # Synthetic 1024-bit template
    template_b = np.random.randint(0, 2, size=1024, dtype=np.uint8)
    helper_w, commit_h, pub_y, sec_c = fuzzy_commit(template_b)

    assert len(helper_w) == 1024
    assert len(commit_h) == 64
    assert pub_y > 1

    # Genuine case with 15% bit error
    noise_gen = np.random.binomial(1, 0.15, size=1024).astype(np.uint8)
    template_gen = template_b ^ noise_gen
    matched_gen, rec_c_gen, cand_h_gen, diag_gen = fuzzy_recover(template_gen, helper_w, commit_h)
    assert matched_gen is True
    assert rec_c_gen == sec_c
    assert cand_h_gen == commit_h

    # Impostor case (independent random template)
    template_imp = np.random.randint(0, 2, size=1024, dtype=np.uint8)
    matched_imp, rec_c_imp, cand_h_imp, diag_imp = fuzzy_recover(template_imp, helper_w, commit_h)
    assert matched_imp is False
    assert rec_c_imp is None
    assert cand_h_imp != commit_h


def test_schnorr_zkp_protocol():
    secret_c = b'KEY_ZKP!'
    x = secret_to_private_key(secret_c)
    pub_y = compute_public_key(x)

    # 1. Honest Prover execution
    verified, transcript = execute_schnorr_protocol(secret_c, pub_y)
    assert verified is True
    assert transcript['match'] is True
    assert transcript['protocol_status'] == 'VERIFIED'

    # 2. Impostor Prover with wrong secret
    wrong_secret = b'WRONGKEY'
    wrong_x = secret_to_private_key(wrong_secret)
    prover_imp = SchnorrProver(wrong_x)
    verifier_honest = SchnorrVerifier(pub_y)

    t_imp = prover_imp.step1_commit()
    c_honest = verifier_honest.step2_challenge(t_imp)
    s_imp = prover_imp.step3_respond(c_honest)
    valid_imp, _ = verifier_honest.step4_verify(s_imp)
    assert valid_imp is False


def test_database_crud_and_security():
    init_database()
    username = "test_user_alpha"
    dummy_w = np.random.randint(0, 2, size=1024, dtype=np.uint8)
    dummy_h = "a" * 64
    dummy_y = 123456789
    center = (150, 150)

    # Store
    store_enrolled_user(username, dummy_w, dummy_h, dummy_y, center)

    # Retrieve
    user = get_enrolled_user(username)
    assert user is not None
    assert user['username'] == username
    assert np.array_equal(user['helper_data_w'], dummy_w)
    assert user['commitment_h'] == dummy_h
    assert user['public_key_y'] == dummy_y
    assert user['center'] == center

    # Audit security
    audit = inspect_database_security()
    assert audit['zero_biometric_leakage_verified'] is True

    # Delete
    deleted = delete_enrolled_user(username)
    assert deleted is True
    assert get_enrolled_user(username) is None

