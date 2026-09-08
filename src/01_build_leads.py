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
kept and relabeled from telephone/cellular to landline-sourced/
mobile-sourced -- this keeps the real distinction the source data
actually supports (which device reached the contact), rather than
inventing a direction-of-contact story the data doesn't back up.
"""
import hashlib

import pandas as pd
import numpy as np

RAW_PATH = "data/raw/bank-additional/bank-additional-full.csv"
OUT_PATH = "data/processed/leads.csv"

# Illustrative vendor economics (documented assumption, not real data).
# Cost per lead varies by acquisition channel quality.
#
# The spread ($9.75-$46.50/lead) is directional, not fitted: it tracks how
# curated finance-vertical leads are typically priced (cheap high-volume
# lists at the low end, hand-vetted/warm leads at the high end), not a
# specific market quote.
VENDOR_ECONOMICS = {
    "Vendor A - Meridian Leads":   {"cost_per_lead": 18.50},
    "Vendor B - Coastal Direct":   {"cost_per_lead": 34.00},
    "Vendor C - Apex Data Group":  {"cost_per_lead": 12.00},
    "Vendor D - Northbridge Mktg": {"cost_per_lead": 46.50},
    "Vendor E - Fieldstone List":  {"cost_per_lead": 9.75},
    "Vendor F - Summit Outreach":  {"cost_per_lead": 27.25},
}
VENDOR_NAMES = list(VENDOR_ECONOMICS.keys())

# What we're paid per converted lead, held flat across vendors as an
# assumed average placement fee (the reseller's take when a delivered
# lead converts for the customer, not the value of whatever product the
# customer ultimately sells -- see README "Data & assumptions"). Kept as
# a single constant rather than a per-row column: revenue is always
# exactly this value times whether the lead converted, so it doesn't
# need to be materialized and re-stored on every row. SQL computes
# revenue as SUM(converted) * this value directly (see sql/vendor_kpis.sql).
REVENUE_PER_CONVERSION = 640

# Columns dropped entirely (not just excluded from modeling): the first
# group because a lead vendor could not plausibly supply them about a
# cold contact, `campaign` because it accrues after intake (leakage
# risk). See the plausibility-audit note above for reasoning per column.
IMPLAUSIBLE_COLUMNS = [
    "marital", "default", "housing", "loan", "pdays", "previous", "poutcome",
    "campaign",
]

# The source field's real meaning: which device reached the contact.
# Kept as-is (not reframed into a story the data doesn't support), just
# relabeled into terms a lead vendor would use.
CHANNEL_LABELS = {"telephone": "landline-sourced", "cellular": "mobile-sourced"}


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
    # Revenue is not stored per-row: it's always exactly REVENUE_PER_CONVERSION
    # x converted, so there's nothing a stored column would add that SQL
    # can't compute directly from `converted` at query time (see
    # sql/vendor_kpis.sql). At warehouse scale, storing a column that's one
    # multiply away from data already on the row is pure wasted storage/IO.

    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df):,} leads to {OUT_PATH}")
    print(df["vendor"].value_counts())
    print(f"Overall conversion rate: {df['converted'].mean():.2%}")


if __name__ == "__main__":
    main()
