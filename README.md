# Lead & Vendor ROI Funnel

**A demo analytics build framed as a client engagement.** The business here is a lead reseller: it buys leads from six vendors, evaluates and scores them, and delivers them to its own customers, earning a fee whenever a delivered lead converts for the customer it went to. The question this project answers is the one that business actually has: are the leads we're buying worth what we pay for them, which vendors should we lean into or drop, and how should we think about buying leads as bundled packages instead of one vendor at a time.

## The business question

> "We're already buying and selling leads. Are we getting good leads from our vendors? What are our margins from lead packages delivered to customers?"

## How the pieces fit together

Each stage below feeds the next one directly, not just conceptually:

1. **Intake** (`01_build_leads.py`) turns a real dataset of 41,188 marketing contacts into a lead file. Every field is checked against one test: could an external lead vendor plausibly know this about a cold contact? Fields that fail that test (marital status, existing loans, prior history with this specific institution) are dropped here, before anything downstream ever sees them.
2. **Evaluation** (`02_lead_scoring_model.py`) takes that intake file and scores each lead's likelihood of converting, using only the fields that survived step 1. The top 40% by score get flagged "advanced," meaning today's model would prioritize them.
3. **KPIs** (`sql/vendor_kpis.sql`) take the scored file and roll it up by vendor: how much was spent, how many converted, what the return looks like. This is the layer a sales or ops leader would actually check week to week.
4. **Statistical check** (`r/regression_r2.R`) asks a different question than the scoring model does: not "will this lead convert" but "does an independently-fit model, using the same raw inputs but built with a different tool, see similar signal." It's a sanity check on the pipeline's own inputs, not a rerun of the same model.
5. **Two separate charts**, deliberately not one. `03_sankey.py` shows what actually happened, historically, by vendor (converted or not). `04_score_lift.py` shows a different thing: whether today's scoring model would have separated good leads from bad ones, using score deciles. These answer different questions and are kept apart rather than forced into one funnel diagram implying that scoring gates conversion, which isn't true of data collected before the model existed.

## What "these numbers mean" (read this before the table)

- **Conversion rate**: converted leads divided by leads purchased, per vendor.
- **Cost per acquisition (CPA)**: total spend on a vendor divided by that vendor's conversions. Lower is better.
- **ROI multiple**: revenue divided by cost, the standard convention. A 3.0x means $3 comes back for every $1 spent, total, not $3 of profit on top of the dollar. Below 1.0x is the only way to actually lose money under this definition.
- **Net return**: revenue minus cost, in raw dollars, so you can see scale alongside the ratio. A great ROI multiple on a small vendor can still be worth less in dollars than a mediocre one on a large vendor.
- **Advance rate**: the share of leads that scored high enough that today's model would flag them worth a sales rep's time (top 40%, see the scoring section for why 40%, and for a check on whether that specific number matters).
- **Revenue** here means the fee the reseller collects from its own customer when a delivered lead converts, not the value of whatever the customer's business sells. It's not a stored column: it's always exactly a flat per-conversion fee times whether the lead converted, so it's computed at query time (`SUM(converted) * 640` in the SQL) rather than kept as a redundant column on every row. That's a real warehouse-scale habit, not just tidiness: storing a value that's one multiply away from data you already have is wasted storage and I/O once a dataset is large.

Cost per lead and the per-conversion fee are the one layer of this project that's an assumption rather than measured fact. See **Data & assumptions** below for exactly what's assumed and why.

## Key findings (from this run)

| Vendor | Leads | Conversion Rate | ROI Multiple | Cost / Acquisition | Net Return |
|---|---:|---:|---:|---:|---:|
| Fieldstone List | 5,219 | 12.1% | **7.94x** | $81 | $352,955 |
| Apex Data Group | 7,406 | 10.1% | 5.36x | $119 | $387,288 |
| Meridian Leads | 6,495 | 11.8% | 4.07x | $157 | $368,803 |
| Summit Outreach | 6,915 | 11.7% | 2.74x | $233 | $328,686 |
| Coastal Direct | 7,384 | 10.9% | 2.04x | $313 | $261,584 |
| Northbridge Mktg | 7,769 | 11.5% | **1.58x** | $405 | $209,622 |

Overall: 41,188 leads in, 16,478 advanced by today's scoring model (40.0%), 4,640 converted historically (11.3% overall conversion rate).

**Read this the way a client would:**
- **Fieldstone List is the standout.** Cheapest cost per lead and the best return by a wide margin. This is the vendor to scale first.
- **No vendor here is actually losing money**, and that's worth saying plainly rather than overstating the worst case. Every vendor returns more than it costs. The real story is the spread: Fieldstone returns nearly 8x, Northbridge returns 1.6x. That's still the single highest-leverage gap in the scorecard, it's just a gap in how efficiently spend converts to return, not a vendor operating at an outright loss.
- **Conversion rate alone would send you the wrong direction.** Northbridge actually converts leads at 11.5%, better than four of the other five vendors. It's cost, not lead quality, that makes it the weakest performer. That distinction is the entire point of tracking ROI and CPA instead of stopping at conversion rate, and it's visible directly in this table: conversion rates cluster tightly between 10 and 12% across every vendor, while ROI multiples range from 1.6x to nearly 8x. Cost is doing almost all of the differentiating work here, not lead quality.
- A simple "buy the two cheapest vendors" bundle (Fieldstone + Apex) returns **6.3x** across 12,625 combined leads. That's not as good as Fieldstone alone, but it's a real answer to the "how do we think about packages" half of the business question: pairing a strong, low-volume vendor with a cheaper, higher-volume one gives real scale without giving up much return. Bundling is a secondary result here, not the headline, the vendor scorecard is, but it's a genuine one worth having ready if a client asks about it.

## The lead-scoring model

A logistic regression model scores each lead on likelihood to convert, using only fields a vendor could plausibly hand over about a cold contact: age, job, education, how the lead was sourced (landline or mobile), when it came in, and a handful of market-condition indicators (employment variation rate, consumer price and confidence indices, the Euribor rate, and number of employees in the economy at the time). Held-out AUC is **0.800** (95% bootstrap confidence interval: 0.784 to 0.814, from 1,000 resamples of the held-out set).

Two things worth calling out:

- **Fields like marital status, existing loans, and prior contact history with this specific institution were deliberately left out**, even though they were available in the source data. A vendor selling a cold lead has no way to know someone's marital status or credit obligations, and if a "lead" already has history with this institution, it isn't really a new lead at all. Excluding that data is a real, disclosed limitation of the model, not something the number above hides.
- The top 40% of leads by score get flagged "advanced." That threshold is a stated operational assumption standing in for a sales team's realistic working capacity, not something derived from the data. A sensitivity check (`output/advance_threshold_sensitivity.txt`) reruns the same math at 50%, 60%, 70%, and 80% advance rates: the gap between advanced and not-advanced conversion rates holds and widens as the threshold tightens (18.5% vs. 4.0% at 50%, up to 34.8% vs. 5.4% at 80%), so the story isn't fragile to the exact 40% pick, the model separates leads consistently across a range of thresholds. 40% itself is still a business judgment about sales capacity, not something this check derives on its own.

An ROC curve (`output/roc_curve.png`) and a score-decile lift chart (`output/score_lift_chart.png`, showing the top-scored 10% of leads converting at 47.0% against a bottom decile of 3.4%) back the model up visually instead of asking you to take a single number on faith.

## The regression check

A linear regression checks whether an independently-fit model, using the same raw inputs but built with a different tool, sees similar signal to the classifier. It is **not** a regression on revenue, and does not use the classifier's own score as a predictor. Two earlier drafts of this got that wrong, worth naming directly since fixing them changed the actual conclusion:

- Regressing dollar revenue instead of the 0/1 conversion outcome added nothing: revenue here is a flat fee times conversion, a linear rescaling of the same target, so the R² would be identical either way, it just adds a dollar sign, not new information. This regression predicts `converted` directly.
- Using the classifier's own `lead_score` as a predictor isn't an independent check, it's comparing the model to its own prediction of the exact thing it was trained to predict. This regression uses only the raw intake fields, none of the classifier's own output.

Two versions were run, to separate what the market explains from what the specific lead explains:

- **Market-only** (macro indicators and vendor): R² = 0.138 (adjusted 0.138).
- **Full** (market-only plus age, job, education, channel, month, day of week): R² = 0.186 (adjusted 0.185).

Lead-specific attributes roughly triple the explained variance over market conditions alone, a real and meaningful result. Vendor's own coefficients are mostly statistically insignificant in both models (one vendor sits at a borderline p ≈ 0.03 with a very small effect size, which is close to what you'd expect from testing five vendor comparisons by chance alone). That near-insignificance isn't a discovery about vendor quality: vendor is assigned from a hash of channel, job, and age that has no relationship to whether the underlying contact actually converted, so vendor showing no independent effect on conversion here is guaranteed by construction, not something this regression found. The real, business-relevant vendor differences (conversion rate, ROI, cost per acquisition) live in the KPI table above and stand on their own; this regression answers a separate question about the intake data generally; it isn't cited as proof of the vendor story, and it doesn't need to be.

This is a linear probability model (ordinary linear regression on a 0/1 outcome), not a logistic regression, which is a real, disclosed limitation: predicted values can technically fall outside 0 to 1. It's used anyway because it keeps R² directly comparable to how this project talks about it throughout, and it's standard practice for exactly this kind of "how much variance is explained, and by what" question.

An R² around 0.14 to 0.19 on an individual-level marketing outcome is a modest, believable number. Most of the variation in whether one specific person converts is noise no model captures, and a much higher R² here would actually be a warning sign of overfitting or a leak somewhere in the pipeline.

## What I'd do next as the analytics lead

1. **Reallocate spend, carefully.** Shift budget toward Fieldstone List and away from Northbridge Mktg and Coastal Direct, but in tranches, not all at once. Lead quality from a vendor can shift when you suddenly ask for a lot more volume, so I'd scale up in steps and re-check conversion rate at each one before going further.
2. **Take the scorecard into a Northbridge conversation.** It's the weakest performer, not a loss, so this is a real negotiation, not an ultimatum: either the price comes down toward the field's average return, or volume gets redirected toward stronger vendors over time.
3. **Propose the Fieldstone + Apex bundle as a standing option**, with lead score as the acceptance gate rather than a flat per-lead price. That's a concrete answer to the "how should we think about packages" question the business asked.
4. **Close the loop on the scoring model.** It only sees what's known at intake. The next iteration should feed realized outcomes back in on a schedule and watch for the model's accuracy drifting as vendor mix shifts over time.
5. **Set a real re-evaluation cadence for the two assumptions everything else rests on**, rather than leaving them open-ended:
   - **The 40% advance threshold** gets re-checked whenever sales team capacity changes (headcount, tooling) or whenever the advanced segment's realized conversion rate drifts from its historical baseline. The decision rule is whether the team's actual capacity to work leads still matches the volume the threshold produces.
   - **Vendor cost and the per-conversion fee** get replaced with real invoice and CRM numbers the moment they exist, and reviewed at minimum on a quarterly cadence tied to contract renewals in the meantime. The decision rule is simple: an assumed number never survives past the point a measured one is available.
6. **Turn this into a living scorecard, not a one-time report.** This was run once, as a point-in-time analysis. In production it becomes a scheduled job that reruns the SQL layer on a cadence, which this is already structured to support without a rebuild.

## Data & assumptions (read this before judging the numbers)

The underlying behavioral data is real: the [UCI Bank Marketing dataset](https://archive.ics.uci.edu/dataset/222/bank+marketing), 41,188 real marketing contacts, public. Its original outcome (subscribed to a term deposit: yes/no) stands in here for "did this delivered lead convert for the customer it went to," a disclosed proxy, not a claim that this is literally a banking dataset used as-is. No company hands out real vendor-level lead-purchase data either, so a few things here are constructed rather than measured, and every one is disclosed rather than presented as real:

- **Vendor labels are a deterministic reframing** of real channel, job, and age combinations into 6 pseudo-vendors. The mapping uses a stable hash, so it's reproducible on every run, not random, and it's auditable in `src/01_build_leads.py`.
- **Cost per lead and the per-conversion fee are illustrative assumptions**, documented directly in `src/01_build_leads.py`. The spread between vendors ($9.75 to $46.50 per lead) is meant to be directionally realistic for a lead-gen business, not fitted to produce a nicer-looking story.
- **Every column kept in the dataset passed a plausibility check**: could an outside lead vendor actually know this about someone before we've contacted them? Marital status, existing loans, and history with this specific institution failed that test and were removed at the source, not just excluded from the model. The `channel` field keeps the real distinction the source data actually supports (which device reached the contact, landline or mobile), relabeled into lead-vendor language rather than reframed into a story the data doesn't back up.
- The **lead-scoring model, funnel structure, KPI math, and regression are real analysis** run on real, if relabeled, data. Only the vendor economics layer (what a vendor charges, and what a conversion is worth) is a stated assumption standing in for numbers a live engagement would supply on day one.

**On scale:** this runs comfortably on a laptop at 41,188 rows using pandas in memory. That's the right choice at this size. It would not be the right choice at 1M+ rows, and the parts of this pipeline that would actually break first are already built to avoid that outcome: vendor assignment is vectorized rather than looping row by row, the assignment key is built so its distinct-value count stays small relative to row count as data grows, and revenue is computed at query time instead of stored as a redundant per-row column. Past a few million rows, the next real move would be a proper warehouse (the SQL layer here already reads like DuckDB, so migrating to Postgres or Snowflake is a connection change more than a rewrite) and chunked or streaming reads for the intake step. None of that is built out here because building it for data that doesn't exist yet would be its own kind of overengineering, but the design decisions already point that direction.

## Repo structure

```
data/raw/                    downloaded UCI source data
data/processed/              leads.csv, leads_scored.csv
src/01_build_leads.py        ingest, vendor assignment, plausibility audit
src/02_lead_scoring_model.py logistic regression lead scoring, AUC bootstrap CI, threshold sensitivity
src/03_sankey.py             retrospective funnel: vendor -> converted / not
src/04_score_lift.py         does the score separate good leads from bad ones (decile lift chart)
sql/vendor_kpis.sql          DuckDB KPI queries (funnel, ROI, bundling)
r/regression_r2.R            independent conversion regression, market-only vs. full model
output/                      funnel_sankey.html/png, roc_curve.png, score_lift_chart.png,
                              advance_threshold_sensitivity.txt, regression_summary.txt
```

## Running it

```bash
pip install -r requirements.txt
python src/01_build_leads.py
python src/02_lead_scoring_model.py
python src/03_sankey.py
python src/04_score_lift.py
duckdb -c ".read sql/vendor_kpis.sql"
Rscript r/regression_r2.R
```

## Stack

Python (pandas, scikit-learn, matplotlib, Plotly), SQL (DuckDB), R. Chosen deliberately over a cloud data warehouse so this runs for anyone who clones it, no cloud account or billing required.
