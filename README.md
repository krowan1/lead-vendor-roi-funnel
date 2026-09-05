# Lead & Vendor ROI Funnel

**A demo analytics build framed as a client engagement**: a company buys leads from multiple vendors, evaluates and prioritizes them, and needs to know — in dollars, not vanity metrics — which vendors are worth the spend, which should be dropped, and how to think about bundling. This project answers that end to end: real intake data, a lead-scoring model, vendor-level KPIs and ROI, and a funnel visualization built to sit in front of a client.

## The business question

> "We're already buying and selling leads. Are we getting good leads from our vendors? Who should we prioritize? How should we think about bundling?"

## What this shows

| Stage | Deliverable |
|---|---|
| Intake | Real-world lead data, reframed as a multi-vendor acquisition funnel |
| Evaluation | A logistic regression lead-scoring model (held-out AUC 0.805) — which leads get advanced |
| KPIs | Vendor-level conversion rate, cost-per-acquisition, ROI multiple, bundling economics — via SQL |
| Statistical rigor | Linear regression (R) on revenue-per-lead — **R² = 0.202**, reported honestly including its limits |
| Executive view | A Sankey diagram: vendor → scored/advanced → converted |

## Key findings (from this run)

| Vendor | Leads | Conversion Rate | ROI Multiple | Cost / Acquisition |
|---|---:|---:|---:|---:|
| Apex Data Group | 3,946 | 16.8% | **7.96x** | $71 |
| Fieldstone List | 14,982 | 8.1% | 4.30x | $121 |
| Meridian Leads | 8,681 | 10.7% | 2.69x | $174 |
| Summit Outreach | 3,729 | 15.1% | 2.55x | $180 |
| Coastal Direct | 3,778 | 14.4% | 1.71x | $237 |
| Northbridge Mktg | 6,072 | 12.1% | **0.67x** | $384 |

**Read this the way a client would:**
- **Apex Data Group is the standout** — cheapest per lead *and* highest ROI. This is the vendor to scale first, not just keep.
- **Northbridge Mktg is currently a net loss** — 0.67x ROI means every dollar spent returns 67 cents. Cutting or renegotiating this vendor is the single highest-leverage move available.
- **Fieldstone List is the volume vendor** — lowest conversion rate but largest volume and still solidly profitable (4.3x); it's the right vendor to keep for scale, not for quality.
- The naive "cheapest-2 bundle" simulation (Apex + Fieldstone) returns **5.2x ROI** — better than either mid-tier vendor alone, which is the actual argument for how to build a bundle: pair a high-quality, low-volume vendor with a cheap, high-volume one rather than bundling on price alone.

**Regression check (R):** a linear model of revenue-per-lead against intake-time attributes returns **R² = 0.202** (adjusted 0.201, n=41,188). That's a modest but real result for individual-level marketing outcomes — most of the variance in whether one specific lead converts is noise a model can't capture, and a much higher R² here would actually be a red flag (overfitting or leakage). The more useful read is the coefficients: `lead_score` itself is by far the strongest predictor (t = 52.4), which cross-validates the Python scoring model against an independent method — the two approaches agree. `previous` (prior contact count), `cons_conf_idx`, and `euribor3m` are also significant, giving three concrete, non-vendor levers for improving lead quality upstream, not just picking better vendors.

## What I'd do next as the analytics lead

1. **Reallocate spend**: shift budget out of Northbridge Mktg and Coastal Direct toward Apex Data Group, tested incrementally (not all at once — vendor lead quality can degrade under higher-volume orders, so I'd scale in tranches and re-check conversion rate at each step).
2. **Renegotiate, don't just cut**: take the vendor scorecard into a Northbridge conversation — either price drops to reach breakeven ROI, or the relationship ends this quarter.
3. **Build the bundle formally**: propose a standing Apex + Fieldstone bundle as the default buy, with lead-score threshold as the acceptance gate rather than a flat per-lead price.
4. **Close the loop on scoring**: the lead-scoring model (AUC 0.805) is intake-time only. Next iteration: feed realized outcomes back in monthly and monitor for score drift as vendor mix shifts.
5. **Instrument this as a living scorecard**: this was run once, as a point-in-time analysis. In production this becomes a scheduled job (weekly vendor scorecard) rather than a one-off report — the SQL layer here is written so that's a scheduling problem, not a rebuild.

## Data & assumptions (read this before judging the numbers)

The underlying behavioral data is real: the [UCI Bank Marketing dataset](https://archive.ics.uci.edu/dataset/222/bank+marketing) (41,188 real marketing contacts, public). No company hands out real vendor-level lead-purchase data, so:

- **Vendor labels are a deterministic reframing** of real contact-channel + prior-campaign-outcome combinations into 6 pseudo-vendors — reproducible, not random, and disclosed here rather than presented as real vendor identities.
- **Cost-per-lead and revenue-per-conversion are illustrative assumptions**, documented in `src/01_build_leads.py`, chosen to be realistic for a lead-gen business rather than fitted to produce a nice story.
- The **lead-scoring model, funnel structure, KPI math, and R² regression are real analysis** run on real (if relabeled) data — only the vendor economics layer is a stated assumption.

This structure — real behavioral data, a disclosed assumption layer for the business inputs a real engagement would supply — is the same shape I'd use with an actual client's data on day one.

## Repo structure

```
data/raw/                   downloaded UCI source data
data/processed/              leads.csv, leads_scored.csv
src/01_build_leads.py        ingest + vendor/economics reframing
src/02_lead_scoring_model.py logistic regression lead scoring
src/03_sankey.py             funnel Sankey diagram (Python/Plotly)
sql/vendor_kpis.sql          DuckDB KPI queries (funnel, ROI, bundling)
r/regression_r2.R            revenue regression with R², reported honestly
output/                      funnel_sankey.html/png, regression_summary.txt
```

## Running it

```bash
pip install -r requirements.txt
python src/01_build_leads.py
python src/02_lead_scoring_model.py
python src/03_sankey.py
duckdb -c ".read sql/vendor_kpis.sql"
Rscript r/regression_r2.R
```

## Stack

Python (pandas, scikit-learn, Plotly) · SQL (DuckDB) · R — chosen deliberately over a cloud data warehouse so this runs for anyone who clones it, no cloud account or billing required.
