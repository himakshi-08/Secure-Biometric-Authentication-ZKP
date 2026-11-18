"""
Secure Fingerprint Authentication System
Module: core/minutiae.py
Author: Antigravity AI
Description:
    Implements minutiae extraction using Crossing Number (CN),
    post-processing pruning, orientation calculation, core point detection,
    and visual overlay generation.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any


class Minutia:
    """Represents an extracted fingerprint minutia point."""
    def __init__(self, x: int, y: int, m_type: str, angle: float = 0.0):
        self.x = int(x)
        self.y = int(y)
        self.type = m_type  # 'ending' or 'bifurcation'
        self.angle = float(angle)  # angle in radians

    def to_dict(self) -> Dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'type': self.type,
            'angle': round(float(self.angle), 4)
        }


def extract_crossing_numbers(skeleton: np.ndarray) -> np.ndarray:
    """
    Computes the 8-neighbor Crossing Number (CN) for every pixel in a binary skeleton.
    CN = 0.5 * sum(|p_i - p_{i+1}|) for i in 1..8, where p_9 = p_1.
    """
    skel_bin = (skeleton > 0).astype(np.uint8)
    
    # 8-neighbor shift matrices
    p2 = np.roll(skel_bin, -1, axis=0)
    p3 = np.roll(np.roll(skel_bin, -1, axis=0), 1, axis=1)
    p4 = np.roll(skel_bin, 1, axis=1)
    p5 = np.roll(np.roll(skel_bin, 1, axis=0), 1, axis=1)
    p6 = np.roll(skel_bin, 1, axis=0)
    p7 = np.roll(np.roll(skel_bin, 1, axis=0), -1, axis=1)
    p8 = np.roll(skel_bin, -1, axis=1)
    p9 = np.roll(np.roll(skel_bin, -1, axis=0), -1, axis=1)
    
    neighbors = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
    cn = np.zeros_like(skel_bin, dtype=np.float32)
    for i in range(8):
        cn += np.abs(neighbors[i].astype(np.float32) - neighbors[i + 1].astype(np.float32))
    cn *= 0.5
    
    # Mask out non-skeleton pixels
    cn[skel_bin == 0] = 0
    return cn


def prune_and_filter_minutiae(
    minutiae_list: List[Minutia],
    mask: np.ndarray,
    min_dist: float = 8.0,
    border_margin: int = 16
) -> List[Minutia]:
    """
    Removes false minutiae:
    1. Minutiae near the border of the image or ROI mask.
    2. Minutiae pairs that are closer than min_dist to each other.
    """
    h, w = mask.shape
    eroded_mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (border_margin * 2, border_margin * 2)))

    # Step 1: Filter border and outside mask
    valid = []
    for m in minutiae_list:
        if 0 <= m.y < h and 0 <= m.x < w:
            if eroded_mask[m.y, m.x] > 0:
                valid.append(m)

    # Step 2: Distance-based suppression (suppress crowded false minutiae)
    if not valid:
        return []

    pts = np.array([[m.x, m.y] for m in valid], dtype=np.float32)
    keep = np.ones(len(valid), dtype=bool)

    for i in range(len(valid)):
        if not keep[i]:
            continue
        # Check pairwise distances to remaining points
        dists = np.sqrt(np.sum((pts[i+1:] - pts[i]) ** 2, axis=1))
        close_indices = np.where(dists < min_dist)[0] + (i + 1)
        if len(close_indices) > 0:
            # If multiple minutiae are too close (broken ridge / bridge artifact), eliminate them
            keep[close_indices] = False
            keep[i] = False

    return [valid[idx] for idx in range(len(valid)) if keep[idx]]


def extract_minutiae(
    skeleton: np.ndarray,
    mask: np.ndarray,
    orientation: np.ndarray = None,
    min_dist: float = 8.0
) -> List[Minutia]:
    """
    Complete minutiae extraction pipeline:
    1. Crossing Number calculation.
    2. Identifies ridge endings (CN=1) and bifurcations (CN=3).
    3. Prunes spurious artifacts.
    4. Attaches local orientation angle.
    """
    cn = extract_crossing_numbers(skeleton)

    endings_y, endings_x = np.where(cn == 1.0)
    bifs_y, bifs_x = np.where(cn == 3.0)

    raw_minutiae: List[Minutia] = []
    h, w = skeleton.shape

    for y, x in zip(endings_y, endings_x):
        angle = orientation[y, x] if orientation is not None else 0.0
        raw_minutiae.append(Minutia(x, y, 'ending', angle))

    for y, x in zip(bifs_y, bifs_x):
        angle = orientation[y, x] if orientation is not None else 0.0
        raw_minutiae.append(Minutia(x, y, 'bifurcation', angle))

    filtered = prune_and_filter_minutiae(raw_minutiae, mask, min_dist=min_dist)
    return filtered


def detect_core_point(orientation: np.ndarray, mask: np.ndarray) -> Tuple[int, int]:
    """
    Detects the canonical core point (singularity) using orientation field curvature.
    Returns (core_x, core_y).
    """
    h, w = orientation.shape
    cos2 = np.cos(2.0 * orientation)
    sin2 = np.sin(2.0 * orientation)

    dcos2_y, dcos2_x = np.gradient(cos2)
    dsin2_y, dsin2_x = np.gradient(sin2)

    curvature = np.abs(dcos2_x * dsin2_y - dcos2_y * dsin2_x)
    curvature = cv2.GaussianBlur(curvature, (25, 25), 0)

    # Restrict search within central 60% of ROI mask
    eroded_mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30)))
    curvature_masked = curvature * (eroded_mask > 0).astype(np.float32)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(curvature_masked)
    if max_val > 0.001:
        return max_loc  # (x, y)
    
    # Fallback to center of mass
    M = cv2.moments(mask)
    if M['m00'] > 0:
        return int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])
    return w // 2, h // 2


def draw_minutiae_overlay(
    image: np.ndarray,
    minutiae: List[Minutia],
    core_point: Tuple[int, int] = None
) -> np.ndarray:
    """
    Renders an RGB overlay visualizing:
    - Ridge endings: Red circles with direction pointers
    - Ridge bifurcations: Blue squares
    - Core point: Green target crosshair
    """
    if len(image.shape) == 2:
        overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        overlay = image.copy()

    for m in minutiae:
        if m.type == 'ending':
            cv2.circle(overlay, (m.x, m.y), 3, (0, 0, 255), 1)  # Red circle
            # Draw orientation pointer
            dx = int(6 * np.cos(m.angle))
            dy = int(6 * np.sin(m.angle))
            cv2.line(overlay, (m.x, m.y), (m.x + dx, m.y + dy), (0, 0, 255), 1)
        elif m.type == 'bifurcation':
            cv2.rectangle(overlay, (m.x - 3, m.y - 3), (m.x + 3, m.y + 3), (255, 0, 0), 1)  # Blue square

    if core_point is not None:
        cx, cy = core_point
        cv2.circle(overlay, (cx, cy), 8, (0, 255, 0), 2)  # Green circle
        cv2.line(overlay, (cx - 12, cy), (cx + 12, cy), (0, 255, 0), 1)
        cv2.line(overlay, (cx, cy - 12), (cx, cy + 12), (0, 255, 0), 1)

    return overlay

