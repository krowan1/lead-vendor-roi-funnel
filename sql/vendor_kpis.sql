-- vendor_kpis.sql
-- Run with: duckdb -c ".read sql/vendor_kpis.sql"  (from repo root)
-- DuckDB reads leads_scored.csv directly, no server/warehouse needed.
--
-- revenue_realized is not a stored column: it's always exactly
-- REVENUE_PER_CONVERSION x converted (see src/01_build_leads.py, the
-- source of truth for this constant), so it's computed here at query
-- time as SUM(converted) * 640 rather than materialized per row.
--
-- roi_multiple below is revenue / cost (the standard convention: a 3.0x
-- means $3 back per $1 spent), not (revenue - cost) / cost. Read the
-- number as "total return," not "profit on top of spend."

CREATE OR REPLACE VIEW leads AS
    SELECT * FROM read_csv_auto('data/processed/leads_scored.csv');

-- 1. Funnel overview: intake -> advanced (scored & prioritized) -> converted
SELECT
    COUNT(*)                                   AS leads_intake,
    SUM(advanced)                              AS leads_advanced,
    SUM(converted)                             AS leads_converted,
    ROUND(SUM(advanced) * 1.0 / COUNT(*), 4)   AS advance_rate,
    ROUND(SUM(converted) * 1.0 / COUNT(*), 4)  AS overall_conversion_rate
FROM leads;

-- 2. Vendor scorecard: cost, conversion, ROI, cost-per-acquisition
SELECT
    vendor,
    COUNT(*)                                                   AS leads_purchased,
    ROUND(SUM(cost_per_lead), 2)                                AS total_spend,
    SUM(converted)                                              AS conversions,
    ROUND(SUM(converted) * 1.0 / COUNT(*), 4)                   AS conversion_rate,
    ROUND(AVG(lead_score), 3)                                   AS avg_lead_score,
    ROUND(SUM(converted) * 640, 2)                              AS revenue,
    ROUND(SUM(converted) * 640 - SUM(cost_per_lead), 2)         AS net_return,
    ROUND(SUM(converted) * 640
          / NULLIF(SUM(cost_per_lead), 0), 3)                   AS roi_multiple,
    ROUND(SUM(cost_per_lead) / NULLIF(SUM(converted), 0), 2)    AS cost_per_acquisition
FROM leads
GROUP BY vendor
ORDER BY roi_multiple DESC;

-- 3. Vendor quality vs price: are we paying more for better leads, or not?
SELECT
    vendor,
    ROUND(AVG(cost_per_lead), 2)   AS avg_cost_per_lead,
    ROUND(AVG(lead_score), 3)      AS avg_lead_score,
    ROUND(AVG(converted), 4)       AS conversion_rate
FROM leads
GROUP BY vendor
ORDER BY avg_cost_per_lead DESC;

-- 4. Bundling simulation: if we bundled the two cheapest vendors by CPL,
--    what conversion rate / ROI would that bundle actually deliver?
WITH ranked AS (
    SELECT vendor, AVG(cost_per_lead) AS avg_cpl
    FROM leads GROUP BY vendor
    ORDER BY avg_cpl ASC LIMIT 2
)
SELECT
    'Cheapest-2 bundle' AS bundle,
    COUNT(*)                                              AS leads,
    ROUND(SUM(cost_per_lead), 2)                          AS spend,
    SUM(converted)                                        AS conversions,
    ROUND(SUM(converted) * 1.0 / COUNT(*), 4)             AS conversion_rate,
    ROUND(SUM(converted) * 640
          / NULLIF(SUM(cost_per_lead), 0), 3)             AS roi_multiple
FROM leads
WHERE vendor IN (SELECT vendor FROM ranked);

-- 5. Funnel by vendor, for the Sankey diagram (intake -> converted / not).
--    Two stages, not three: whether a lead converted already happened,
--    independent of whether today's scoring model would flag it
--    "advanced." See 03_sankey.py and 04_score_lift.py for why that's a
--    separate chart, not a third stage of this one.
SELECT
    vendor,
    COUNT(*)                       AS intake,
    SUM(converted)                 AS converted,
    COUNT(*) - SUM(converted)      AS not_converted
FROM leads
GROUP BY vendor
ORDER BY intake DESC;
