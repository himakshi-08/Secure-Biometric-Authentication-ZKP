"""Unit tests for core/minutiae.py"""
import os
import cv2
import numpy as np
import pytest

from core.preprocessing import preprocess_pipeline
from core.minutiae import (
    extract_crossing_numbers, extract_minutiae,
    detect_core_point, draw_minutiae_overlay, Minutia
)

SAMPLE_PATH = 'data/fvc2002_db1_b/101_1.tif'


def test_crossing_number_and_minutiae():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    prep = preprocess_pipeline(img)
    skel = prep['skeleton']
    mask = prep['mask']
    theta = prep['orientation']

    cn = extract_crossing_numbers(skel)
    assert cn.shape == skel.shape

    minutiae = extract_minutiae(skel, mask, theta)
    assert len(minutiae) > 10
    types = {m.type for m in minutiae}
    assert 'ending' in types
    assert 'bifurcation' in types


def test_core_point_detection():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    prep = preprocess_pipeline(img)
    core = detect_core_point(prep['orientation'], prep['mask'])
    assert isinstance(core, tuple)
    assert len(core) == 2
    assert 0 <= core[0] < img.shape[1]
    assert 0 <= core[1] < img.shape[0]


def test_overlay_rendering():
    img = cv2.imread(SAMPLE_PATH, cv2.IMREAD_GRAYSCALE)
    prep = preprocess_pipeline(img)
    minutiae = extract_minutiae(prep['skeleton'], prep['mask'], prep['orientation'])
    core = detect_core_point(prep['orientation'], prep['mask'])

    overlay = draw_minutiae_overlay(img, minutiae, core)
    assert overlay.shape == (img.shape[0], img.shape[1], 3)
    assert overlay.dtype == np.uint8

