"""
Secure Fingerprint Authentication System
Module: evaluation/metrics.py
Author: Antigravity AI
Description:
    Computes biometric and cryptographic security metrics:
    - Genuine vs Impostor Hamming Distance distributions
    - False Acceptance Rate (FAR)
    - False Rejection Rate (FRR)
    - Genuine Acceptance Rate (GAR = 1 - FRR)
    - Equal Error Rate (EER) and optimal threshold
    - Area Under the Curve (AUC)
    - Cryptographic Verification Metrics
    - High-resolution plot generation (ROC Curve, DET/Error Curves, Score Distributions)
"""

import os
import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple


def compute_roc_and_eer(
    genuine_distances: np.ndarray,
    impostor_distances: np.ndarray,
    num_thresholds: int = 500
) -> Dict[str, Any]:
    """
    Computes biometric verification performance curves:
    - FAR(th) = P(impostor <= th)
    - FRR(th) = P(genuine > th)
    - GAR(th) = 1 - FRR(th)
    - EER = value where FAR == FRR
    """
    thresholds = np.linspace(0.0, 1.0, num_thresholds)
    far_list = []
    frr_list = []
    gar_list = []

    for th in thresholds:
        far = float(np.mean(impostor_distances <= th))
        frr = float(np.mean(genuine_distances > th))
        far_list.append(far)
        frr_list.append(frr)
        gar_list.append(1.0 - frr)

    far_arr = np.array(far_list)
    frr_arr = np.array(frr_list)

    # Find EER: minimum absolute difference between FAR and FRR
    diffs = np.abs(far_arr - frr_arr)
    eer_idx = int(np.argmin(diffs))
    eer = float((far_arr[eer_idx] + frr_arr[eer_idx]) / 2.0)
    eer_threshold = float(thresholds[eer_idx])

    # Compute AUC (Area Under ROC curve: GAR vs FAR)
    # Sort by FAR for numerical trapezoidal integration
    sorted_indices = np.argsort(far_arr)
    trapz_func = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
    auc = float(trapz_func(np.array(gar_list)[sorted_indices], far_arr[sorted_indices]))

    return {
        'thresholds': thresholds.tolist(),
        'far': far_list,
        'frr': frr_list,
        'gar': gar_list,
        'eer': eer,
        'eer_percentage': round(eer * 100.0, 3),
        'eer_threshold': round(eer_threshold, 4),
        'auc': round(auc, 4),
        'mean_genuine_hd': round(float(np.mean(genuine_distances)), 4),
        'std_genuine_hd': round(float(np.std(genuine_distances)), 4),
        'min_genuine_hd': round(float(np.min(genuine_distances)), 4),
        'max_genuine_hd': round(float(np.max(genuine_distances)), 4),
        'mean_impostor_hd': round(float(np.mean(impostor_distances)), 4),
        'std_impostor_hd': round(float(np.std(impostor_distances)), 4),
        'min_impostor_hd': round(float(np.min(impostor_distances)), 4),
        'max_impostor_hd': round(float(np.max(impostor_distances)), 4),
        'separation_margin': round(float(np.min(impostor_distances) - np.mean(genuine_distances)), 4)
    }


def generate_metrics_plots(
    genuine_distances: np.ndarray,
    impostor_distances: np.ndarray,
    metrics: Dict[str, Any],
    output_dir: str = 'evaluation/plots',
    prefix: str = 'benchmark'
) -> Dict[str, str]:
    """
    Generates publication-quality biometric performance plots and returns base64 strings and filepaths:
    1. Score Distributions (Genuine vs Impostor histograms)
    2. FAR and FRR vs Decision Threshold
    3. Receiver Operating Characteristic (ROC) Curve
    """
    os.makedirs(output_dir, exist_ok=True)
    plots = {}

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

    # Figure 1: Combined 3-Panel Evaluation Dashboard
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), dpi=150)

    # 1. Hamming Distance Distributions
    ax = axes[0]
    ax.hist(genuine_distances, bins=25, density=True, alpha=0.65, color='#10B981', label='Genuine (Intra-finger)', edgecolor='black', linewidth=0.5)
    ax.hist(impostor_distances, bins=25, density=True, alpha=0.65, color='#EF4444', label='Impostor (Inter-finger)', edgecolor='black', linewidth=0.5)
    ax.axvline(metrics['eer_threshold'], color='#6366F1', linestyle='--', linewidth=2, label=f"EER Cutoff ({metrics['eer_threshold']:.3f})")
    ax.set_title("Hamming Distance Distributions", fontsize=12, fontweight='bold')
    ax.set_xlabel("Normalized Hamming Distance (0.0 to 1.0)", fontsize=10)
    ax.set_ylabel("Probability Density", fontsize=10)
    ax.legend(loc='upper right', frameon=True)

    # 2. FAR & FRR vs Threshold
    ax = axes[1]
    th = metrics['thresholds']
    ax.plot(th, [x * 100 for x in metrics['far']], label='FAR (%)', color='#EF4444', linewidth=2)
    ax.plot(th, [x * 100 for x in metrics['frr']], label='FRR (%)', color='#3B82F6', linewidth=2)
    ax.plot(metrics['eer_threshold'], metrics['eer_percentage'], 'o', color='#F59E0B', markersize=8, label=f"EER = {metrics['eer_percentage']}%")
    ax.set_title("FAR & FRR vs. Decision Threshold", fontsize=12, fontweight='bold')
    ax.set_xlabel("Hamming Distance Threshold", fontsize=10)
    ax.set_ylabel("Error Rate (%)", fontsize=10)
    ax.set_ylim(-2, 102)
    ax.legend(loc='center right', frameon=True)

    # 3. ROC Curve (GAR vs FAR)
    ax = axes[2]
    ax.plot([x * 100 for x in metrics['far']], [x * 100 for x in metrics['gar']], color='#8B5CF6', linewidth=2.5, label=f"ROC (AUC = {metrics['auc']:.4f})")
    ax.plot([0, 100], [0, 100], linestyle=':', color='gray', label='Random Guess')
    ax.set_title("Receiver Operating Characteristic (ROC)", fontsize=12, fontweight='bold')
    ax.set_xlabel("False Acceptance Rate (FAR %)", fontsize=10)
    ax.set_ylabel("Genuine Acceptance Rate (GAR %)", fontsize=10)
    ax.set_xlim(-1, 101)
    ax.set_ylim(-1, 102)
    ax.legend(loc='lower right', frameon=True)

    plt.tight_layout()
    combined_path = os.path.join(output_dir, f"{prefix}_summary.png")
    plt.savefig(combined_path)

    # Encode to base64 for API / web rendering
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    plots['summary_b64'] = base64.b64encode(buf.read()).decode('utf-8')
    plots['summary_path'] = combined_path

    return plots
