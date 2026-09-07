"""
02_lead_scoring_model.py

Trains a lead-scoring model: given attributes known at intake (before
conversion outcome is known), predict probability of conversion. This is
the "evaluation" stage of the funnel — leads above the score threshold are
"advanced," others are deprioritized. Threshold is chosen to hold advance
rate near a realistic ops capacity (top ~40% of leads by score).

Outputs data/processed/leads_scored.csv with lead_score and advanced flag,
plus prints model quality (AUC) so the read is honest about how much
signal the model actually carries.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, roc_curve

IN_PATH = "data/processed/leads.csv"
OUT_PATH = "data/processed/leads_scored.csv"
ROC_PATH = "output/roc_curve.png"

# Feature lists reflect the plausibility audit in 01_build_leads.py: only
# columns a lead vendor could plausibly supply about a cold contact, plus
# market-condition indicators. `duration` is deliberately excluded even
# though it's in leads.csv -- it's the length of the outcome call itself,
# only known after the call, so using it as an intake-time feature would
# leak the outcome.
NUMERIC = ["age", "emp_var_rate", "cons_price_idx", "cons_conf_idx",
           "euribor3m", "nr_employed"]
CATEGORICAL = ["job", "education", "channel", "month", "day_of_week"]

# Advance top 40% of leads by score. This is an operational assumption,
# not derived from the data: it stands in for a sales team's realistic
# working capacity (advance more leads than the team can act on and the
# score becomes noise; advance fewer and profitable leads get dropped).
# In a live version this would be tuned against actual team capacity and
# re-checked as that capacity changes, not fixed at build time.
ADVANCE_QUANTILE = 0.60


def main():
    df = pd.read_csv(IN_PATH)

    X = df[NUMERIC + CATEGORICAL]
    y = df["converted"]

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=0.25, random_state=42, stratify=y
    )

    pre = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    model = Pipeline([
        ("pre", pre),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    model.fit(X_train, y_train)

    test_scores = model.predict_proba(X_test)[:, 1]
    test_auc = roc_auc_score(y_test, test_scores)
    print(f"Held-out AUC: {test_auc:.3f}")

    fpr, tpr, _ = roc_curve(y_test, test_scores)
    plt.figure(figsize=(5, 5))
    plt.plot(fpr, tpr, label=f"AUC = {test_auc:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("Lead-scoring model: held-out ROC curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ROC_PATH, dpi=150)
    plt.close()
    print(f"Wrote {ROC_PATH}")

    df["lead_score"] = model.predict_proba(X)[:, 1]
    threshold = df["lead_score"].quantile(ADVANCE_QUANTILE)
    df["advanced"] = (df["lead_score"] >= threshold).astype(int)

    print(f"Advance threshold (score): {threshold:.3f}")
    print(f"Advanced leads: {df['advanced'].sum():,} of {len(df):,}")
    print("Conversion rate, advanced vs not:")
    print(df.groupby("advanced")["converted"].mean())

    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
