"""
Measles & Immunization Burden Dashboard
MSBA382 Healthcare Analytics - Individual Project

A consultant tool for understanding the global measles burden and its
relationship to vaccination coverage. The recurring reference line at
80% (outbreak floor) and 95% (herd-immunity threshold) is the analytical
spine of every view.
"""

import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score,
    recall_score, roc_auc_score,
)

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
DATA_PATH = os.path.join(os.path.dirname(__file__), "measles_master.csv")

FLOOR = 80      # below this, outbreaks take off
HERD = 95       # WHO herd-immunity target for measles
OUTBREAK_CUTOFF = 10  # cases per million flagged as a "notable outbreak"

# WHO Eastern Mediterranean Region (Lebanon's region) - 22 member states
EMR = {"AFG", "BHR", "DJI", "EGY", "IRN", "IRQ", "JOR", "KWT", "LBN", "LBY",
       "MAR", "OMN", "PAK", "PSE", "QAT", "SAU", "SOM", "SDN", "SYR", "TUN",
       "ARE", "YEM"}

RED = "#C0392B"      # measles / danger
TEAL = "#1D9E75"     # protected
INK = "#262626"
MUTED = "#8A8A82"

# ----------------------------------------------------------------------------
# Data + model logic (pure functions, testable without Streamlit)
# ----------------------------------------------------------------------------
def _load_data(path):
    df = pd.read_csv(path)
    df["continent"] = df["continent"].fillna("Other")
    df["who_emr"] = df["Code"].isin(EMR)
    return df


def weighted_coverage(frame, col="mcv1"):
    """Population-weighted mean coverage over rows with both values."""
    f = frame.dropna(subset=[col, "population"])
    if f["population"].sum() == 0:
        return np.nan
    return np.average(f[col], weights=f["population"])


def aggregate_series(df, scope):
    """Return a yearly series (cases, incidence, weighted MCV1) for a scope."""
    if scope == "World":
        sub = df
    elif scope == "Eastern Mediterranean (WHO)":
        sub = df[df["who_emr"]]
    else:
        sub = df[df["continent"] == scope]
    rows = []
    for yr, g in sub.groupby("Year"):
        cases = g["measles_cases"].sum(min_count=1)
        pop = g.dropna(subset=["measles_cases"])["population"].sum()
        rows.append({
            "Year": yr,
            "cases": cases,
            "incidence_per_m": (cases / pop * 1e6) if pop and not np.isnan(cases) else np.nan,
            "mcv1": weighted_coverage(g),
        })
    return pd.DataFrame(rows).sort_values("Year")


def train_outbreak_model(df, cutoff=OUTBREAK_CUTOFF, year_from=2010):
    """Logistic regression: predict 'notable outbreak' from coverage."""
    d = df[(df["Year"] >= year_from)].dropna(
        subset=["mcv1", "dtp3", "pol3", "incidence_per_m"]).copy()
    d["outbreak"] = (d["incidence_per_m"] > cutoff).astype(int)
    X = d[["mcv1", "dtp3", "pol3"]]
    y = d["outbreak"]
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced"))
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    proba = model.predict_proba(Xte)[:, 1]
    metrics = {
        "accuracy": accuracy_score(yte, pred),
        "precision": precision_score(yte, pred, zero_division=0),
        "recall": recall_score(yte, pred, zero_division=0),
        "roc_auc": roc_auc_score(yte, proba),
        "n_train": len(Xtr),
        "n_test": len(Xte),
        "outbreak_rate": y.mean(),
        "cm": confusion_matrix(yte, pred),
    }
    return model, metrics


# ----------------------------------------------------------------------------
# Streamlit-cached wrappers
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    return _load_data(DATA_PATH)


@st.cache_resource
def get_model(cutoff, year_from):
    return train_outbreak_model(load_data(), cutoff, year_from)


# ----------------------------------------------------------------------------
# Password gate (configurable via Streamlit secrets)
# ----------------------------------------------------------------------------
def get_password():
    try:
        return st.secrets["app_password"]
    except Exception:
        return "measles2026"


def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        "<div style='max-width:430px;margin:8vh auto 0;text-align:center;'>"
        "<h1 style='margin-bottom:.2rem;'>Measles Burden Explorer</h1>"
        "<p style='color:#8A8A82;'>Global immunization coverage vs. disease burden, "
        "2000\u20132024. Enter the access password to continue.</p></div>",
        unsafe_allow_html=True,
    )
    c = st.columns([1, 2, 1])[1]
    with c:
        pw = st.text_input("Password", type="password", label_visibility="collapsed",
                           placeholder="Password")
        if st.button("Enter dashboard", use_container_width=True):
            if pw == get_password():
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password. Try again.")
        st.caption("Consultant deliverable \u00b7 MSBA382 Healthcare Analytics")
    return False


# ----------------------------------------------------------------------------
# Reference-line helper (the signature element)
# ----------------------------------------------------------------------------
def add_thresholds(fig, axis="y"):
    for val, lab, col in [(FLOOR, "80% outbreak floor", MUTED),
                          (HERD, "95% herd immunity", RED)]:
        if axis == "y":
            fig.add_hline(y=val, line_dash="dash", line_color=col,
                          annotation_text=lab, annotation_position="right",
                          annotation_font_size=11)
        else:
            fig.add_vline(x=val, line_dash="dash", line_color=col,
                          annotation_text=lab, annotation_font_size=11)
    return fig


# ============================================================================
# SECTIONS
# ============================================================================
def section_overview(df):
    st.header("Overview")
    st.markdown(
        "Measles is the most contagious vaccine-preventable disease. This tool "
        "tests one thesis against the data: **measles resurges wherever first-dose "
        "(MCV1) coverage slips below the ~95% needed for herd immunity \u2014 and "
        "the danger turns sharply once a country falls under ~80%.**")

    latest = int(df.dropna(subset=["measles_cases"])["Year"].max())
    cur = df[df["Year"] == latest]
    global_cases = int(cur["measles_cases"].sum())
    global_mcv1 = weighted_coverage(cur)
    below_floor = cur.dropna(subset=["mcv1"])
    n_below = int((below_floor["mcv1"] < FLOOR).sum())

    a, b, c, d = st.columns(4)
    a.metric(f"Reported cases ({latest})", f"{global_cases:,}")
    b.metric(f"Global MCV1 coverage ({latest})", f"{global_mcv1:.0f}%")
    c.metric("Countries below 80% floor", f"{n_below}")
    d.metric("Herd-immunity target", f"{HERD}%")

    st.subheader("The threshold effect")
    st.caption("Median measles incidence per million, by MCV1 coverage band "
               f"({latest if latest in df.Year.values else 2023}).")
    yr = 2023 if 2023 in df["Year"].values else latest
    snap = df[df["Year"] == yr].dropna(subset=["mcv1", "incidence_per_m"])
    bands = pd.cut(snap["mcv1"], [0, FLOOR, HERD, 1000], right=False,
                   labels=["< 80%", "80\u201394%", "\u2265 95%"])
    med = snap.groupby(bands, observed=True)["incidence_per_m"].median().reindex(
        ["< 80%", "80\u201394%", "\u2265 95%"])
    fig = px.bar(x=med.index, y=med.values,
                 labels={"x": "MCV1 coverage band", "y": "median cases per million"},
                 color=med.index,
                 color_discrete_map={"< 80%": RED, "80\u201394%": TEAL, "\u2265 95%": TEAL})
    fig.update_layout(showlegend=False, height=360, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"Countries below 80% coverage carry roughly **{med['< 80%']/max(med['80\u201394%'],0.1):.0f}\u00d7** "
            "the median incidence of better-covered countries \u2014 a cliff, not a slope.")


def section_trends(df, scope):
    st.header("Trends over time")
    st.caption(f"Scope: {scope}. Reported cases against population-weighted MCV1 coverage.")
    s = aggregate_series(df, scope)
    s = s[s["Year"] >= 2000]

    fig = go.Figure()
    fig.add_bar(x=s["Year"], y=s["cases"], name="Reported cases",
                marker_color=RED, opacity=0.55, yaxis="y1")
    fig.add_trace(go.Scatter(x=s["Year"], y=s["mcv1"], name="MCV1 coverage (%)",
                             line=dict(color=TEAL, width=3), yaxis="y2"))
    fig.add_hline(y=HERD, line_dash="dash", line_color=RED, yref="y2",
                  annotation_text="95% target", annotation_font_size=11)
    fig.update_layout(
        height=440, margin=dict(t=20),
        yaxis=dict(title="reported cases"),
        yaxis2=dict(title="MCV1 coverage (%)", overlaying="y", side="right",
                    range=[0, 100]),
        legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "Coverage climbed for two decades and cases fell with it \u2014 then "
        "pandemic-era disruption stalled coverage and cases rebounded.")


def section_threshold(df, year):
    st.header("The coverage\u2013incidence relationship")
    snap = df[df["Year"] == year].dropna(subset=["mcv1", "incidence_per_m"])
    st.caption(f"Each point is a country in {year} (n = {len(snap)}). "
               "Incidence on a log scale to show the full range.")
    plot = snap.copy()
    plot["incidence_plot"] = plot["incidence_per_m"].clip(lower=0.1)
    fig = px.scatter(plot, x="mcv1", y="incidence_plot",
                     hover_name="Entity", color="continent",
                     log_y=True, size="population", size_max=40,
                     labels={"mcv1": "MCV1 coverage (%)",
                             "incidence_plot": "cases per million (log)"})
    add_thresholds(fig, axis="x")
    fig.update_layout(height=480, margin=dict(t=20),
                      legend=dict(orientation="h", y=1.12, title=""))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        "The cloud of high-incidence countries sits almost entirely to the left "
        "of the 80% line. Push a country past that floor and its outbreak risk "
        "collapses toward the baseline.")


def section_map(df, year, metric):
    st.header("Geographic distribution")
    snap = df[df["Year"] == year].copy()
    if metric == "MCV1 coverage (%)":
        col, scale, rng = "mcv1", "RdYlGn", (40, 100)
        st.caption(f"First-dose measles coverage by country, {year}. "
                   "Red marks the immunity gaps where outbreaks incubate.")
    else:
        col, scale, rng = "incidence_per_m", "Reds", (0, 200)
        st.caption(f"Reported measles cases per million people, {year}.")
    snap = snap.dropna(subset=[col])
    fig = px.choropleth(snap, locations="Code", color=col,
                        hover_name="Entity", color_continuous_scale=scale,
                        range_color=rng, labels={col: metric})
    fig.update_layout(height=480, margin=dict(t=10, b=0, l=0, r=0),
                      geo=dict(showframe=False, projection_type="natural earth"))
    st.plotly_chart(fig, use_container_width=True)


def section_country(df):
    st.header("Country deep-dive")
    names = sorted(df["Entity"].unique())
    default = names.index("Lebanon") if "Lebanon" in names else 0
    name = st.selectbox("Select a country", names, index=default)
    cd = df[df["Entity"] == name].sort_values("Year")
    cd = cd[cd["Year"] >= 2000]

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**MCV1 coverage vs. regional and world average**")
        world = aggregate_series(df, "World")
        emr = aggregate_series(df, "Eastern Mediterranean (WHO)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cd["Year"], y=cd["mcv1"], name=name,
                                 line=dict(color=RED, width=3)))
        fig.add_trace(go.Scatter(x=world["Year"], y=world["mcv1"], name="World",
                                 line=dict(color=MUTED, dash="dot")))
        fig.add_trace(go.Scatter(x=emr["Year"], y=emr["mcv1"],
                                 name="E. Mediterranean", line=dict(color=TEAL, dash="dash")))
        fig.add_hline(y=HERD, line_dash="dash", line_color=RED)
        fig.update_layout(height=360, yaxis=dict(range=[0, 100], title="MCV1 (%)"),
                          margin=dict(t=10), legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**Reported measles cases**")
        fig2 = px.bar(cd, x="Year", y="measles_cases")
        fig2.update_traces(marker_color=RED)
        fig2.update_layout(height=360, margin=dict(t=10),
                           yaxis_title="reported cases")
        st.plotly_chart(fig2, use_container_width=True)


def section_program(df, scope):
    st.header("Is measles falling behind the wider program?")
    st.caption(f"Scope: {scope}. Population-weighted coverage for measles (MCV1) "
               "against two backbone childhood vaccines.")
    if scope == "World":
        sub = df
    elif scope == "Eastern Mediterranean (WHO)":
        sub = df[df["who_emr"]]
    else:
        sub = df[df["continent"] == scope]
    rows = []
    for yr, g in sub.groupby("Year"):
        rows.append({"Year": yr,
                     "Measles (MCV1)": weighted_coverage(g, "mcv1"),
                     "DTP3": weighted_coverage(g, "dtp3"),
                     "Polio (Pol3)": weighted_coverage(g, "pol3")})
    series = pd.DataFrame(rows).query("Year >= 2000")
    long = series.melt("Year", var_name="Vaccine", value_name="Coverage")
    fig = px.line(long, x="Year", y="Coverage", color="Vaccine",
                  color_discrete_map={"Measles (MCV1)": RED, "DTP3": TEAL,
                                      "Polio (Pol3)": MUTED})
    fig.add_hline(y=HERD, line_dash="dash", line_color=RED,
                  annotation_text="95%", annotation_font_size=11)
    fig.update_layout(height=440, yaxis=dict(range=[0, 100], title="coverage (%)"),
                      margin=dict(t=20), legend=dict(orientation="h", y=1.12, title=""))
    st.plotly_chart(fig, use_container_width=True)


def section_predict(df):
    st.header("Predicting outbreak risk")
    st.markdown(
        "A logistic-regression classifier flags a country-year as a **notable "
        f"outbreak** (more than {OUTBREAK_CUTOFF} reported cases per million) from "
        "its vaccination coverage alone. This is an illustrative model, not a "
        "clinical forecast.")
    model, m = get_model(OUTBREAK_CUTOFF, 2010)

    a, b, c, d = st.columns(4)
    a.metric("Accuracy", f"{m['accuracy']*100:.0f}%")
    b.metric("Recall (catches outbreaks)", f"{m['recall']*100:.0f}%")
    c.metric("Precision", f"{m['precision']*100:.0f}%")
    d.metric("ROC-AUC", f"{m['roc_auc']:.2f}")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Confusion matrix (test set)**")
        cm = m["cm"]
        fig = px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                        labels=dict(x="Predicted", y="Actual"),
                        x=["No outbreak", "Outbreak"], y=["No outbreak", "Outbreak"])
        fig.update_layout(height=340, margin=dict(t=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**Try it: outbreak probability at a coverage level**")
        mcv1 = st.slider("MCV1 coverage (%)", 30, 100, 75)
        dtp3 = st.slider("DTP3 coverage (%)", 30, 100, 80)
        pol3 = st.slider("Polio coverage (%)", 30, 100, 80)
        x_in = pd.DataFrame([[mcv1, dtp3, pol3]], columns=["mcv1", "dtp3", "pol3"])
        p = model.predict_proba(x_in)[0, 1]
        st.metric("Estimated outbreak probability", f"{p*100:.0f}%")
        st.progress(float(p))
        st.caption("Tuned for sensitivity (to catch outbreaks), so it errs "
                   "toward flagging risk. Coverage is necessary but not the "
                   "only driver \u2014 imported cases and sub-national gaps matter too.")


def section_about():
    st.header("Data & methodology")
    st.markdown(f"""
**Sources**
- Reported measles cases \u2014 Our World in Data, from the WHO Global Health Observatory.
- MCV1 / DTP3 / Polio coverage \u2014 Our World in Data, from WHO/UNICEF national estimates (WUENIC).
- Population \u2014 World Bank, via the Datahub population dataset.

**Build**
- The three sources were joined on ISO-3 country code and year into one master table (194 countries, 1980\u20132024). Population matched 97.9% of country-years.
- Incidence is computed as reported cases \u00f7 population \u00d7 1,000,000.
- Regional aggregates use population-weighted coverage and summed cases.
- Reference lines: {FLOOR}% (outbreak floor) and {HERD}% (WHO herd-immunity target).

**Limitations**
- Reported cases undercount true infection (surveillance varies by country and year); per-capita normalization reduces but does not remove this bias.
- Coverage figures are national averages and hide sub-national pockets of low immunity where outbreaks often begin.
- The prediction model is a teaching illustration trained on observational data \u2014 it shows association, not causation.
""")


# ============================================================================
# APP
# ============================================================================
def main():
    st.set_page_config(page_title="Measles Burden Explorer",
                       page_icon="\U0001FA7A", layout="wide")
    if not check_password():
        return

    df = load_data()
    years = sorted(df["Year"].unique())
    regions = ["World", "Eastern Mediterranean (WHO)"] + \
        sorted(df["continent"].unique().tolist())

    st.sidebar.title("Measles Burden Explorer")
    page = st.sidebar.radio("View", [
        "Overview", "Trends", "Coverage vs. incidence", "Map",
        "Country deep-dive", "Program comparison", "Outbreak prediction",
        "Data & methodology"])
    st.sidebar.markdown("---")

    if page == "Overview":
        section_overview(df)
    elif page == "Trends":
        scope = st.sidebar.selectbox("Region", regions)
        section_trends(df, scope)
    elif page == "Coverage vs. incidence":
        yr = st.sidebar.select_slider("Year", years, value=2023 if 2023 in years else years[-1])
        section_threshold(df, yr)
    elif page == "Map":
        yr = st.sidebar.select_slider("Year", years, value=2023 if 2023 in years else years[-1])
        metric = st.sidebar.radio("Show", ["MCV1 coverage (%)", "Incidence per million"])
        section_map(df, yr, metric)
    elif page == "Country deep-dive":
        section_country(df)
    elif page == "Program comparison":
        scope = st.sidebar.selectbox("Region", regions)
        section_program(df, scope)
    elif page == "Outbreak prediction":
        section_predict(df)
    else:
        section_about()

    st.sidebar.caption("MSBA382 Healthcare Analytics \u00b7 consultant deliverable")


if __name__ == "__main__":
    main()
