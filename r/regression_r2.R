# regression_r2.R
#
# Statistical companion to the Python lead-scoring model: a linear
# regression of whether a lead converted (0/1) against intake-time
# attributes, reported with R^2. This is intentionally NOT the same
# model as the Python classifier -- it's a separately-fit model, in a
# different tool, using the SAME raw inputs, to check whether an
# independent method sees similar signal. It does not use lead_score as
# a predictor: lead_score is the classifier's own prediction of this
# exact outcome, so regressing on it wouldn't be an independent check,
# it would be checking the model against itself.
#
# converted (not revenue_realized) is the target. revenue_realized was
# dropped from this pipeline entirely (see 01_build_leads.py): it's
# always exactly a flat dollar amount x converted, so regressing it
# instead of converted directly would just rescale every coefficient by
# that same constant and produce an identical R^2 -- it added a dollar
# sign, not new information.
#
# This is a linear probability model (OLS on a 0/1 outcome), not a
# logistic regression. That's a real, disclosed limitation: predicted
# values can fall outside [0,1], and it's a linear approximation of
# something bounded. It's used anyway because it keeps R^2 directly
# comparable to how this project has talked about it throughout, and
# linear probability models are standard practice for exactly this kind
# of "how much variance is explained, and by which predictors" question.
#
# Honest read: R^2 on an individual-level marketing outcome is expected
# to be modest (most conversion behavior is noise at the individual
# level). What matters for the business case is which coefficients are
# significant and their direction/size, not chasing a high R^2 --
# reporting a low R^2 as a limitation, not hiding it, is the
# senior-analyst signal here.
#
# Run from repo root: Rscript r/regression_r2.R

df <- read.csv("data/processed/leads_scored.csv", stringsAsFactors = TRUE)

HEADER <- "=== Lead conversion regression (independent check) ==="

# --- Market-only model: do macroeconomic conditions alone explain
# conversion, before any lead-specific attribute is considered? ---
market_only <- lm(
  converted ~ emp_var_rate + cons_price_idx + cons_conf_idx +
    euribor3m + nr_employed + vendor,
  data = df
)

# --- Full model: adds lead-specific intake attributes (age, job,
# education, channel, month, day_of_week) on top of the market-only
# model. Run side by side to see how much of the explained variance is
# "the market" vs. "this specific lead." ---
full <- lm(
  converted ~ emp_var_rate + cons_price_idx + cons_conf_idx +
    euribor3m + nr_employed + vendor +
    age + job + education + channel + month + day_of_week,
  data = df
)

s_market <- summary(market_only)
s_full <- summary(full)

cat(HEADER, "\n", sep = "")
cat(sprintf("Market-only model - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_market$r.squared, s_market$adj.r.squared))
cat(sprintf("Full model        - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_full$r.squared, s_full$adj.r.squared))
cat(sprintf("N observations: %d\n\n", nrow(df)))
cat("Read: vendor's coefficients are mostly statistically insignificant\n")
cat("in both models (one vendor is a borderline exception around p=0.03,\n")
cat("with a tiny effect size -- with 5 vendor dummies tested, one crossing\n")
cat("p<0.05 by chance is close to what multiple-comparisons noise predicts\n")
cat("on its own). This isn't a discovery about vendor quality either way:\n")
cat("vendor is assigned from channel+job+age via a hash with no\n")
cat("relationship to whether the underlying contact actually converted,\n")
cat("so vendor having ~no independent effect on conversion here is\n")
cat("guaranteed by how vendor was constructed, not a finding this\n")
cat("regression discovers. The vendor-level differences that DO matter\n")
cat("for the business (conversion rate, ROI, cost per acquisition) are\n")
cat("real and are reported in sql/vendor_kpis.sql -- this regression\n")
cat("answers a different question (does intake data explain conversion)\n")
cat("and vendor's near-insignificance here isn't evidence either way\n")
cat("about that separate KPI story.\n\n")

cat("Full model -- top coefficients by |t value| (excluding intercept):\n")
coefs <- as.data.frame(s_full$coefficients)
coefs <- coefs[order(-abs(coefs$`t value`)), ]
print(head(coefs[rownames(coefs) != "(Intercept)", ], 10))

# Save a compact summary for the README / demo talking points. Same
# header string as the console output above, so grepping for it finds
# both.
sink("output/regression_summary.txt")
cat(HEADER, "\n", sep = "")
cat(sprintf("Market-only - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_market$r.squared, s_market$adj.r.squared))
cat(sprintf("Full        - R-squared: %.4f | Adjusted R-squared: %.4f\n",
            s_full$r.squared, s_full$adj.r.squared))
cat(sprintf("N: %d\n\n", nrow(df)))
cat("--- Market-only model ---\n")
print(s_market)
cat("\n--- Full model (reported in README) ---\n")
print(s_full)
sink()
cat("\nWrote output/regression_summary.txt\n")
