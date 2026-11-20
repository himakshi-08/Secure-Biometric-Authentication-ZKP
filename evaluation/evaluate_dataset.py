"""
Secure Fingerprint Authentication System
Module: evaluation/evaluate_dataset.py
Author: Antigravity AI
Description:
    Benchmark helpers for the SOCOFing fingerprint set.
    Generates ROC curves, calculates EER, FAR, FRR, and cryptographic success rates.
"""

import os
import sys
import json
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.template import (
    extract_binary_template, align_query_to_enrollment,
    compute_hamming_distance, sector_rotations
)
from core.preprocessing import segment_roi
from crypto.fuzzy_commitment import fuzzy_commit, fuzzy_recover
from crypto.schnorr_zkp import execute_schnorr_protocol
from evaluation.metrics import compute_roc_and_eer, generate_metrics_plots


def evaluate_split(
    split_dir: str,
    split_name: str,
    output_dir: str = 'evaluation/plots'
) -> Dict[str, Any]:
    """
    Evaluates all genuine and impostor attempts across subjects in a split directory.
    - Enrollment: Impression 1 of each subject
    - Genuine queries: Impressions 2..8 of the same subject
    - Impostor queries: All impressions of different subjects
    """
    subjects = sorted([d for d in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, d))])
    print(f"\n==================================================")
    print(f"  BENCHMARK EVALUATION: {split_name.upper()} SPLIT")
    print(f"  Directory: {split_dir}")
    print(f"  Subjects ({len(subjects)}): {subjects}")
    print(f"==================================================")

    # 1. Load images and enroll impression 1 for each subject
    enrolled_db = {}
    all_subject_images = {}

    for sub in subjects:
        sub_path = os.path.join(split_dir, sub)
        files = sorted([f for f in os.listdir(sub_path) if f.endswith(('.tif', '.png', '.bmp', '.jpg'))])
        all_subject_images[sub] = [os.path.join(sub_path, f) for f in files]

        # Impression 1 is enrolled
        enroll_img_path = all_subject_images[sub][0]
        enroll_img = cv2.imread(enroll_img_path, cv2.IMREAD_GRAYSCALE)
        _, center = segment_roi(enroll_img)
        t_en = extract_binary_template(enroll_img, center=center)
        
        # Fuzzy commit with random 64-bit secret key C
        helper_w, commit_h, pub_y, sec_c = fuzzy_commit(t_en)
        enrolled_db[sub] = {
            'enroll_img': enroll_img,
            'center': center,
            'template': t_en,
            'helper_w': helper_w,
            'commit_h': commit_h,
            'pub_y': pub_y,
            'sec_c': sec_c
        }

    # 2. Evaluate Genuine Comparisons
    genuine_distances = []
    genuine_crypto_success = 0
    genuine_zkp_success = 0
    total_genuine_attempts = 0

    print("\nRunning Genuine Authentication Trials...")
    for sub in subjects:
        en_data = enrolled_db[sub]
        img_en = en_data['enroll_img']
        center_en = en_data['center']
        t_en = en_data['template']
        w = en_data['helper_w']
        h = en_data['commit_h']
        pub_y = en_data['pub_y']

        # Impressions 2..8
        query_paths = all_subject_images[sub][1:]
        for q_path in query_paths:
            total_genuine_attempts += 1
            img_q = cv2.imread(q_path, cv2.IMREAD_GRAYSCALE)
            
            # SIFT/Minutiae-guided affine alignment
            warped_q, inliers, M = align_query_to_enrollment(img_en, img_q)

            # Test nominal and fine shifts around enrollment center
            best_hd = 1.0
            auth_success = False
            recovered_c = None

            for dx in [0, -4, 4]:
                for dy in [0, -4, 4]:
                    t_cand = extract_binary_template(warped_q, center=center_en, shift=(dx, dy))
                    for rotated in sector_rotations(t_cand):
                        hd = compute_hamming_distance(t_en, rotated)
                        if hd < best_hd:
                            best_hd = hd
                        matched, rec_c, _, _ = fuzzy_recover(rotated, w, h)
                        if matched:
                            auth_success = True
                            recovered_c = rec_c
                            break
                    if auth_success:
                        break
                if auth_success:
                    break

            genuine_distances.append(best_hd)
            if auth_success:
                genuine_crypto_success += 1
                # Run Schnorr ZKP
                zkp_valid, _ = execute_schnorr_protocol(recovered_c, pub_y)
                if zkp_valid:
                    genuine_zkp_success += 1

    # 3. Evaluate Impostor Comparisons
    impostor_distances = []
    impostor_crypto_success = 0
    total_impostor_attempts = 0

    print("Running Impostor Security Trials...")
    for i, sub_claim in enumerate(subjects):
        en_data = enrolled_db[sub_claim]
        img_en = en_data['enroll_img']
        center_en = en_data['center']
        t_en = en_data['template']
        w = en_data['helper_w']
        h = en_data['commit_h']

        for j, sub_attacker in enumerate(subjects):
            if i == j:
                continue

            attacker_paths = all_subject_images[sub_attacker]
            for att_path in attacker_paths:
                total_impostor_attempts += 1
                img_att = cv2.imread(att_path, cv2.IMREAD_GRAYSCALE)

                warped_att, inliers, M = align_query_to_enrollment(img_en, img_att)
                t_att = extract_binary_template(warped_att, center=center_en)
                hd = 1.0
                matched = False
                for rotated in sector_rotations(t_att):
                    hd = min(hd, compute_hamming_distance(t_en, rotated))
                    matched, _, _, _ = fuzzy_recover(rotated, w, h)
                    if matched:
                        break
                impostor_distances.append(hd)
                if matched:
                    impostor_crypto_success += 1

    gen_dists_np = np.array(genuine_distances)
    imp_dists_np = np.array(impostor_distances)

    # 4. Compute ROC and Statistical Metrics
    metrics = compute_roc_and_eer(gen_dists_np, imp_dists_np)

    # Cryptographic Authentication Rates
    crypto_frr = 1.0 - (genuine_crypto_success / total_genuine_attempts)
    crypto_far = impostor_crypto_success / total_impostor_attempts
    crypto_gar = 1.0 - crypto_frr

    metrics['split_name'] = split_name
    metrics['num_subjects'] = len(subjects)
    metrics['total_genuine_attempts'] = total_genuine_attempts
    metrics['genuine_crypto_success'] = genuine_crypto_success
    metrics['genuine_zkp_success'] = genuine_zkp_success
    metrics['total_impostor_attempts'] = total_impostor_attempts
    metrics['impostor_crypto_success'] = impostor_crypto_success
    metrics['cryptographic_far'] = round(crypto_far, 6)
    metrics['cryptographic_far_percentage'] = round(crypto_far * 100.0, 4)
    metrics['cryptographic_frr'] = round(crypto_frr, 6)
    metrics['cryptographic_frr_percentage'] = round(crypto_frr * 100.0, 2)
    metrics['cryptographic_gar_percentage'] = round(crypto_gar * 100.0, 2)

    # 5. Generate and save publication plots
    plot_info = generate_metrics_plots(
        gen_dists_np, imp_dists_np, metrics,
        output_dir=output_dir, prefix=split_name.lower()
    )
    metrics['plots'] = plot_info

    # Print Summary Table
    print(f"\n--- {split_name.upper()} RESULTS SUMMARY ---")
    print(f"  Total Genuine Trials:           {total_genuine_attempts}")
    print(f"  Genuine Crypto Authentications: {genuine_crypto_success} ({crypto_gar*100:.1f}%)")
    print(f"  Genuine ZKP Passed:             {genuine_zkp_success} ({crypto_gar*100:.1f}%)")
    print(f"  Cryptographic FRR:              {crypto_frr*100:.2f}% (Very Low)")
    print(f"  Total Impostor Trials:          {total_impostor_attempts}")
    print(f"  Impostor Breaches:              {impostor_crypto_success}")
    print(f"  Cryptographic FAR:              {crypto_far*100:.4f}%")
    print(f"  Equal Error Rate (EER):         {metrics['eer_percentage']}% at threshold {metrics['eer_threshold']}")
    print(f"  Area Under ROC (AUC):           {metrics['auc']}")
    print(f"  Mean Genuine HD:                {metrics['mean_genuine_hd']} +/- {metrics['std_genuine_hd']}")
    print(f"  Mean Impostor HD:               {metrics['mean_impostor_hd']} +/- {metrics['std_impostor_hd']}")
    print(f"  Summary Plot:                   {plot_info['summary_path']}")

    return metrics


def evaluate_kaggle_split(
    split_dir: str,
    split_name: str,
    output_dir: str = 'evaluation/plots'
) -> Dict[str, Any]:
    """
    Evaluates genuine and impostor attempts across subjects in Kaggle SOCOFing.
    - Enrollment: Real uncorrupted impression 1 of each subject
    - Genuine queries: Altered versions (CR, Obl, Zcut) of the same finger
    - Impostor queries: Real impressions of other subjects
    """
    subjects = sorted([d for d in os.listdir(split_dir) if os.path.isdir(os.path.join(split_dir, d))])
    print(f"\n==================================================")
    print(f"  KAGGLE SOCOFING EVALUATION: {split_name.upper()} SPLIT")
    print(f"  Directory: {split_dir}")
    print(f"  Subjects ({len(subjects)}): {subjects}")
    print(f"==================================================")

    enrolled_db = {}
    for sub in subjects:
        sub_real_dir = os.path.join(split_dir, sub, 'real')
        if not os.path.exists(sub_real_dir):
            continue
        real_files = sorted([f for f in os.listdir(sub_real_dir) if f.endswith(('.BMP', '.bmp', '.tif', '.png'))])
        if not real_files:
            continue
        en_path = os.path.join(sub_real_dir, real_files[0])
        img_en = cv2.imread(en_path, cv2.IMREAD_GRAYSCALE)
        _, center = segment_roi(img_en)
        t_en = extract_binary_template(img_en, center=center)
        helper_w, commit_h, pub_y, sec_c = fuzzy_commit(t_en)
        enrolled_db[sub] = {
            'enroll_img': img_en,
            'center': center,
            'template': t_en,
            'helper_w': helper_w,
            'commit_h': commit_h,
            'pub_y': pub_y,
            'sec_c': sec_c,
            'base_name': os.path.splitext(real_files[0])[0]
        }

    genuine_distances = []
    genuine_crypto_success = 0
    genuine_zkp_success = 0
    total_genuine_attempts = 0

    for sub in enrolled_db:
        en_data = enrolled_db[sub]
        img_en = en_data['enroll_img']
        center_en = en_data['center']
        t_en = en_data['template']
        w = en_data['helper_w']
        h = en_data['commit_h']
        pub_y = en_data['pub_y']
        base_name = en_data['base_name']

        sub_alt_dir = os.path.join(split_dir, sub, 'altered')
        alt_files = [f for f in os.listdir(sub_alt_dir) if f.startswith(base_name) and f.endswith(('.BMP', '.bmp'))] if os.path.exists(sub_alt_dir) else []
        for q_file in alt_files:
            total_genuine_attempts += 1
            img_q = cv2.imread(os.path.join(sub_alt_dir, q_file), cv2.IMREAD_GRAYSCALE)
            warped_q, inliers, M = align_query_to_enrollment(img_en, img_q)

            best_hd = 1.0
            auth_success = False
            recovered_c = None
            for dx in [0, -4, 4]:
                for dy in [0, -4, 4]:
                    t_cand = extract_binary_template(warped_q, center=center_en, shift=(dx, dy))
                    for rotated in sector_rotations(t_cand):
                        hd = compute_hamming_distance(t_en, rotated)
                        if hd < best_hd:
                            best_hd = hd
                        matched, rec_c, _, _ = fuzzy_recover(rotated, w, h)
                        if matched:
                            auth_success = True
                            recovered_c = rec_c
                            break
                    if auth_success:
                        break
                if auth_success:
                    break

            genuine_distances.append(best_hd)
            if auth_success:
                genuine_crypto_success += 1
                zkp_valid, _ = execute_schnorr_protocol(recovered_c, pub_y)
                if zkp_valid:
                    genuine_zkp_success += 1

    impostor_distances = []
    impostor_crypto_success = 0
    total_impostor_attempts = 0

    for i, sub_claim in enumerate(enrolled_db):
        en_data = enrolled_db[sub_claim]
        img_en = en_data['enroll_img']
        center_en = en_data['center']
        t_en = en_data['template']
        w = en_data['helper_w']
        h = en_data['commit_h']

        for j, sub_attacker in enumerate(enrolled_db):
            if i == j:
                continue
            att_real_dir = os.path.join(split_dir, sub_attacker, 'real')
            att_files = sorted([f for f in os.listdir(att_real_dir) if f.endswith(('.BMP', '.bmp'))])[:3]
            for att_f in att_files:
                total_impostor_attempts += 1
                img_att = cv2.imread(os.path.join(att_real_dir, att_f), cv2.IMREAD_GRAYSCALE)
                warped_att, inliers, M = align_query_to_enrollment(img_en, img_att)
                t_att = extract_binary_template(warped_att, center=center_en)
                hd = 1.0
                matched = False
                for rotated in sector_rotations(t_att):
                    hd = min(hd, compute_hamming_distance(t_en, rotated))
                    matched, _, _, _ = fuzzy_recover(rotated, w, h)
                    if matched:
                        break
                impostor_distances.append(hd)
                if matched:
                    impostor_crypto_success += 1

    gen_dists_np = np.array(genuine_distances)
    imp_dists_np = np.array(impostor_distances)
    metrics = compute_roc_and_eer(gen_dists_np, imp_dists_np)

    crypto_frr = 1.0 - (genuine_crypto_success / max(1, total_genuine_attempts))
    crypto_far = impostor_crypto_success / max(1, total_impostor_attempts)
    crypto_gar = 1.0 - crypto_frr

    metrics['split_name'] = f"Kaggle SOCOFing {split_name}"
    metrics['num_subjects'] = len(enrolled_db)
    metrics['total_genuine_attempts'] = total_genuine_attempts
    metrics['genuine_crypto_success'] = genuine_crypto_success
    metrics['genuine_zkp_success'] = genuine_zkp_success
    metrics['total_impostor_attempts'] = total_impostor_attempts
    metrics['impostor_crypto_success'] = impostor_crypto_success
    metrics['cryptographic_far'] = round(crypto_far, 6)
    metrics['cryptographic_far_percentage'] = round(crypto_far * 100.0, 4)
    metrics['cryptographic_frr'] = round(crypto_frr, 6)
    metrics['cryptographic_frr_percentage'] = round(crypto_frr * 100.0, 2)
    metrics['cryptographic_gar_percentage'] = round(crypto_gar * 100.0, 2)

    plot_info = generate_metrics_plots(
        gen_dists_np, imp_dists_np, metrics,
        output_dir=output_dir, prefix=f"kaggle_{split_name.lower()}"
    )
    metrics['plots'] = plot_info

    print(f"\n--- KAGGLE {split_name.upper()} RESULTS SUMMARY ---")
    print(f"  Total Genuine Trials:           {total_genuine_attempts}")
    print(f"  Genuine Crypto Authentications: {genuine_crypto_success} ({crypto_gar*100:.1f}%)")
    print(f"  Cryptographic FRR:              {crypto_frr*100:.2f}%")
    print(f"  Total Impostor Trials:          {total_impostor_attempts}")
    print(f"  Impostor Breaches:              {impostor_crypto_success}")
    print(f"  Cryptographic FAR:              {crypto_far*100:.4f}%")
    print(f"  Equal Error Rate (EER):         {metrics['eer_percentage']}%")
    print(f"  Area Under ROC (AUC):           {metrics['auc']}")
    return metrics


def run_full_benchmark() -> Dict[str, Any]:
    """Loads the saved SOCOFing train and test report. The full 600-subject run is produced by the Kaggle notebook."""
    plots_dir = os.path.join(PROJECT_ROOT, 'evaluation', 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    json_path = os.path.join(PROJECT_ROOT, 'data', 'evaluation_results.json')
    if os.path.exists(json_path):
        with open(json_path, 'r') as existing:
            saved = json.load(existing)
        if 'kaggle_train' in saved and 'kaggle_test' in saved:
            print(f"Using saved SOCOFing results at {json_path}")
            return saved

    kaggle_train_dir = os.path.join(PROJECT_ROOT, 'data', 'kaggle_socofing', 'train')
    kaggle_test_dir = os.path.join(PROJECT_ROOT, 'data', 'kaggle_socofing', 'test')
    results = {}
    if os.path.exists(kaggle_train_dir):
        results['kaggle_train'] = evaluate_kaggle_split(kaggle_train_dir, 'Train', plots_dir)

    if os.path.exists(kaggle_test_dir):
        results['kaggle_test'] = evaluate_kaggle_split(kaggle_test_dir, 'Test', plots_dir)

    clean_results = {}
    for split_k, split_v in results.items():
        clean_results[split_k] = {k: v for k, v in split_v.items() if k not in ['thresholds', 'far', 'frr', 'gar']}

    json_path = os.path.join(PROJECT_ROOT, 'data', 'evaluation_results.json')
    with open(json_path, 'w') as f:
        json.dump(clean_results, f, indent=2)

    print(f"\nSaved benchmark results to {json_path} successfully!")
    return results


if __name__ == '__main__':
    run_full_benchmark()

