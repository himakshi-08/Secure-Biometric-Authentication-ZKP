"""Core biometric processing and feature extraction package."""
from .preprocessing import (
    normalize_image, segment_roi, estimate_orientation_field,
    build_gabor_filter_bank, filter_with_gabor_bank, binarize_image,
    thin_skeleton, preprocess_pipeline
)
from .minutiae import (
    Minutia, extract_crossing_numbers, extract_minutiae,
    detect_core_point, draw_minutiae_overlay
)
from .template import (
    extract_binary_template, align_query_to_enrollment,
    compute_hamming_distance, compute_bit_flips,
    render_binary_template_matrix
)

__all__ = [
    'normalize_image', 'segment_roi', 'estimate_orientation_field',
    'build_gabor_filter_bank', 'filter_with_gabor_bank', 'binarize_image',
    'thin_skeleton', 'preprocess_pipeline',
    'Minutia', 'extract_crossing_numbers', 'extract_minutiae',
    'detect_core_point', 'draw_minutiae_overlay',
    'extract_binary_template', 'align_query_to_enrollment',
    'compute_hamming_distance', 'compute_bit_flips',
    'render_binary_template_matrix'
]

