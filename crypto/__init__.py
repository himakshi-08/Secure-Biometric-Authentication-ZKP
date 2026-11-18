"""Cryptographic primitives, Fuzzy Commitment, and Schnorr ZKP."""
from .ecc import ecc_encode, ecc_decode
from .fuzzy_commitment import (
    generate_secret_key, compute_sha256,
    fuzzy_commit, fuzzy_recover
)
from .schnorr_zkp import (
    SchnorrProver, SchnorrVerifier,
    secret_to_private_key, compute_public_key,
    execute_schnorr_protocol, P, Q, G
)
from .database import (
    init_database, store_enrolled_user, get_enrolled_user,
    list_enrolled_users, delete_enrolled_user, inspect_database_security
)

__all__ = [
    'ecc_encode', 'ecc_decode',
    'generate_secret_key', 'compute_sha256',
    'fuzzy_commit', 'fuzzy_recover',
    'SchnorrProver', 'SchnorrVerifier',
    'secret_to_private_key', 'compute_public_key',
    'execute_schnorr_protocol', 'P', 'Q', 'G',
    'init_database', 'store_enrolled_user', 'get_enrolled_user',
    'list_enrolled_users', 'delete_enrolled_user', 'inspect_database_security'
]

