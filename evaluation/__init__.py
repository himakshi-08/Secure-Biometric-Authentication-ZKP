"""Evaluation and benchmarking package."""
from .metrics import compute_roc_and_eer, generate_metrics_plots
from .evaluate_dataset import evaluate_split, run_full_benchmark

__all__ = [
    'compute_roc_and_eer', 'generate_metrics_plots',
    'evaluate_split', 'run_full_benchmark'
]

