"""
Functions for reporting metrics in SuperHF training.
"""

from dataclasses import dataclass
import time

# from typing import Any

import numpy as np
import wandb
from superhf.utils import calculate_meteor_similarity_only_completions

# from superhf.filtering import CompletionFilterTopK


@dataclass
class SuperHFMetrics:
    """
    Metrics for SuperHF training.
    """

    # pylint: disable=too-many-instance-attributes

    superbatches_complete: int
    superbatch_count: int
    completions: list[str]
    filtered_completions: list[str]
    scores_train: list[float]
    scores_val: list[float]
    filtered_scores: list[float]
    average_loss: float
    average_kl_div: float
    scheduler_lr: float
    completion_lengths: list[int]
    filtered_completion_lengths: list[int]


### Printing ###


def report_metrics_print(metrics: SuperHFMetrics) -> None:
    """
    Print basic metrics to STD out.
    """
    percent_complete = (
        (metrics.superbatches_complete + 1) / metrics.superbatch_count * 100
    )
    average_completion_length = np.mean([len(c) for c in metrics.completions])
    average_filtered_completion_length = np.mean(
        [len(c) for c in metrics.filtered_completions]
    )
    score_train_avg = np.mean(metrics.scores_train)
    score_train_std = np.std(metrics.scores_train)
    score_val_avg = np.mean(metrics.scores_val) if metrics.scores_val else np.nan
    score_val_std = np.std(metrics.scores_val) if metrics.scores_val else np.nan
    score_filtered_avg = np.mean(metrics.filtered_scores)
    similarity = calculate_meteor_similarity_only_completions(
        metrics.filtered_completions
    )
    similarity = similarity if similarity is not None else np.nan
    print(
        "\n📊 Metrics at time"
        f" {time.strftime('%H:%M:%S', time.localtime())}\nSuperbatch"
        f" {metrics.superbatches_complete}/{metrics.superbatch_count} ({percent_complete:.3f}%):"
        f" {len(metrics.completions)} completions,"
        f" {len(metrics.filtered_completions)} filtered completions, completion length"
        f" {average_completion_length:.3f}, filtered completion length"
        f" {average_filtered_completion_length:.3f}\ntrain score"
        f" {score_train_avg:.3f} ±{score_train_std:.3f}, val score"
        f" {score_val_avg:.3f} ±{score_val_std:.3f}, filtered score"
        f" {score_filtered_avg:.3f}\nloss {metrics.average_loss:.3f},  KL"
        f" {metrics.average_kl_div:.3f}, similarity: {similarity:.3f}."
    )


### Weights and Biases ###


def initialize_metrics_wandb() -> None:
    """
    Defines metrics for a Weights and Biases run.
    """
    wandb.define_metric("average_loss", summary="min")
    wandb.define_metric("score_train_avg", summary="last")
    wandb.define_metric("score_train_avg", summary="mean")
    wandb.define_metric("score_val_avg", summary="last")
    wandb.define_metric("score_val_avg", summary="mean")
    wandb.define_metric("average_kl_div", summary="mean")
    wandb.define_metric("average_completion_length", summary="last")


def report_metrics_wandb(metrics: SuperHFMetrics) -> None:
    """
    Report metrics to Weights and Biases.

    Logs the following metrics:
    - Superbatch index and percentage complete
    - Score average and histogram
    - Filtered score average and histogram
    - Scheduler learning rate
    - Average loss
    - Scheduler learning rate
    - Completions length average and histogram
    - Filtered completions length average and histogram
    - Completions table
    - Filtered completions table
    - Histogram of filtered score if we filtered different top-K numbers
    """
    percent_complete = (
        (metrics.superbatches_complete + 1) / metrics.superbatch_count * 100
    )
    score_train_avg = np.mean(metrics.scores_train)
    score_train_std = np.std(metrics.scores_train)
    score_train_hist = (
        wandb.Histogram(metrics.scores_train) if metrics.scores_train else None
    )
    score_val_avg = np.mean(metrics.scores_val) if metrics.scores_val else None
    score_val_std = np.std(metrics.scores_val) if metrics.scores_val else None
    score_val_hist = wandb.Histogram(metrics.scores_val) if metrics.scores_val else None
    score_filtered_avg = np.mean(metrics.filtered_scores)
    prompt_index = metrics.superbatches_complete * len(metrics.filtered_completions)
    similarity = calculate_meteor_similarity_only_completions(
        metrics.filtered_completions
    )

    # # Create plot data of average score if we filtered different top-K numbers
    # max_top_k_to_explore = 48
    # scores_per_top_k: list[list[Any]] = []
    # for top_k in range(1, max_top_k_to_explore + 1):
    #     top_k_filter = CompletionFilterTopK(top_k)
    #     scores, _ = top_k_filter.filter(
    #         metrics.scores,
    #         metrics.completions,
    #     )
    #     mean, variance = np.mean(scores), np.var(scores)
    #     scores_per_top_k.append([top_k, mean, variance])

    wandb.log(
        {
            "superbatch_index": metrics.superbatches_complete,
            "percent_complete": percent_complete,
            "score_train_avg": score_train_avg,
            "score_train_std": score_train_std,
            "score_train_histogram": score_train_hist,
            "score_val_avg": score_val_avg,
            "score_val_std": score_val_std,
            "score_val_histogram": score_val_hist,
            "average_filtered_score": score_filtered_avg,
            # "filtered_score_histogram": wandb.Histogram(metrics.filtered_scores),
            "average_loss": metrics.average_loss,
            "average_kl_div": metrics.average_kl_div,
            "similarity": similarity,
            "scheduler_lr": metrics.scheduler_lr,
            "average_completion_length": np.mean(metrics.completion_lengths),
            # "completion_length_histogram": wandb.Histogram(metrics.completion_lengths),
            # "average_filtered_completion_length": np.mean(
            #     metrics.filtered_completion_lengths
            # ),
            # "filtered_completion_length_histogram": wandb.Histogram(
            #     metrics.filtered_completion_lengths
            # ),
            # "completions": wandb.Table(
            #     columns=["superbatch", "completion", "score"],
            #     data=[
            #         [metrics.superbatch_index, completion, score]
            #         for completion, score in zip(metrics.completions, metrics.scores)
            #     ],
            # ),
            # "filtered_completions": wandb.Table(
            #     columns=["superbatch", "completion", "score"],
            #     data=[
            #         [metrics.superbatches_complete, completion, score]
            #         for completion, score in zip(
            #             metrics.filtered_completions, metrics.filtered_scores
            #         )
            #     ],
            # ),
            # "scores_per_top_k": wandb.plot.line(  # type: ignore
            #     wandb.Table(
            #         columns=["Top-K", "Score", "Variance"], data=scores_per_top_k
            #     ),
            #     "Top-K",
            #     "Score",
            #     stroke="Variance",
            #     title="Scores Per Top-K (Latest)",
            # ),
        },
        step=prompt_index,
    )


### Delay ###


def delay_metrics(_: SuperHFMetrics) -> None:
    """
    Delay to allow time for logging to reach a server.
    """
    time.sleep(3)
