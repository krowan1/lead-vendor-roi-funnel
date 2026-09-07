# regression_r2.R
#
# Statistical companion to the Python lead-scoring model: a linear
# regression of realized revenue per lead against lead-level attributes,
# reported with R^2. This is intentionally NOT the same model as the
# Python classifier -- it answers a different business question:
# "how much of the variation in revenue-per-lead is explained by
# observable attributes at intake?" rather than "will this lead convert?"
#
# Honest read: R^2 on an individual-level marketing-outcome regression is
# expected to be modest (most conversion behavior is noise at the
# individual level). What matters for the business case is which
# coefficients are significant and their direction/size, not chasing a
# high R^2 -- reporting a low R^2 as a limitation, not hiding it, is the
# senior-analyst signal here.
#
# Run from repo root: Rscript r/regression_r2.R

# NOTE: `campaign` and `previous` (used in an earlier version of this
# script) no longer exist in leads_scored.csv -- both were dropped
# upstream in 01_build_leads.py during the vendor-plausibility audit
# (previous/poutcome/pdays describe prior contact history with this
# institution, which a fresh vendor lead wouldn't have; campaign accrues
# after intake). The baseline model below reflects that.

df <- read.csv("data/processed/leads_scored.csv", stringsAsFactors = TRUE)

HEADER <- "=== Revenue-per-lead regression ==="

# --- Baseline model: numeric intake attributes + the classifier's own
# score + vendor. ---
baseline <- lm(
  revenue_realized ~ age + emp_var_rate + cons_price_idx + cons_conf_idx +
    euribor3m + nr_employed + lead_score + vendor,
  data = df
)

# --- Fuller model: adds the categorical intake fields (job, education,
# channel, month, day_of_week) that the Python classifier also uses. Run
# side by side, not silently swapped in, to answer directly: does adding
# these on top of lead_score meaningfully improve the fit, or is it
# mostly redundant with a score that already encodes them? ---
fuller <- lm(
  revenue_realized ~ age + emp_var_rate + cons_price_idx + cons_conf_idx +
    euribor3m + nr_employed + lead_score + vendor +
    job + education + channel + month + day_of_week,
  data = df
)

s_base <- summary(baseline)
s_full <- summary(fuller)

cat(HEADER, "\n", sep = "")
cat(sprintf("Baseline model  - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_base$r.squared, s_base$adj.r.squared))
cat(sprintf("Fuller model    - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_full$r.squared, s_full$adj.r.squared))
cat(sprintf("N observations: %d\n\n", nrow(df)))
cat("Read: if the fuller model's adjusted R-squared isn't meaningfully\n")
cat("higher than the baseline's, that's expected, not a bug -- job/\n")
cat("education/channel/month/day_of_week are already folded into\n")
cat("lead_score by the classifier, so adding them again mostly re-states\n")
cat("information the score already carries rather than adding new signal.\n\n")

cat("Baseline model -- top coefficients by |t value| (excluding intercept):\n")
coefs <- as.data.frame(s_base$coefficients)
coefs <- coefs[order(-abs(coefs$`t value`)), ]
print(head(coefs[rownames(coefs) != "(Intercept)", ], 10))

cat("\n--- lead_score coefficient (the model's own scoring signal) ---\n")
print(coefs["lead_score", ])

# Save a compact summary for the README / demo talking points. Same
# header string as the console output above, so grepping for it finds
# both -- previously these used two different header strings and the
# console-only one never made it into the file.
sink("output/regression_summary.txt")
cat(HEADER, "\n", sep = "")
cat(sprintf("Baseline  - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_base$r.squared, s_base$adj.r.squared))
cat(sprintf("Fuller    - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_full$r.squared, s_full$adj.r.squared))
cat(sprintf("N: %d\n\n", nrow(df)))
cat("--- Baseline model (reported in README) ---\n")
print(s_base)
cat("\n--- Fuller model (categorical intake fields added) ---\n")
print(s_full)
sink()
cat("\nWrote output/regression_summary.txt\n")
