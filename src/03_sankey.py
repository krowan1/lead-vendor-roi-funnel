"""
03_sankey.py

Builds the funnel Sankey: Vendor -> Converted / Not Converted.

This is deliberately a two-stage, retrospective funnel, not a three-stage
one with an "advanced" middle step. This is historical data: whether a
lead converted already happened, independent of whether today's scoring
model would have flagged it "advanced." A vendor -> advanced -> converted
diagram implies advancing is what let a lead convert, which isn't true of
data collected before the model existed. That question (does the score
actually separate good leads from bad ones) is a real and useful one, but
it belongs in 04_score_lift.py as its own chart, not folded into this
funnel diagram as if it were one more stage of the same pipeline.

Output: output/funnel_sankey.html (open directly in a browser; also embeds
cleanly in a README via screenshot).
"""
import duckdb
import plotly.graph_objects as go

con = duckdb.connect()
con.execute("CREATE VIEW leads AS SELECT * FROM read_csv_auto('data/processed/leads_scored.csv')")

by_vendor = con.execute("""
    SELECT vendor,
           SUM(converted) AS converted,
           COUNT(*) - SUM(converted) AS not_converted
    FROM leads GROUP BY vendor
""").df()

vendors = by_vendor["vendor"].tolist()
labels = vendors + ["Converted", "Not Converted"]
idx = {label: i for i, label in enumerate(labels)}

source, target, value, link_color = [], [], [], []

CONV_COLOR = "rgba(44,160,44,0.5)"
NOT_CONV_COLOR = "rgba(214,39,40,0.5)"

for _, row in by_vendor.iterrows():
    source += [idx[row["vendor"]], idx[row["vendor"]]]
    target += [idx["Converted"], idx["Not Converted"]]
    value += [row["converted"], row["not_converted"]]
    link_color += [CONV_COLOR, NOT_CONV_COLOR]

node_color = ["#1f77b4"] * len(vendors) + ["#2ca02c", "#d62728"]

fig = go.Figure(data=[go.Sankey(
    node=dict(pad=18, thickness=18, label=labels, color=node_color,
              line=dict(color="rgba(0,0,0,0.3)", width=0.5)),
    link=dict(source=source, target=target, value=value, color=link_color),
)])
fig.update_layout(
    title_text="Lead Funnel: Vendor Intake → Conversion (historical outcomes)",
    font_size=13, width=1000, height=600,
    paper_bgcolor="white",
)
fig.write_html("output/funnel_sankey.html", include_plotlyjs="cdn")
try:
    fig.write_image("output/funnel_sankey.png", scale=2)
    print("Wrote output/funnel_sankey.png")
except Exception as e:
    print(f"PNG export skipped ({e}); HTML still written.")
print("Wrote output/funnel_sankey.html")
