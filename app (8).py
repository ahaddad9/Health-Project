"""
The Spending Paradox — a single-screen Streamlit dashboard.

Two-world story, top to bottom:
  KPIs -> the paradox in numbers
  1    -> more money buys life, up to a point (curve coloured by access)
  2    -> the relentless rise of spending over time
  3    -> inside the rich-country club: access is universal, money stops
          buying life, and heavier countries lag (coloured by obesity)
  4    -> value for money: years lived above/below what spending predicts

Data: Our World in Data (WHO / World Bank / UN). See data.py.
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import data

st.set_page_config(page_title="The Spending Paradox", page_icon="🩺", layout="wide")

CORAL, BLUE, TREND = "#D85A30", "#185FA5", "#5F5E5A"
HL_COLORS = [CORAL, BLUE, "#1D9E75", "#534AB7", "#BA7517"]


# ----------------------------------------------------------------- password
def check_password() -> bool:
    expected = st.secrets.get("password", "health2026")
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("<h2 style='text-align:center'>🩺 The Spending Paradox</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray'>Does more health "
                "spending actually buy longer lives?</p>", unsafe_allow_html=True)
    pw = st.text_input("Password", type="password",
                       label_visibility="collapsed", placeholder="Enter password")
    if pw == expected:
        st.session_state["auth_ok"] = True
        st.rerun()
    elif pw:
        st.error("Incorrect password.")
    st.stop()


@st.cache_data(show_spinner="Loading data…")
def get_data():
    return data.load_data()


def log_fit(x, y):
    m = (x > 0) & np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5:
        return None, None
    b, a = np.polyfit(np.log(x[m]), y[m], 1)
    xs = np.linspace(x[m].min(), x[m].max(), 100)
    return xs, a + b * np.log(xs)


def money(v):
    return "—" if pd.isna(v) else f"${v:,.0f}"


# ----------------------------------------------------------------- app
def main():
    check_password()
    df = get_data()
    lo, hi = data.year_bounds(df)

    st.title("The Spending Paradox")
    st.caption("Health spending buys life expectancy only until access is "
               "universal. After that, efficiency — not budget — decides.")

    with st.sidebar:
        st.header("Filters")
        year = st.slider("Year", lo, hi, 2019 if lo <= 2019 <= hi else hi)
        countries = sorted(df["Entity"].unique())
        highlights = st.multiselect(
            "Highlight countries", countries,
            default=[c for c in data.DEFAULT_HIGHLIGHT if c in countries])
        st.divider()
        st.download_button(
            "⬇ Download merged data (CSV)",
            df.to_csv(index=False).encode("utf-8"),
            "health_spending_merged.csv", "text/csv",
            help="Your submission data file.")
        st.caption(f"Rich-country club = spending ≥ "
                   f"${data.RICH_THRESHOLD:,}/person (PPP).")

    cross = data.cross_section(df, year)
    cmap = {c: HL_COLORS[i % len(HL_COLORS)] for i, c in enumerate(highlights)}

    def hl_layer(sub, x, y):
        h = sub[sub["Entity"].isin(highlights)]
        return go.Scatter(
            x=h[x], y=h[y], mode="markers+text", text=h["Entity"],
            textposition="top center", textfont=dict(size=11),
            marker=dict(size=13, color=[cmap[e] for e in h["Entity"]],
                        line=dict(width=1.5, color="white")),
            hoverinfo="skip", showlegend=False)

    # ---- KPIs
    st.subheader(f"The paradox at a glance · {year}")
    k = st.columns(4)
    if len(highlights) >= 2:
        c1, c2 = highlights[0], highlights[1]
        r1 = cross[cross["Entity"] == c1]
        r2 = cross[cross["Entity"] == c2]
        g1 = r1["value_gap"].iloc[0] if len(r1) else np.nan
        l1 = r1["life_exp"].iloc[0] if len(r1) else np.nan
        l2 = r2["life_exp"].iloc[0] if len(r2) else np.nan
        k[0].metric(f"{c1} · spend/person",
                    money(r1["health_pc"].iloc[0] if len(r1) else np.nan))
        k[1].metric(f"{c2} · spend/person",
                    money(r2["health_pc"].iloc[0] if len(r2) else np.nan))
        k[2].metric(f"{c1} · value for money",
                    "—" if pd.isna(g1) else f"{g1:+.1f} yrs",
                    help="Years lived above/below what its spending predicts.")
        k[3].metric(f"Life-expectancy gap ({c1}−{c2})",
                    "—" if pd.isna(l1) or pd.isna(l2) else f"{l1 - l2:+.1f} yrs")
    else:
        k[0].info("Pick two highlight countries in the sidebar.")

    st.divider()

    # ---- 1: the curve, coloured by access
    st.markdown("#### 1 · More money, more life — up to a point")
    st.caption("Every country in the selected year. Colour is health-service "
               "access (UHC). Life expectancy climbs steeply where spending is "
               "buying access, then flattens once access is near-universal.")
    c = cross.dropna(subset=["health_pc", "life_exp"]).copy()
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=c["health_pc"], y=c["life_exp"], mode="markers",
        marker=dict(size=8, color=c["uhc"], colorscale="RdYlBu", cmin=40, cmax=90,
                    showscale=True, colorbar=dict(title="Access<br>(UHC)", thickness=12),
                    line=dict(width=0.5, color="white")),
        text=c["Entity"],
        hovertemplate="<b>%{text}</b><br>Spend $%{x:,.0f}<br>"
                      "Life %{y:.1f}y<extra></extra>"))
    xs, ys = log_fit(c["health_pc"].to_numpy(), c["life_exp"].to_numpy())
    if xs is not None:
        fig1.add_trace(go.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip",
                                  line=dict(color=TREND, dash="dash", width=2),
                                  showlegend=False))
    fig1.add_trace(hl_layer(c, "health_pc", "life_exp"))
    fig1.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10),
                       xaxis_type="log", xaxis_title="Health spending per person (PPP $, log)",
                       yaxis_title="Life expectancy (years)")
    st.plotly_chart(fig1, use_container_width=True)

    cc = st.columns(2)
    # ---- 2: spending over time
    with cc[0]:
        st.markdown("#### 2 · The relentless rise")
        st.caption("Spending per person over time for the highlighted countries.")
        tr = df[df["Entity"].isin(highlights)].dropna(subset=["health_pc"])
        fig2 = go.Figure()
        for ent in highlights:
            g = tr[tr["Entity"] == ent]
            if len(g):
                fig2.add_trace(go.Scatter(x=g["Year"], y=g["health_pc"],
                               mode="lines", name=ent,
                               line=dict(color=cmap[ent], width=2)))
        fig2.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                           yaxis_title="Spend/person (PPP $)",
                           legend=dict(orientation="h", y=1.02, x=0))
        st.plotly_chart(fig2, use_container_width=True)

    # ---- 3: rich-country club, coloured by obesity
    with cc[1]:
        st.markdown("#### 3 · Inside the rich-country club")
        st.caption("Spending ≥ $4k, where access is universal. More money no "
                   "longer buys life — and heavier countries (darker) lag.")
        rich = c[c["health_pc"] >= data.RICH_THRESHOLD].dropna(subset=["obesity"])
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=rich["health_pc"], y=rich["life_exp"], mode="markers",
            marker=dict(size=10, color=rich["obesity"], colorscale="YlOrRd",
                        cmin=5, cmax=40, showscale=True,
                        colorbar=dict(title="Obesity<br>%", thickness=12),
                        line=dict(width=0.5, color="white")),
            text=rich["Entity"],
            hovertemplate="<b>%{text}</b><br>Spend $%{x:,.0f}<br>"
                          "Life %{y:.1f}y<br>Obesity %{marker.color:.0f}%<extra></extra>"))
        fig3.add_trace(hl_layer(rich, "health_pc", "life_exp"))
        fig3.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                           xaxis_title="Health spending per person (PPP $)",
                           yaxis_title="Life expectancy (years)")
        st.plotly_chart(fig3, use_container_width=True)

    # ---- 4: value for money
    st.markdown("#### 4 · Value for money")
    st.caption("Years of life lived above (green) or below (red) what each "
               "country's spending predicts. The big spenders sink to the bottom.")
    eff = c[c["health_pc"] >= data.RICH_THRESHOLD].dropna(subset=["value_gap"])
    eff = eff.sort_values("value_gap")
    if len(eff):
        colors = ["#C0504D" if v < 0 else "#4F9D69" for v in eff["value_gap"]]
        fig4 = go.Figure(go.Bar(
            x=eff["value_gap"], y=eff["Entity"], orientation="h",
            marker_color=colors,
            hovertemplate="<b>%{y}</b><br>%{x:+.1f} yrs vs predicted<extra></extra>"))
        fig4.update_layout(height=max(320, 17 * len(eff)),
                           margin=dict(l=10, r=10, t=10, b=10),
                           xaxis_title="Years lived vs. spending prediction")
        st.plotly_chart(fig4, use_container_width=True)

    st.divider()
    st.caption(
        "Sources: Our World in Data — health spending per capita (WHO/World "
        "Bank), life expectancy (UN WPP), UHC service coverage index (WHO), "
        "adult obesity (WHO). Relationships are correlational; cross-country "
        "differences also reflect inequality, diet, demographics, and other "
        "factors beyond the health system.")


if __name__ == "__main__":
    main()
