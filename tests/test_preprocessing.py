"""Unit tests for core/preprocessing.py"""
import os
import cv2
import numpy as np
import pytest

from core.preprocessing import (
    normalize_image, segment_roi, estimate_orientation_field,
    build_gabor_filter_bank, filter_with_gabor_bank, binarize_image,
    thin_skeleton, preprocess_pipeline
)

SAMPLE_PATH = 'data/fvc2002_db1_b/101_1.tif'


def test_normalization():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    assert img is not None, "Sample image not found"
    norm = normalize_image(img, target_mean=128.0, target_var=2500.0)
    assert norm.shape == img.shape
    assert norm.dtype == np.uint8
    assert 120 < norm.mean() < 136


def test_segment_roi():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    mask, center = segment_roi(img)
    assert mask.shape == img.shape
    assert mask.dtype == np.uint8
    assert 0 <= center[0] < img.shape[1]
    assert 0 <= center[1] < img.shape[0]


def test_orientation_field():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    theta = estimate_orientation_field(img)
    assert theta.shape == img.shape
    assert -np.pi/2 <= theta.min() <= np.pi/2
    assert -np.pi/2 <= theta.max() <= np.pi/2


def test_gabor_filter_bank():
    filters = build_gabor_filter_bank(num_orientations=8)
    assert len(filters) == 8
    for k in filters:
        assert abs(k.mean()) < 1e-4  # Zero DC


def test_binarization_and_thinning():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    bin_img = binarize_image(img)
    assert set(np.unique(bin_img)).issubset({0, 255})
    
    skel = thin_skeleton(bin_img)
    assert skel.shape == img.shape
    assert cv2.countNonZero(skel) > 0
    # Skeleton should have significantly fewer foreground pixels than raw binary image
    assert cv2.countNonZero(skel) < cv2.countNonZero(bin_img)


def test_full_preprocessing_pipeline():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    res = preprocess_pipeline(img)
    assert 'normalized' in res
    assert 'mask' in res
    assert 'orientation' in res
    assert 'binarized' in res
    assert 'skeleton' in res
    assert 'gabor_filtered' in res
    assert len(res['gabor_filtered']) == 8

