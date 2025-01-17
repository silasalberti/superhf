"""
Plot test reward along with METEOR score similarity.
"""

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from chart_utils import (
    get_test_scores,
    initialize_plot,
    model_type_to_palette_color,
    save_plot,
    # LLAMA_TEST_REWARD,
)
from superhf.utils import bootstrap_meteor_similarity_from_completions

INSTRUCT_NOT_LLAMA = True  # Swap between generating 2 types of charts
OUTPUT_FILE = (
    "./charts/ablations/kl_meteor_similarity_instruct.png"
    if INSTRUCT_NOT_LLAMA
    else "./charts/ablations/kl_meteor_similarity_llama.png"
)
TEST_COMPLETIONS_DIRECTORY = "./experiments/evaluations/test_completions/"
TEST_SCORES_DIRECTORY = "./experiments/evaluations/test_scores/"
NUM_BOOTSTRAP_SAMPLES = 16
model_types_to_file_name_templates = {
    "SuperHF": (
        [
            "shf-v4-llama-instruct-10k-kl-",
            "shf-v4-instruct-s1-10k-kl",
            "shf-v4-instruct-s2-10k-kl",
            "shf-v4-instruct-s3-10k-kl",
            "shf-v4-instruct-s4-10k-kl",
        ]
        if INSTRUCT_NOT_LLAMA
        else [
            "shf-v4-llama-10000-kl-",
            "shf-v4-llama-s1-10k-kl",
            "shf-v4-llama-s2-10k-kl",
            "shf-v4-llama-s3-10k-kl",
            "shf-v4-llama-s4-10k-kl",
        ]
    )
}
kl_values = [
    0.0,
    0.025,
    0.05,
    0.1,
    0.15,
    0.2,
    0.225,
    0.25,
    0.275,
    0.3,
    0.35,
    0.375,
    0.4,
    0.45,
    0.5,
]


def get_rewards_and_similarity(file_name: str) -> tuple[list[float], list[float]]:
    """Get the test scores and METEOR similarity scores for a given model."""
    score_file_path = os.path.join(TEST_SCORES_DIRECTORY, file_name)
    completion_file_path = os.path.join(TEST_COMPLETIONS_DIRECTORY, file_name)
    rewards = get_test_scores(score_file_path)
    meteor_scores = bootstrap_meteor_similarity_from_completions(
        completion_file_path, NUM_BOOTSTRAP_SAMPLES
    )
    return rewards, meteor_scores


def main() -> None:
    """Main function."""

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements

    # Initialize
    initialize_plot()
    color_reward = model_type_to_palette_color("SuperHF")
    color_similarity = model_type_to_palette_color("ftp")

    # Define the model sizes and their corresponding file names

    # Compute LLaMA's, Instruct's, and Alpaca's mean reward and similarity
    llama_rewards, llama_meteor_scores = get_rewards_and_similarity("llama-7b.json")
    llama_mean_reward = np.mean(llama_rewards)
    llama_mean_meteor_score = np.mean(llama_meteor_scores)
    print(f"LLaMA Mean Test Reward: {llama_mean_reward:.3f}")
    print(f"LLaMA Mean Meteor Score: {llama_mean_meteor_score:.3f}")

    instruct_mean_reward = None
    instruct_mean_meteor_score = None
    if INSTRUCT_NOT_LLAMA:
        instruct_rewards, instruct_meteor_scores = get_rewards_and_similarity(
            "llama-instruct-12379.json"
        )
        instruct_mean_reward = np.mean(instruct_rewards)
        instruct_mean_meteor_score = np.mean(instruct_meteor_scores)
        print(f"Instruct Mean Test Reward: {instruct_mean_reward:.3f}")
        print(f"Instruct Mean Meteor Score: {instruct_mean_meteor_score:.3f}")

    alpaca_rewards, alpaca_meteor_scores = get_rewards_and_similarity("alpaca_7b.json")
    alpaca_mean_reward = np.mean(alpaca_rewards)
    alpaca_mean_meteor_score = np.mean(alpaca_meteor_scores)
    print(f"Alpaca Mean Test Reward: {alpaca_mean_reward:.3f}")
    print(f"Alpaca Mean Meteor Score: {alpaca_mean_meteor_score:.3f}")

    # Find all the files in the test scores directory
    file_names = []
    last_model_type = None
    for model_type, file_name_templates in model_types_to_file_name_templates.items():
        for template in file_name_templates:
            intermediate_file_names = []
            for file_name in os.listdir(TEST_SCORES_DIRECTORY):
                if file_name.startswith(template):
                    intermediate_file_names.append(file_name)
                    last_model_type = model_type
            print(
                f"Found {len(intermediate_file_names)} files with the template"
                f" {template}"
            )
            file_names.extend(intermediate_file_names)
    file_names.sort()
    reward_data = []
    meteor_data = []
    for file_name in tqdm(file_names, desc="Models"):
        kl_coefficient = float(file_name.split("-")[-1].split(".json")[0])
        if kl_coefficient not in kl_values:
            print(f"Skipping {file_name} with KL coefficient {kl_coefficient}")
            continue
        rewards, meteor_scores = get_rewards_and_similarity(file_name)
        labeled_rewards = [
            [last_model_type, kl_coefficient, score] for score in rewards
        ]
        labeled_meteor_scores = [
            [last_model_type, kl_coefficient, score] for score in meteor_scores
        ]
        reward_data.extend(labeled_rewards)
        meteor_data.extend(labeled_meteor_scores)

    dataframe_scores = pd.DataFrame(
        reward_data, columns=["Model", "KL-Coefficient", "Test Reward →"]
    )

    # Create the plot
    ax1 = sns.lineplot(
        data=dataframe_scores,
        x="KL-Coefficient",
        y="Test Reward →",
        errorbar="ci",
        # capsize=0.1,
        # marker="",
        # label="Pythia Base",
        # palette=[
        #     model_type_to_palette_color(m) for m in dataframe_scores["Model"].unique()
        # ],
        color=color_reward,
    )

    # Twin
    ax2 = plt.twinx()
    dataframe_meteor = pd.DataFrame(
        meteor_data, columns=["Model", "KL-Coefficient", "METEOR Similarity ←"]
    )
    sns.lineplot(
        data=dataframe_meteor,
        x="KL-Coefficient",
        y="METEOR Similarity ←",
        errorbar="ci",
        # capsize=0.1,
        # marker="",
        # label="Pythia Base",
        # palette=[
        #     model_type_to_palette_color(m) for m in dataframe_meteor["Model"].unique()
        # ],
        color=model_type_to_palette_color("ftp"),
        ax=ax2,
    )

    # Color each y axis with the color of the corresponding line
    # ax1.spines["left"].set_color(color_reward)
    ax1.tick_params(axis="y", colors=color_reward)
    ax1.set_ylabel("Test Reward →", color=color_reward)
    # ax2.spines["right"].set_color(color_similarity)
    ax2.tick_params(axis="y", colors=color_similarity)
    ax2.set_ylabel("METEOR Similarity ←", color=color_similarity)

    # Turn off the grid for the second y axis
    ax2.grid(False)

    if not INSTRUCT_NOT_LLAMA:
        # Room in legend, add labels for main lines
        ax1.plot(
            [],
            [],
            color=color_reward,
            linestyle="-",
            label="SuperHF (LLaMA) Test Reward",
        )
        ax1.plot(
            [],
            [],
            color=color_similarity,
            linestyle="-",
            label="SuperHF (LLaMA) Test Similarity",
        )

    # Plot dashed horizontal lines for llama and alpaca
    plt.rcParams["lines.marker"] = ""
    ax1.axhline(
        llama_mean_reward, color=color_reward, linestyle="--", label="LLaMA Mean Reward"
    )
    ax2.axhline(
        llama_mean_meteor_score,
        color=color_similarity,
        linestyle="--",
        label="LLaMA Mean Similarity",
    )
    if INSTRUCT_NOT_LLAMA:
        ax1.axhline(
            instruct_mean_reward,
            color=color_reward,
            linestyle="-.",
            label="Instruct Mean Reward",
        )
        ax2.axhline(
            instruct_mean_meteor_score,
            color=color_similarity,
            linestyle="-.",
            label="Instruct Mean Similarity",
        )
    ax1.axhline(
        alpaca_mean_reward,
        color=color_reward,
        linestyle=":",
        label="Alpaca Mean Reward",
    )
    # ax2.axhline(
    #     alpaca_mean_meteor_score,
    #     color=color_similarity,
    #     linestyle=":",
    #     label="Alpaca Mean Similarity",
    # )  # About the same as llama

    # Add empty lines to ax1 so they show up on the legend
    label = (
        "LLaMA/Alpaca Similarity"
        if INSTRUCT_NOT_LLAMA
        else "LLaMA/Alpaca Mean Similarity"
    )
    ax1.plot(
        [],
        [],
        color=color_similarity,
        linestyle="--",
        label=label,
    )
    if INSTRUCT_NOT_LLAMA:
        ax1.plot(
            [],
            [],
            color=color_similarity,
            linestyle="-.",
            label="Instruct Mean Similarity",
        )

    # Set labels and title
    plt.xlabel("KL Coefficient")
    # plt.ylabel("Test Score →")
    title = (
        "SuperHF (Instruct) KL-Coefficient on Reward and Completion Similarity"
        if INSTRUCT_NOT_LLAMA
        else "SuperHF (LLaMA) KL-Coefficient on Reward and Completion Similarity"
    )
    plt.title(title)

    # Set legend
    ax1.legend()

    # Nudge the similarity axis bounds so the llama reward and similarity lines don't overlap
    ax1.set_ylim(-0.56, 2.4)
    ax2.set_ylim(-0.02, 0.85)

    # Save the plot
    save_plot(OUTPUT_FILE)

    # Zoom in
    # plt.xlim(0.2, 0.4)
    # ax1.set_ylim(-0.5, 0.4)
    # ax2.set_ylim(0.0, 0.23)
    # save_plot(OUTPUT_FILE.replace(".png", "-zoom.png"))


if __name__ == "__main__":
    main()
