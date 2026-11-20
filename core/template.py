"""
Secure Fingerprint Authentication System
Module: core/template.py
Author: Antigravity AI
Description:
    Implements fixed-length binary template generation (1024 bits),
    SIFT/minutiae-guided affine alignment, Hamming distance metrics,
    and visual binary template matrix rendering.
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict, Any


def build_gabor_bank(num_angles: int = 8, frequency: float = 0.10, ksize: int = 21) -> List[np.ndarray]:
    """Builds standard 8-orientation Gabor filter bank."""
    filters = []
    lambd = 1.0 / frequency
    for i in range(num_angles):
        theta = i * np.pi / num_angles
        kernel = cv2.getGaborKernel((ksize, ksize), 4.0, theta, lambd, 0.5, 0, ktype=cv2.CV_32F)
        kernel -= kernel.mean()
        filters.append(kernel)
    return filters


# Global cached filter bank
GABOR_BANK = build_gabor_bank(8)
SIFT_DETECTOR = cv2.SIFT_create()
BF_MATCHER = cv2.BFMatcher(cv2.NORM_L2)


def enhance_for_alignment(image: np.ndarray) -> np.ndarray:
    """Enhances image contrast with CLAHE for feature alignment."""
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    img_f = image.astype(np.float32)
    m, s = img_f.mean(), img_f.std() + 1e-6
    norm = np.clip(((img_f - m) / s) * 50 + 128, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return clahe.apply(norm)


def align_query_to_enrollment(
    img_enroll: np.ndarray,
    img_query: np.ndarray,
    min_inliers: int = 6
) -> Tuple[np.ndarray, int, Optional[np.ndarray]]:
    """
    Computes rigid affine transformation aligning query fingerprint to enrollment frame
    using robust SIFT feature descriptors and RANSAC.
    Returns:
        warped_query: Query image transformed into enrollment coordinate space
        inlier_count: Number of robust geometric inlier correspondences
        affine_matrix: 2x3 affine matrix (or None if unaligned)
    """
    if len(img_enroll.shape) == 3:
        img_enroll = cv2.cvtColor(img_enroll, cv2.COLOR_BGR2GRAY)
    if len(img_query.shape) == 3:
        img_query = cv2.cvtColor(img_query, cv2.COLOR_BGR2GRAY)

    en_A = enhance_for_alignment(img_enroll)
    en_B = enhance_for_alignment(img_query)

    kpA, desA = SIFT_DETECTOR.detectAndCompute(en_A, None)
    kpB, desB = SIFT_DETECTOR.detectAndCompute(en_B, None)

    if desA is None or desB is None or len(kpA) < 4 or len(kpB) < 4:
        return img_query, 0, None

    matches = BF_MATCHER.knnMatch(desB, desA, k=2)
    good = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good.append(m)

    if len(good) < 4:
        return img_query, len(good), None

    src_pts = np.float32([kpB[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kpA[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    M, mask = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    inliers = int(np.sum(mask)) if mask is not None else 0

    h, w = img_enroll.shape
    if M is not None and inliers >= min_inliers:
        warped = cv2.warpAffine(img_query, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        return warped, inliers, M

    return img_query, inliers, None


def extract_binary_template(
    image: np.ndarray,
    center: Optional[Tuple[int, int]] = None,
    shift: Tuple[int, int] = (0, 0),
    num_bands: int = 8,
    num_sectors: int = 16,
    r_in: int = 15,
    r_out: int = 120
) -> np.ndarray:
    """
    Extracts a canonical 1024-bit binary template from a fingerprint image:
    Tessellates region into 8 concentric bands x 16 sectors = 128 polar cells.
    Computes Average Absolute Deviation (AAD) across 8 Gabor filter directions = 1024 features.
    Binarizes relative to the median value -> 1024-bit vector B in {0, 1}^1024.
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    h, w = image.shape
    min_dim = min(h, w)
    if r_out > int(min_dim * 0.48):
        r_in = max(4, int(min_dim * 0.06))
        r_out = max(r_in + 12, int(min_dim * 0.46))

    if center is None:
        cx, cy = w // 2, h // 2
    else:
        cx, cy = center

    cx += shift[0]
    cy += shift[1]

    # Contrast normalization
    img_f = image.astype(np.float32)
    m, s = img_f.mean(), img_f.std() + 1e-6
    norm = np.clip(((img_f - m) / s) * 50 + 128, 0, 255).astype(np.uint8)

    # Convolve with Gabor filter bank
    filtered = [cv2.filter2D(norm, cv2.CV_32F, k) for k in GABOR_BANK]

    # Fast polar grid mapping
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    angle = (np.arctan2(y - cy, x - cx)) % (2.0 * np.pi)

    band_width = (r_out - r_in) / float(num_bands)
    sector_width = (2.0 * np.pi) / float(num_sectors)

    sec_idx = np.floor(angle / sector_width).astype(np.int32)
    band_idx = np.floor((dist - r_in) / band_width).astype(np.int32)

    valid = (dist >= r_in) & (dist < r_out) & (sec_idx >= 0) & (sec_idx < num_sectors) & (band_idx >= 0) & (band_idx < num_bands)

    N_regions = num_bands * num_sectors
    region_id = np.full((h, w), -1, dtype=np.int32)
    region_id[valid] = band_idx[valid] * num_sectors + sec_idx[valid]

    reg_flat = region_id.ravel()
    valid_flat = reg_flat >= 0
    reg_valid = reg_flat[valid_flat]
    counts = np.maximum(np.bincount(reg_valid, minlength=N_regions).astype(np.float32), 1.0)

    # Vectorized AAD extraction across 8 filters
    features = np.zeros((N_regions, len(filtered)), dtype=np.float32)
    for k in range(len(filtered)):
        f_flat = filtered[k].ravel()[valid_flat]
        sums = np.bincount(reg_valid, weights=f_flat, minlength=N_regions)
        means = sums / counts
        diff = np.abs(f_flat - means[reg_valid])
        features[:, k] = np.bincount(reg_valid, weights=diff, minlength=N_regions) / counts

    flat_feats = features.ravel()
    med = float(np.median(flat_feats))
    binary_template = (flat_feats > med).astype(np.uint8)
    return binary_template


def sector_rotations(
    template: np.ndarray,
    num_bands: int = 8,
    num_sectors: int = 16,
    num_filters: int = 8
) -> np.ndarray:
    """
    Returns every circular shift of the polar template, one row per sector step.
    A central rotation of the finger moves bits along the sector axis.
    Shape: (num_sectors, 1024). Row 0 is the unshifted template.
    """
    flat = np.asarray(template, dtype=np.uint8).reshape(-1)
    expected = num_bands * num_sectors * num_filters
    if flat.size != expected:
        raise ValueError(f"Template length {flat.size} does not match {expected}.")
    cube = flat.reshape(num_bands, num_sectors, num_filters)
    shifted = np.empty((num_sectors, expected), dtype=np.uint8)
    for step in range(num_sectors):
        shifted[step] = np.roll(cube, step, axis=1).ravel()
    return shifted


def compute_hamming_distance(template_A: np.ndarray, template_B: np.ndarray) -> float:
    """Computes normalized Hamming distance in [0, 1]."""
    return float(np.mean(template_A != template_B))


def compute_bit_flips(template_A: np.ndarray, template_B: np.ndarray) -> int:
    """Computes total number of differing bits."""
    return int(np.sum(template_A != template_B))


def render_binary_template_matrix(binary_template: np.ndarray, cell_size: int = 10) -> np.ndarray:
    """
    Renders 1024-bit binary template as a 32x32 visual grid image (uint8 grayscale).
    0 = black, 1 = white, scaled for display.
    """
    grid = binary_template.reshape(32, 32).astype(np.uint8) * 255
    rendered = cv2.resize(grid, (32 * cell_size, 32 * cell_size), interpolation=cv2.INTER_NEAREST)
    return rendered

