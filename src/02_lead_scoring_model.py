"""
02_lead_scoring_model.py

Trains a lead-scoring model: given attributes known at intake (before
conversion outcome is known), predict probability of conversion. Leads
above a score threshold are flagged "advanced," a label for how the
model would prioritize leads today, not a stage the historical leads in
this file ever actually passed through (they already converted or didn't
before this model existed). See 03_sankey.py for why that distinction
matters for how this gets visualized.

Outputs data/processed/leads_scored.csv with lead_score and advanced
flag, plus:
- Held-out AUC with a bootstrap confidence interval, so a single point
  estimate isn't presented as more precise than it is.
- A sensitivity check on ADVANCE_QUANTILE (output/advance_threshold_
  sensitivity.txt): rather than asserting 40% is fine, this reruns the
  same advance-rate math at several thresholds so it's visible whether
  the headline numbers actually depend on that specific cutoff.
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
SENSITIVITY_PATH = "output/advance_threshold_sensitivity.txt"

N_BOOTSTRAP = 1000
RANDOM_SEED = 42

# Candidate advance rates to check ADVANCE_QUANTILE's sensitivity against.
# 0.60 (the value actually used) is included so it shows up in the same
# table as the alternatives, not singled out.
SENSITIVITY_QUANTILES = [0.50, 0.60, 0.70, 0.80]

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

    # Bootstrap CI: resample the held-out set with replacement many times
    # and recompute AUC on each resample, using predictions already
    # computed above (no retraining). This says how much confidence to
    # place in the single AUC estimate on its own -- it does not compare
    # against any earlier version of this model, since an earlier
    # feature set no longer exists in this pipeline to compare against.
    rng = np.random.default_rng(RANDOM_SEED)
    y_test_arr = y_test.to_numpy()
    boot_aucs = []
    n = len(y_test_arr)
    for _ in range(N_BOOTSTRAP):
        sample_idx = rng.integers(0, n, n)
        y_sample = y_test_arr[sample_idx]
        if y_sample.min() == y_sample.max():
            continue  # AUC undefined if the resample has only one class
        boot_aucs.append(roc_auc_score(y_sample, test_scores[sample_idx]))
    ci_low, ci_high = np.percentile(boot_aucs, [2.5, 97.5])

    print(f"Held-out AUC: {test_auc:.3f} (95% bootstrap CI: {ci_low:.3f}-{ci_high:.3f}, "
          f"{len(boot_aucs)} resamples)")

    fpr, tpr, _ = roc_curve(y_test, test_scores)
    plt.figure(figsize=(5, 5))
    plt.plot(fpr, tpr, label=f"AUC = {test_auc:.3f} (95% CI {ci_low:.3f}-{ci_high:.3f})")
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

    # Sensitivity check: does the headline story depend on 0.60 specifically,
    # or does it hold up across nearby thresholds? Reuses the lead_score
    # already computed above -- no retraining needed for this.
    sensitivity_rows = []
    for q in SENSITIVITY_QUANTILES:
        thr = df["lead_score"].quantile(q)
        adv = df["lead_score"] >= thr
        sensitivity_rows.append({
            "advance_quantile": q,
            "advance_rate": adv.mean(),
            "leads_advanced": int(adv.sum()),
            "conversion_rate_advanced": df.loc[adv, "converted"].mean(),
            "conversion_rate_not_advanced": df.loc[~adv, "converted"].mean(),
        })
    sensitivity = pd.DataFrame(sensitivity_rows)

    print("\nADVANCE_QUANTILE sensitivity (0.60 is the value actually used):")
    print(sensitivity.to_string(index=False))
    with open(SENSITIVITY_PATH, "w") as f:
        f.write("ADVANCE_QUANTILE sensitivity check\n")
        f.write("Does the advanced/not-advanced conversion gap hold at nearby thresholds,\n")
        f.write("or is 0.60 doing unseen work? 0.60 is the value actually used.\n\n")
        f.write(sensitivity.to_string(index=False))
        f.write("\n")
    print(f"Wrote {SENSITIVITY_PATH}")

    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
