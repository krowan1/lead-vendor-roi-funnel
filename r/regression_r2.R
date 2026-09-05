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

df <- read.csv("data/processed/leads_scored.csv", stringsAsFactors = TRUE)

model <- lm(
  revenue_realized ~ age + campaign + previous + emp_var_rate +
    cons_price_idx + cons_conf_idx + euribor3m + nr_employed +
    lead_score + vendor,
  data = df
)

s <- summary(model)
cat("=== Revenue-per-lead regression ===\n")
cat(sprintf("R-squared: %.4f\n", s$r.squared))
cat(sprintf("Adjusted R-squared: %.4f\n", s$adj.r.squared))
cat(sprintf("N observations: %d\n\n", nrow(df)))

cat("Top coefficients by |t value| (excluding intercept):\n")
coefs <- as.data.frame(s$coefficients)
coefs <- coefs[order(-abs(coefs$`t value`)), ]
print(head(coefs[rownames(coefs) != "(Intercept)", ], 10))

cat("\n--- lead_score coefficient (the model's own scoring signal) ---\n")
print(coefs["lead_score", ])

# Save a compact summary for the README / demo talking points.
sink("output/regression_summary.txt")
cat("Revenue-per-lead regression summary\n")
cat(sprintf("R-squared: %.4f | Adjusted R-squared: %.4f | N: %d\n\n",
            s$r.squared, s$adj.r.squared, nrow(df)))
print(s)
sink()
cat("\nWrote output/regression_summary.txt\n")
