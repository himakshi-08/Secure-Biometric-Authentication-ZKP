"""
Secure Fingerprint Authentication System
Module: core/preprocessing.py
Author: Antigravity AI
Description:
    Implements standard biometric preprocessing according to Hong, Wan, and Jain (1998):
    1. Contrast Normalization
    2. ROI Foreground Segmentation
    3. Ridge Orientation Field Estimation
    4. Gabor Filter Bank Construction and Ridge Enhancement
    5. Adaptive Binarization
    6. Morphological Thinning / Skeletonization
"""

import cv2
import numpy as np
from typing import Tuple, List, Dict, Any


def normalize_image(image: np.ndarray, target_mean: float = 128.0, target_var: float = 2500.0) -> np.ndarray:
    """
    Standardizes the dynamic range and contrast of the input fingerprint image.
    I'(x, y) = M0 + sqrt((V0 * (I(x, y) - M)^2) / V) if I(x, y) > M else M0 - ...
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    img_f = image.astype(np.float32)
    m = float(np.mean(img_f))
    v = float(np.var(img_f)) + 1e-6
    std = np.sqrt(v)
    target_std = np.sqrt(target_var)

    normalized = np.where(
        img_f > m,
        target_mean + np.sqrt(target_var * ((img_f - m) ** 2) / v),
        target_mean - np.sqrt(target_var * ((img_f - m) ** 2) / v)
    )
    return np.clip(normalized, 0, 255).astype(np.uint8)


def segment_roi(image: np.ndarray, block_size: int = 16, threshold_ratio: float = 0.1) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Segments the fingerprint ridge foreground from background using local variance
    and morphological operations. Returns binary mask (0 or 255) and center of mass (cx, cy).
    """
    h, w = image.shape
    blurred = cv2.GaussianBlur(image, (7, 7), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

    M = cv2.moments(mask)
    if M['m00'] > 0:
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
    else:
        cx, cy = w // 2, h // 2

    return mask, (cx, cy)


def estimate_orientation_field(image: np.ndarray, block_size: int = 16) -> np.ndarray:
    """
    Estimates the dominant ridge orientation field using Rao's gradient method
    with continuous vector field Gaussian smoothing.
    """
    gx = cv2.Sobel(image.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(image.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)

    vx = 2.0 * gx * gy
    vy = (gx ** 2) - (gy ** 2)

    ksize = block_size * 2 + 1
    vx = cv2.GaussianBlur(vx, (ksize, ksize), 0)
    vy = cv2.GaussianBlur(vy, (ksize, ksize), 0)

    theta = 0.5 * np.arctan2(vx, vy)
    return theta


def build_gabor_filter_bank(
    num_orientations: int = 8,
    frequency: float = 0.10,
    ksize: int = 21,
    sigma: float = 4.0,
    gamma: float = 0.5
) -> List[np.ndarray]:
    """
    Constructs a bank of 2D Gabor filters across evenly spaced orientations in [0, pi).
    Each filter has zero DC bias to prevent uniform lighting shifts.
    """
    filters = []
    lambd = 1.0 / frequency
    for i in range(num_orientations):
        theta = i * np.pi / num_orientations
        kernel = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, gamma, 0, ktype=cv2.CV_32F)
        kernel -= kernel.mean()  # Zero DC component
        filters.append(kernel)
    return filters


def filter_with_gabor_bank(image: np.ndarray, filters: List[np.ndarray]) -> List[np.ndarray]:
    """
    Convolves the normalized image with all filters in the Gabor filter bank.
    """
    img_f = image.astype(np.float32)
    return [cv2.filter2D(img_f, cv2.CV_32F, k) for k in filters]


def binarize_image(image: np.ndarray) -> np.ndarray:
    """
    Binarizes fingerprint image using Gaussian adaptive thresholding.
    Output: 255 for ridges, 0 for valleys.
    """
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    bin_img = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 3
    )
    # Morphological closing to seal minute breaks along ridges
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kernel)
    return bin_img


def thin_skeleton(binary_image: np.ndarray) -> np.ndarray:
    """
    Morphological skeletonization producing a 1-pixel wide connected skeleton.
    Input: Binary image (0 or 255).
    Output: Skeleton image (0 or 255).
    """
    img = binary_image.copy()
    skel = np.zeros(img.shape, dtype=np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    
    size = np.size(img)
    done = False
    while not done:
        eroded = cv2.erode(img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img, temp)
        skel = cv2.bitwise_or(skel, temp)
        img = eroded.copy()
        
        zeros = size - cv2.countNonZero(img)
        if zeros == size:
            done = True
            
    return skel


def preprocess_pipeline(image: np.ndarray) -> Dict[str, Any]:
    """
    Executes the complete preprocessing pipeline on a raw fingerprint image.
    Returns:
        Dict containing:
            'normalized': contrast-normalized image
            'mask': foreground ROI mask
            'center': ROI center coordinates (cx, cy)
            'orientation': orientation field theta
            'binarized': binarized ridge image
            'skeleton': 1-pixel thinned skeleton
            'gabor_filtered': list of Gabor filter responses
    """
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    normalized = normalize_image(image)
    mask, center = segment_roi(normalized)
    orientation = estimate_orientation_field(normalized)
    binarized = binarize_image(normalized)
    skeleton = thin_skeleton(binarized)
    
    filters = build_gabor_filter_bank(num_orientations=8)
    gabor_filtered = filter_with_gabor_bank(normalized, filters)

    return {
        'normalized': normalized,
        'mask': mask,
        'center': center,
        'orientation': orientation,
        'binarized': binarized,
        'skeleton': skeleton,
        'gabor_filtered': gabor_filtered,
        'filters': filters
    }

