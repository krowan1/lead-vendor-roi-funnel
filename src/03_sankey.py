"""
03_sankey.py

Builds the funnel Sankey: Vendor -> Advanced/Deprioritized -> Converted/Not.
Output: output/funnel_sankey.html (open directly in a browser; also embeds
cleanly in a README via screenshot).
"""
import duckdb
import plotly.graph_objects as go

con = duckdb.connect()
con.execute("CREATE VIEW leads AS SELECT * FROM read_csv_auto('data/processed/leads_scored.csv')")

by_vendor = con.execute("""
    SELECT vendor,
           SUM(advanced) AS advanced,
           COUNT(*) - SUM(advanced) AS deprioritized
    FROM leads GROUP BY vendor
""").df()

stage2 = con.execute("""
    SELECT
        SUM(CASE WHEN advanced=1 AND converted=1 THEN 1 ELSE 0 END) AS adv_converted,
        SUM(CASE WHEN advanced=1 AND converted=0 THEN 1 ELSE 0 END) AS adv_not_converted,
        SUM(CASE WHEN advanced=0 AND converted=1 THEN 1 ELSE 0 END) AS depr_converted,
        SUM(CASE WHEN advanced=0 AND converted=0 THEN 1 ELSE 0 END) AS depr_not_converted
    FROM leads
""").df().iloc[0]

vendors = by_vendor["vendor"].tolist()
labels = vendors + ["Advanced (scored high)", "Deprioritized (scored low)",
                     "Converted", "Not Converted"]
idx = {label: i for i, label in enumerate(labels)}

source, target, value, link_color = [], [], [], []

VENDOR_COLOR = "rgba(31,119,180,0.5)"
ADV_COLOR = "rgba(44,160,44,0.5)"
DEPR_COLOR = "rgba(214,39,40,0.5)"

for _, row in by_vendor.iterrows():
    source += [idx[row["vendor"]], idx[row["vendor"]]]
    target += [idx["Advanced (scored high)"], idx["Deprioritized (scored low)"]]
    value += [row["advanced"], row["deprioritized"]]
    link_color += [VENDOR_COLOR, VENDOR_COLOR]

source += [idx["Advanced (scored high)"], idx["Advanced (scored high)"],
           idx["Deprioritized (scored low)"], idx["Deprioritized (scored low)"]]
target += [idx["Converted"], idx["Not Converted"],
           idx["Converted"], idx["Not Converted"]]
value += [stage2["adv_converted"], stage2["adv_not_converted"],
          stage2["depr_converted"], stage2["depr_not_converted"]]
link_color += [ADV_COLOR, ADV_COLOR, DEPR_COLOR, DEPR_COLOR]

node_color = ["#1f77b4"] * len(vendors) + ["#2ca02c", "#d62728", "#17becf", "#7f7f7f"]

fig = go.Figure(data=[go.Sankey(
    node=dict(pad=18, thickness=18, label=labels, color=node_color,
              line=dict(color="rgba(0,0,0,0.3)", width=0.5)),
    link=dict(source=source, target=target, value=value, color=link_color),
)])
fig.update_layout(
    title_text="Lead Funnel: Vendor Intake → Scoring → Conversion",
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
