"""Write a latex table of win rates."""

import csv
from typing import Any

from chart_utils import create_file_dir_if_not_exists, MODEL_NAME_MAPPING

INPUT_FILE = "./eval_results/gpt4_qualitative/new_models/win_rates.csv"
OUTPUT_PATH = "./charts/qualitative/win_rates_table.tex"


def main() -> None:
    """Main function."""

    # Read the CSV file
    win_rates = {}
    with open(INPUT_FILE, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header
        for row in reader:
            model_a, model_b, win_rate = row
            win_rates[(MODEL_NAME_MAPPING[model_a], MODEL_NAME_MAPPING[model_b])] = (
                win_rate
            )

    # Create an NxN matrix
    model_names = list(MODEL_NAME_MAPPING.values())
    num_models = len(model_names)
    matrix: list[list[Any]] = [
        [0 for _ in range(num_models)] for _ in range(num_models)
    ]
    for i, model_a in enumerate(model_names):
        for j, model_b in enumerate(model_names):
            if model_a == model_b:
                matrix[i][j] = "-"
            else:
                win_rate = win_rates.get(
                    (model_a, model_b), win_rates.get((model_b, model_a), "0")
                )
                matrix[i][j] = rf"{round(float(win_rate) * 100, 2)}\%"
                print(f"'{model_a}' vs '{model_b}': {win_rate},")

    # Add new lines
    new_model_names = []
    for model_name in list(MODEL_NAME_MAPPING.values()):
        if " " in model_name:
            model_name = "\\makecell{" + model_name.replace(" ", "\\\\") + "}"
        else:
            model_name = "\\makecell{" + model_name + "\\\\\\phantom{space}}"
        new_model_names.append(model_name)
    model_names = new_model_names

    # Write the matrix into a LaTeX file
    create_file_dir_if_not_exists(OUTPUT_PATH)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as latexfile:
        # Make sure this is the right number of columns
        latexfile.write("\\begin{tabular}{|c|c|c|c|c|c|c|c|c|}\n")
        latexfile.write("\\hline\n")
        latexfile.write(" & " + " & ".join(model_names) + " \\\\\n")
        latexfile.write("\\hline\n")
        for i, row in enumerate(matrix):
            # latexfile.write(
            #     model_names[i] + " & " + " & ".join(str(x) for x in row) + " \\\\\n"
            # )
            # Bold the >50% win rates
            latexfile.write(
                model_names[i]
                + " & "
                + " & ".join(
                    rf"\textbf{{{x}}}" if x != "-" and float(x[:-2]) > 50 else x
                    for x in row
                )
                + " \\\\\n"
            )
            latexfile.write("\\hline\n")
        latexfile.write("\\end{tabular}\n")


if __name__ == "__main__":
    main()
