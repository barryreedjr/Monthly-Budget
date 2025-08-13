
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Budget → Pieces Planner", layout="wide")

# ---- Defaults ----
default_categories = [
    {"Category": "Apparel",     "Mix %": 50.0, "Avg Sale": 6.5,  "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
    {"Category": "Wares",       "Mix %": 23.0, "Avg Sale": 5.0,  "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
    {"Category": "Shoes",       "Mix %": 7.0,  "Avg Sale": 9.0,  "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
    {"Category": "Accessories", "Mix %": 7.0,  "Avg Sale": 4.0,  "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
    {"Category": "E&M",         "Mix %": 5.0,  "Avg Sale": 18.0, "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
    {"Category": "Media",       "Mix %": 2.0,  "Avg Sale": 3.0,  "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
    {"Category": "Furniture",   "Mix %": 4.0,  "Avg Sale": 55.0, "Sell-through %": 0.0, "ASP Δ%": 0.0, "ST Δ%": 0.0},
]

# ---- Sidebar ----
st.sidebar.title("Inputs")
monthly_budget = st.sidebar.number_input("Monthly Revenue Target ($)", min_value=0, value=180_000, step=1_000)
days_in_month = st.sidebar.number_input("Days in Month", min_value=1, max_value=31, value=30, step=1)
labor_pct      = st.sidebar.number_input("Labor % of Revenue", min_value=0.0, max_value=100.0, value=40.0, step=1.0)
normalize_mix  = st.sidebar.checkbox("Auto-normalize Mix % to 100% for calculations", value=True)
st.sidebar.caption(f"Labor dollars: **${monthly_budget * labor_pct/100:,.0f}**")

# ---- Title ----
st.title("Budget → Pieces Planner")
st.caption("Enter your target + category metrics. See required **daily pieces** and what-if gains from improving ASP or Sell-Through. Assistant Manager bonus = 2% of incremental revenue.")

# ---- Category editor ----
st.subheader("Category assumptions (edit these)")
df = pd.DataFrame(default_categories)
edited = st.data_editor(
    df[["Category","Mix %","Avg Sale","Sell-through %","ASP Δ%","ST Δ%"]],
    num_rows="fixed", use_container_width=True, hide_index=True,
    column_config={
        "Mix %": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1),
        "Avg Sale": st.column_config.NumberColumn(min_value=0.01, step=0.1, format="%.2f"),
        "Sell-through %": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1),
        "ASP Δ%": st.column_config.NumberColumn(min_value=-100.0, max_value=500.0, step=1.0),
        "ST Δ%": st.column_config.NumberColumn(min_value=-90.0,  max_value=500.0, step=1.0),
    }
).copy()

mix_sum = float(edited["Mix %"].fillna(0).sum())
if normalize_mix and abs(mix_sum - 100) > 1e-6:
    factor = 100.0 / mix_sum if mix_sum != 0 else 0.0
    edited["_Mix_used_"] = edited["Mix %"] * factor
else:
    edited["_Mix_used_"] = edited["Mix %"]

if abs(mix_sum - 100) > 0.5 and not normalize_mix:
    st.warning(f"Category Mix totals **{mix_sum:.2f}%**. Enable *Auto-normalize* or adjust values to sum to 100%.")

# ---- Calculations ----
calc = edited.copy()
calc["mix"] = (calc["_Mix_used_"] / 100.0).astype(float)
calc["asp"] = calc["Avg Sale"].astype(float).clip(lower=0.01)
calc["st"]  = (calc["Sell-through %"] / 100.0).astype(float).clip(lower=0.001)  # avoid divide-by-zero

calc["Target Revenue"]        = monthly_budget * calc["mix"]
calc["Req Sold Units"]        = calc["Target Revenue"] / calc["asp"]
calc["Req Produced Units"]    = calc["Req Sold Units"] / calc["st"]
calc["Daily Required Pieces"] = calc["Req Produced Units"] / days_in_month

# What-If (hold produced units constant)
calc["asp_up"] = calc["asp"] * (1 + (calc["ASP Δ%"].fillna(0.0) / 100.0))
calc["st_up"]  = (calc["st"]  * (1 + (calc["ST Δ%"].fillna(0.0)  / 100.0))).clip(lower=0.001, upper=10.0)

calc["sold_baseline"]    = calc["Req Produced Units"] * calc["st"]   # equals Req Sold Units
calc["sold_whatif"]      = calc["Req Produced Units"] * calc["st_up"]
calc["Revenue Baseline"] = calc["sold_baseline"] * calc["asp"]       # equals Target Revenue
calc["Revenue What-If"]  = calc["sold_whatif"]   * calc["asp_up"]
calc["Incremental Revenue"] = (calc["Revenue What-If"] - calc["Revenue Baseline"]).clip(lower=0.0)
asst_mgr_bonus = float(calc["Incremental Revenue"].sum()) * 0.02

# ---- Display ----
st.subheader("Results by category")
show_cols = [
    "Category","Mix %","Avg Sale","Sell-through %",
    "Target Revenue","Req Sold Units","Req Produced Units","Daily Required Pieces",
    "ASP Δ%","ST Δ%","Revenue What-If","Incremental Revenue"
]
pretty = calc[show_cols].copy()
pretty["Target Revenue"]       = pretty["Target Revenue"].map(lambda x: f"${x:,.0f}")
pretty["Req Sold Units"]       = pretty["Req Sold Units"].round(0).astype(int).astype(str)
pretty["Req Produced Units"]   = pretty["Req Produced Units"].round(0).astype(int).astype(str)
pretty["Daily Required Pieces"]= pretty["Daily Required Pieces"].round(1)
pretty["Revenue What-If"]      = pretty["Revenue What-If"].map(lambda x: f"${x:,.0f}")
pretty["Incremental Revenue"]  = pretty["Incremental Revenue"].map(lambda x: f"${x:,.0f}")

st.dataframe(pretty, use_container_width=True, hide_index=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Daily Production Needed (pcs/day)", f"{calc['Daily Required Pieces'].sum():,.1f}")
with c2:
    st.metric("Labor Allocation (FYI)", f"${monthly_budget * labor_pct/100:,.0f}")
with c3:
    st.metric("What-If: Assistant Manager Bonus (2%)", f"${asst_mgr_bonus:,.0f}")

# Download
csv_bytes = calc[show_cols].to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_bytes, file_name="budget_to_pieces_results.csv", mime="text/csv")
