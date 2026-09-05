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
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score

IN_PATH = "data/processed/leads.csv"
OUT_PATH = "data/processed/leads_scored.csv"

NUMERIC = ["age", "campaign", "pdays", "previous", "emp_var_rate",
           "cons_price_idx", "cons_conf_idx", "euribor3m", "nr_employed"]
CATEGORICAL = ["job", "marital", "education", "default", "housing", "loan",
               "channel", "month", "day_of_week", "poutcome"]

ADVANCE_QUANTILE = 0.60  # advance top 40% of leads by score


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

    test_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"Held-out AUC: {test_auc:.3f}")

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
