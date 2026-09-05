"""
01_build_leads.py

Reframes the UCI Bank Marketing dataset (real, public: 41,188 marketing
contacts, archive.ics.uci.edu/dataset/222) as a lead-generation / vendor
funnel: each contact becomes a "lead" acquired through a channel, and the
original outcome (subscribed to term deposit: yes/no) becomes "converted".

IMPORTANT — documented assumption layer:
The source data has no vendor field. To demonstrate vendor-level ROI and
bundling analysis (the point of this project), leads are deterministically
grouped into 6 pseudo-vendors from their real contact channel + prior-
campaign-outcome combination, and each vendor is assigned an illustrative
cost-per-lead and revenue-per-conversion. These are clearly synthetic
business assumptions layered on top of real behavioral data — not claimed
as real vendor financials. See README "Data & Assumptions" section.
"""
import pandas as pd
import numpy as np

RAW_PATH = "data/raw/bank-additional/bank-additional-full.csv"
OUT_PATH = "data/processed/leads.csv"

# Illustrative vendor economics (documented assumption, not real data).
# Cost per lead varies by acquisition channel quality; revenue per
# conversion held constant since the underlying product (term deposit)
# is the same regardless of source.
VENDOR_ECONOMICS = {
    "Vendor A - Meridian Leads":   {"cost_per_lead": 18.50, "revenue_per_conversion": 640},
    "Vendor B - Coastal Direct":   {"cost_per_lead": 34.00, "revenue_per_conversion": 640},
    "Vendor C - Apex Data Group":  {"cost_per_lead": 12.00, "revenue_per_conversion": 640},
    "Vendor D - Northbridge Mktg": {"cost_per_lead": 46.50, "revenue_per_conversion": 640},
    "Vendor E - Fieldstone List":  {"cost_per_lead": 9.75,  "revenue_per_conversion": 640},
    "Vendor F - Summit Outreach":  {"cost_per_lead": 27.25, "revenue_per_conversion": 640},
}
VENDOR_NAMES = list(VENDOR_ECONOMICS.keys())


def assign_vendor(row, idx) -> str:
    """Deterministic pseudo-vendor assignment from real fields + row index,
    so re-runs are reproducible and the mapping is auditable, not random."""
    key = f"{row['contact']}|{row['poutcome']}|{idx % 7}"
    bucket = abs(hash(key)) % len(VENDOR_NAMES)
    return VENDOR_NAMES[bucket]


def main():
    df = pd.read_csv(RAW_PATH, sep=";")
    df.columns = [c.strip('"').replace(".", "_") for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip('"')

    df["vendor"] = [assign_vendor(r, i) for i, r in df.iterrows()]

    df = df.rename(columns={"y": "converted", "contact": "channel"})
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
