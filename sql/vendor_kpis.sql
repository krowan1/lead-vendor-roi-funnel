-- vendor_kpis.sql
-- Run with: duckdb -c ".read sql/vendor_kpis.sql"  (from repo root)
-- DuckDB reads leads_scored.csv directly, no server/warehouse needed.

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
    ROUND(SUM(revenue_realized), 2)                             AS revenue,
    ROUND(SUM(revenue_realized) - SUM(cost_per_lead), 2)        AS net_return,
    ROUND((SUM(revenue_realized) - SUM(cost_per_lead))
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
    ROUND((SUM(revenue_realized) - SUM(cost_per_lead))
          / NULLIF(SUM(cost_per_lead), 0), 3)             AS roi_multiple
FROM leads
WHERE vendor IN (SELECT vendor FROM ranked);

-- 5. Funnel by vendor, for the Sankey diagram (intake -> advanced -> converted)
SELECT
    vendor,
    COUNT(*)                       AS intake,
    SUM(advanced)                  AS advanced,
    SUM(CASE WHEN advanced=1 THEN converted ELSE 0 END) AS converted_from_advanced,
    SUM(CASE WHEN advanced=0 THEN converted ELSE 0 END) AS converted_from_not_advanced
FROM leads
GROUP BY vendor
ORDER BY intake DESC;
