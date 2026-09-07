"""
01_build_leads.py

Reframes the UCI Bank Marketing dataset (real, public: 41,188 marketing
contacts, archive.ics.uci.edu/dataset/222) as a lead-generation / vendor
funnel: each contact becomes a "lead" acquired through a channel, and the
original outcome (subscribed to term deposit: yes/no) becomes "converted".

IMPORTANT — documented assumption layer:
The source data has no vendor field. To demonstrate vendor-level ROI and
bundling analysis (the point of this project), leads are deterministically
grouped into 6 pseudo-vendors from their contact channel + job + age
combination, and each vendor is assigned an illustrative cost-per-lead
and revenue-per-conversion. These are clearly synthetic business
assumptions layered on top of real behavioral data — not claimed as real
vendor financials. See README "Data & Assumptions" section.

IMPORTANT — plausibility audit:
Columns are kept only if an external lead vendor could plausibly supply
them about a cold contact. `marital`, `default`, `housing`, `loan` are
dropped as private financial/credit facts a vendor wouldn't have.
`pdays`, `previous`, `poutcome` are dropped for a structural reason, not
just a plausibility one: they describe prior campaign history *with this
institution* — a contact with that history isn't a fresh vendor lead.
`month` and `day_of_week` are kept as separate columns (delivery date is
vendor-knowable) but are deliberately not merged into one field or used
for vendor assignment. `campaign` (contacts made during the current
campaign) is dropped for a different reason: that count accrues *after*
lead delivery, so using it as an intake-time feature risks leaking
information from later in the funnel back into the score. `contact` is
kept but relabeled from telephone/cellular to inbound/outbound — a
disclosed reframing (like the vendor names) of how the lead came in,
rather than the device used to reach them.
"""
import hashlib

import pandas as pd
import numpy as np

RAW_PATH = "data/raw/bank-additional/bank-additional-full.csv"
OUT_PATH = "data/processed/leads.csv"

# Illustrative vendor economics (documented assumption, not real data).
# Cost per lead varies by acquisition channel quality; revenue per
# conversion held constant since the underlying product (term deposit)
# is the same regardless of source.
#
# The spread ($9.75-$46.50/lead) is directional, not fitted: it tracks how
# curated finance-vertical leads are typically priced (cheap high-volume
# lists at the low end, hand-vetted/warm leads at the high end), not a
# specific market quote. revenue_per_conversion is held flat across
# vendors as an assumed average product value, since the underlying
# product (term deposit) doesn't vary by source.
VENDOR_ECONOMICS = {
    "Vendor A - Meridian Leads":   {"cost_per_lead": 18.50, "revenue_per_conversion": 640},
    "Vendor B - Coastal Direct":   {"cost_per_lead": 34.00, "revenue_per_conversion": 640},
    "Vendor C - Apex Data Group":  {"cost_per_lead": 12.00, "revenue_per_conversion": 640},
    "Vendor D - Northbridge Mktg": {"cost_per_lead": 46.50, "revenue_per_conversion": 640},
    "Vendor E - Fieldstone List":  {"cost_per_lead": 9.75,  "revenue_per_conversion": 640},
    "Vendor F - Summit Outreach":  {"cost_per_lead": 27.25, "revenue_per_conversion": 640},
}
VENDOR_NAMES = list(VENDOR_ECONOMICS.keys())

# Columns dropped entirely (not just excluded from modeling): the first
# group because a lead vendor could not plausibly supply them about a
# cold contact, `campaign` because it accrues after intake (leakage
# risk). See the plausibility-audit note above for reasoning per column.
IMPLAUSIBLE_COLUMNS = [
    "marital", "default", "housing", "loan", "pdays", "previous", "poutcome",
    "campaign",
]

# Disclosed relabeling: the source field is the device used to reach the
# contact (landline vs. mobile). Reframed as how the lead came in, which
# is what a lead vendor would actually report.
CHANNEL_LABELS = {"telephone": "outbound", "cellular": "inbound"}


def assign_vendors(df: pd.DataFrame) -> pd.Series:
    """Deterministic pseudo-vendor assignment from real fields, so re-runs
    are reproducible and the mapping is auditable, not random.

    Vectorized rather than row-by-row: `contact` x `job` x `age` has a
    small, fixed number of distinct combinations relative to row count
    (1,037 of 41,188 rows in this dataset) regardless of how large the
    dataset grows, so the hash is computed once per distinct key and
    joined back via `map` instead of once per row. At 1M+ rows an
    iterrows()/apply() loop is the actual bottleneck in this script; this
    keeps the assignment O(n) with a small constant cost as data grows.
    """
    # Python's built-in hash() is randomized per-process (PYTHONHASHSEED)
    # for strings, so it is NOT stable across runs -- using it here would
    # silently reshuffle vendor buckets on every re-run despite the
    # "reproducible" intent above. hashlib.md5 is stable across processes
    # and Python versions, so the same key always maps to the same vendor.
    def stable_hash(s: str) -> int:
        return int(hashlib.md5(s.encode()).hexdigest(), 16)

    key = df["contact"] + "|" + df["job"] + "|" + df["age"].astype(str)
    lookup = {
        k: VENDOR_NAMES[stable_hash(k) % len(VENDOR_NAMES)] for k in key.unique()
    }
    return key.map(lookup)


def main():
    # pandas' CSV parser already handles this file's `"`-quoted fields and
    # headers natively (verified: no leftover quote characters after
    # read_csv) — no manual quote-stripping needed.
    df = pd.read_csv(RAW_PATH, sep=";")
    df.columns = [c.replace(".", "_") for c in df.columns]

    df["vendor"] = assign_vendors(df)
    df = df.drop(columns=IMPLAUSIBLE_COLUMNS)

    df = df.rename(columns={"y": "converted", "contact": "channel"})
    df["channel"] = df["channel"].map(CHANNEL_LABELS)
    df["converted"] = (df["converted"] == "yes").astype(int)
    df["lead_id"] = df.index + 100000

    df["cost_per_lead"] = df["vendor"].map(lambda v: VENDOR_ECONOMICS[v]["cost_per_lead"])
    df["revenue_if_converted"] = df["vendor"].map(lambda v: VENDOR_ECONOMICS[v]["revenue_per_conversion"])
    df["revenue_realized"] = df["revenue_if_converted"] * df["converted"]

    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} leads to {OUT_PATH}")
    print(df["vendor"].value_counts())
    print(f"Overall conversion rate: {df['converted'].mean():.2%}")


if __name__ == "__main__":
    main()
