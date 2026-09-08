"""
04_score_lift.py

Answers a different question than the funnel diagram does: not "what
happened by vendor" but "does the lead-scoring model actually separate
good leads from bad ones." Splits leads into 10 score deciles (highest
score first) and plots the real, historical conversion rate within each
decile. If the model carries real signal, the top decile should convert
at a visibly higher rate than the bottom one.

Kept as a standalone chart rather than a stage of the funnel Sankey: this
is a retrospective validation question about the model, not a live
operational step leads pass through, and folding the two together implied
an order of operations ("advanced" leads converting because they were
advanced) that isn't true of historical data. See 03_sankey.py.

Output: output/score_lift_chart.png
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IN_PATH = "data/processed/leads_scored.csv"
OUT_PATH = "output/score_lift_chart.png"


def main():
    df = pd.read_csv(IN_PATH)

    # Decile 1 = highest-scored 10% of leads, decile 10 = lowest-scored.
    df["decile"] = pd.qcut(df["lead_score"], 10, labels=False, duplicates="drop")
    df["decile"] = df["decile"].max() - df["decile"] + 1  # flip so 1 = highest score

    by_decile = df.groupby("decile")["converted"].mean().sort_index()
    overall_rate = df["converted"].mean()

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(by_decile.index.astype(str), by_decile.values, color="#1f77b4")
    ax.axhline(overall_rate, color="gray", linestyle="--",
               label=f"Overall conversion rate ({overall_rate:.1%})")
    ax.set_xlabel("Score decile (1 = highest-scored leads)")
    ax.set_ylabel("Actual conversion rate")
    ax.set_title("Does the score separate good leads from bad ones?")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150)
    plt.close()

    print(f"Wrote {OUT_PATH}")
    print("Conversion rate by decile (1 = highest-scored):")
    print(by_decile)


if __name__ == "__main__":
    main()
