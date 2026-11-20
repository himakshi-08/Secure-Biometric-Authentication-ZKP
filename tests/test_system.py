"""Integration tests for end-to-end system flow."""
import os
import cv2
import numpy as np
import pytest

from core.preprocessing import segment_roi
from core.template import extract_binary_template
from crypto.fuzzy_commitment import fuzzy_commit, fuzzy_recover
from crypto.schnorr_zkp import execute_schnorr_protocol
from crypto.database import store_enrolled_user, get_enrolled_user, delete_enrolled_user


def test_kaggle_socofing_end_to_end():
    """Validates enrollment, genuine match with altered query, and impostor rejection on Kaggle SOCOFing."""
    en_path = 'data/kaggle_socofing/real/100__M_Left_index_finger.BMP'
    alt_path = 'data/kaggle_socofing/altered/100__M_Left_index_finger_CR.BMP'
    imp_path = 'data/kaggle_socofing/real/101__M_Left_index_finger.BMP'

    img_en = cv2.imread(en_path, cv2.IMREAD_GRAYSCALE)
    assert img_en is not None

    _, center_en = segment_roi(img_en)
    t_en = extract_binary_template(img_en, center=center_en)

    helper_w, commit_h, pub_y, sec_c = fuzzy_commit(t_en)
    username = "kaggle_test_user_100"
    store_enrolled_user(username, helper_w, commit_h, pub_y, center_en)

    # 1. Genuine Verification (Altered image with rotation)
    img_alt = cv2.imread(alt_path, cv2.IMREAD_GRAYSCALE)
    auth_ok = False
    rec_key = None
    for dx in [0, -4, 4, -8, 8]:
        for dy in [0, -4, 4, -8, 8]:
            t_cand = extract_binary_template(img_alt, center=center_en, shift=(dx, dy))
            matched, c_recovered, _, _ = fuzzy_recover(t_cand, helper_w, commit_h)
            if matched:
                auth_ok = True
                rec_key = c_recovered
                break
        if auth_ok:
            break

    assert auth_ok is True, "Kaggle altered genuine fingerprint failed to authenticate"
    assert rec_key == sec_c

    # Schnorr ZKP
    zkp_valid, transcript = execute_schnorr_protocol(rec_key, pub_y)
    assert zkp_valid is True

    # 2. Impostor Verification (Subject 101)
    img_imp = cv2.imread(imp_path, cv2.IMREAD_GRAYSCALE)
    t_imp = extract_binary_template(img_imp, center=center_en)
    imp_matched, _, _, _ = fuzzy_recover(t_imp, helper_w, commit_h)
    assert imp_matched is False, "Kaggle impostor was falsely accepted!"

    # Clean up
    delete_enrolled_user(username)


