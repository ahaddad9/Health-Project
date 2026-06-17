"""
Moving Less, Weighing More — Physical inactivity and obesity
MSBA382 Healthcare Analytics | Consultant dashboard
"""
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

DATA = os.path.join(os.path.dirname(__file__), "mobility_master.csv")
CORAL = "#D85A30"
TEAL = "#1D9E75"
MUTED = "#8A8A82"
BANDS = ["Q1 (most active)", "Q2", "Q3", "Q4 (most inactive)"]
REGIONS = ["Africa", "Americas", "Eastern Mediterranean", "Europe",
           "South-East Asia", "Western Pacific"]


@st.cache_data
def load():
    return pd.read_csv(DATA)


def quartile_medians(df, year, col):
    s = df[df["Year"] == year].dropna(subset=["inactivity", col]).copy()
    s["band"] = pd.qcut(s["inactivity"], 4, labels=BANDS)
    return s.groupby("band", observed=True)[col].median()


def yearly_median(df, scope, cols):
    sub = df if scope == "World" else df[df["who_region"] == scope]
    return sub[sub["Year"] >= 2000].groupby("Year")[cols].median().reset_index()


def insights(bullets):
    st.markdown("**Key insights**")
    st.markdown("\n".join(f"- {b}" for b in bullets))


# ---------------------------------------------------------------- password
def password():
    try:
        secret = st.secrets["app_password"]
    except Exception:
        secret = "move2026"
    if st.session_state.get("ok"):
        return True
    st.markdown("<div style='max-width:430px;margin:8vh auto 0;text-align:center;'>"
                "<h1>Moving Less, Weighing More</h1>"
                "<p style='color:#8A8A82;'>Physical inactivity and obesity across "
                "the world. Enter the password to continue.</p></div>",
                unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        pw = st.text_input("Password", type="password", label_visibility="collapsed",
                           placeholder="Password")
        if st.button("Enter dashboard", use_container_width=True):
            if pw == secret:
                st.session_state["ok"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.caption("MSBA382 Healthcare Analytics \u00b7 consultant deliverable")
    return False


# ---------------------------------------------------------------- sections
def overview(df):
    st.title("Moving less, weighing more")
    st.markdown("**As adults move less, obesity rises \u2014 and obesity is a gateway "
                "to heart disease, type 2 diabetes, and other serious conditions.** "
                "This tool pairs physical inactivity with adult obesity across roughly "
                "190 countries, using WHO data.")
    ob = quartile_medians(df, 2022, "obesity")
    a, b, c = st.columns(3)
    a.metric("Countries analysed", df["Code"].nunique())
    b.metric("Obesity \u2014 most active countries", f"{ob.iloc[0]:.0f}%")
    c.metric("Obesity \u2014 most inactive countries", f"{ob.iloc[-1]:.0f}%",
             delta=f"{ob.iloc[-1]-ob.iloc[0]:.0f} pts higher", delta_color="inverse")

    st.subheader("Obesity rises with inactivity")
    st.caption("Countries grouped into four bands by adult inactivity; bars show "
               "median obesity in each band (2022).")
    fig = go.Figure(go.Bar(x=BANDS, y=ob.values, marker_color=CORAL,
                           text=[f"{v:.1f}%" for v in ob.values], textposition="outside"))
    fig.update_layout(height=400, yaxis_title="median obesity (%)", margin=dict(t=20),
                      showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    insights([
        f"Obesity in the most-inactive countries (~{ob.iloc[-1]:.0f}%) is more than "
        f"double that of the most-active (~{ob.iloc[0]:.0f}%).",
        "The pattern holds across ~190 countries \u2014 a clear, if moderate, association.",
        "Obesity is itself a leading risk factor for heart disease, type 2 diabetes and several cancers.",
    ])


def world_map(df, year, metric):
    st.title("Where the burden sits")
    col = "inactivity" if metric.startswith("Physical") else "obesity"
    scale = "OrRd"
    rng = (0, 65) if col == "inactivity" else (0, 70)
    snap = df[df["Year"] == year].dropna(subset=[col])
    st.caption(f"{metric}, {year}. Darker = higher.")
    fig = px.choropleth(snap, locations="Code", color=col, hover_name="Entity",
                        color_continuous_scale=scale, range_color=rng,
                        labels={col: metric})
    fig.update_layout(height=470, margin=dict(t=10, b=0, l=0, r=0),
                      geo=dict(showframe=False, projection_type="natural earth"))
    st.plotly_chart(fig, use_container_width=True)
    insights([
        "Inactivity peaks in the Gulf (UAE ~66%, Kuwait ~63%), Cuba, Lebanon and South Korea.",
        "It is lowest across much of sub-Saharan Africa (Malawi, Tanzania, Uganda below 6%).",
        "Obesity peaks in the Pacific islands \u2014 Tonga, the Cook Islands and Nauru exceed 70%.",
    ])


def relationship(df, year):
    st.title("Inactivity vs. obesity")
    snap = df[df["Year"] == year].dropna(subset=["inactivity", "obesity"])
    st.caption(f"Each point is a country in {year} (n = {len(snap)}).")
    fig = px.scatter(snap, x="inactivity", y="obesity", hover_name="Entity",
                     color="who_region", trendline="ols",
                     trendline_scope="overall", trendline_color_override=MUTED,
                     labels={"inactivity": "adults insufficiently active (%)",
                             "obesity": "adults obese (%)", "who_region": "WHO region"})
    leb = snap[snap["Code"] == "LBN"]
    if len(leb):
        fig.add_trace(go.Scatter(x=leb["inactivity"], y=leb["obesity"], mode="markers+text",
                      text=["Lebanon"], textposition="top center", marker=dict(size=14, color="black"),
                      showlegend=False))
    fig.update_layout(height=480, margin=dict(t=10), legend=dict(orientation="h", y=1.12, title=""))
    st.plotly_chart(fig, use_container_width=True)
    insights([
        "More inactivity tends to mean more obesity (rank correlation \u2248 0.5).",
        "Exceptions prove it is not a law: Japan and South Korea are very inactive yet lean (diet); Pacific islands are extremely obese.",
        "Lebanon sits high on both axes \u2014 among the most inactive, with ~30% obesity.",
    ])


def trends(df, scope):
    st.title("Trends over time")
    s = yearly_median(df, scope, ["inactivity", "obesity"])
    st.caption(f"Median across countries \u2014 {scope}, 2000\u20132022.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["Year"], y=s["inactivity"], name="Inactivity",
                  line=dict(color=TEAL, width=3)))
    fig.add_trace(go.Scatter(x=s["Year"], y=s["obesity"], name="Obesity",
                  line=dict(color=CORAL, width=3)))
    fig.update_layout(height=440, yaxis_title="% of adults", margin=dict(t=20),
                      legend=dict(orientation="h", y=1.12, title=""))
    st.plotly_chart(fig, use_container_width=True)
    insights([
        "Obesity has climbed steadily since 2000 (median ~14% \u2192 ~22%).",
        "Inactivity stays persistently high (~25% of adults) and is not improving.",
        "Both trends point the same way: populations are getting heavier and less active.",
    ])


def by_sex(df, scope):
    st.title("Women vs. men")
    s = yearly_median(df, scope, ["inactivity_female", "inactivity_male"])
    st.caption(f"Median inactivity by sex \u2014 {scope}, 2000\u20132022.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["Year"], y=s["inactivity_female"], name="Women",
                  line=dict(color=CORAL, width=3)))
    fig.add_trace(go.Scatter(x=s["Year"], y=s["inactivity_male"], name="Men",
                  line=dict(color=TEAL, width=3)))
    fig.update_layout(height=440, yaxis_title="adults insufficiently active (%)",
                      margin=dict(t=20), legend=dict(orientation="h", y=1.12, title=""))
    st.plotly_chart(fig, use_container_width=True)
    insights([
        "Women are consistently more inactive than men (~31% vs ~24% of adults in 2022).",
        "The gap shows up in almost every region and has not closed over time.",
        "Activity programmes should pay particular attention to reaching women.",
    ])


def country_focus(df):
    st.title("Country focus")
    names = sorted(df["Entity"].unique())
    name = st.selectbox("Country", names,
                        index=names.index("Lebanon") if "Lebanon" in names else 0)
    cd = df[df["Entity"] == name].sort_values("Year")
    region = cd["who_region"].dropna().iloc[0] if cd["who_region"].notna().any() else "World"
    latest = cd[cd["Year"] == 2022]
    a, b = st.columns(2)
    if len(latest):
        a.metric("Adults inactive (2022)", f"{latest['inactivity'].iloc[0]:.0f}%")
        b.metric("Adults obese (2022)", f"{latest['obesity'].iloc[0]:.0f}%")
    st.caption(f"Inactivity: {name} vs. its region ({region}) and the world median.")
    world = yearly_median(df, "World", ["inactivity"])
    reg = yearly_median(df, region, ["inactivity"])
    cdy = cd[cd["Year"] >= 2000]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cdy["Year"], y=cdy["inactivity"], name=name,
                  line=dict(color=CORAL, width=3)))
    fig.add_trace(go.Scatter(x=reg["Year"], y=reg["inactivity"], name=region,
                  line=dict(color=TEAL, dash="dash")))
    fig.add_trace(go.Scatter(x=world["Year"], y=world["inactivity"], name="World",
                  line=dict(color=MUTED, dash="dot")))
    fig.update_layout(height=420, yaxis_title="adults inactive (%)", margin=dict(t=20),
                      legend=dict(orientation="h", y=1.12, title=""))
    st.plotly_chart(fig, use_container_width=True)
    insights([
        "The Eastern Mediterranean is the most inactive WHO region (~39% of adults).",
        "Lebanon is among the most inactive countries worldwide (~59%), with ~30% obesity.",
        "That combination signals elevated downstream risk of heart disease and diabetes locally.",
    ])


def conclusions():
    st.title("Conclusions & recommendations")
    st.markdown("**What the data says**")
    st.markdown(
        "- Across countries, less physical activity goes hand-in-hand with higher obesity.\n"
        "- Obesity is a gateway to heart disease, type 2 diabetes and other costly conditions.\n"
        "- The burden is uneven: women and the Eastern Mediterranean region are hit hardest.\n"
        "- The relationship is an association, not a guarantee \u2014 diet and wealth also matter.")
    st.markdown("**Recommendations for a health centre**")
    st.markdown(
        "- Prioritise physical-activity promotion, especially programmes that reach women.\n"
        "- Target high-inactivity settings \u2014 in this region, that is much of the population.\n"
        "- Treat inactivity as an early lever: raising activity lowers obesity and the diseases that follow.\n"
        "- Screen inactive, higher-BMI patients for cardiovascular and diabetes risk.")


def about():
    st.title("Data & methodology")
    st.markdown(
        "**Sources**\n"
        "- Physical inactivity \u2014 WHO Global Health Observatory (insufficient activity among adults 18+, age-standardised).\n"
        "- Obesity \u2014 WHO Global Health Observatory (BMI \u2265 30, adults 18+, age-standardised).\n\n"
        "**Build**\n"
        "- The two indicators were joined on ISO-3 country code and year (~190 countries, 2000\u20132022).\n"
        "- The WHO file also supplies sex breakdown and WHO region, used directly.\n\n"
        "**Limitations**\n"
        "- Country-level (ecological) data shows association, not individual causation.\n"
        "- Inactivity is self-reported; national figures hide differences within countries.\n"
        "- Obesity is a risk factor for the downstream diseases discussed, which are not charted here.")


# ---------------------------------------------------------------- app
def main():
    st.set_page_config(page_title="Moving Less, Weighing More", layout="wide")
    if not password():
        return
    df = load()
    st.sidebar.title("Moving Less, Weighing More")
    page = st.sidebar.radio("View", ["Overview", "Map", "Inactivity vs. obesity",
                            "Trends", "Women vs. men", "Country focus",
                            "Conclusions", "Data & methodology"])
    st.sidebar.markdown("---")

    if page == "Overview":
        overview(df)
    elif page == "Map":
        metric = st.sidebar.radio("Show", ["Physical inactivity", "Obesity"])
        year = st.sidebar.slider("Year", 2000, 2022, 2022)
        world_map(df, year, metric)
    elif page == "Inactivity vs. obesity":
        year = st.sidebar.slider("Year", 2000, 2022, 2022)
        relationship(df, year)
    elif page == "Trends":
        scope = st.sidebar.selectbox("Region", ["World"] + REGIONS)
        trends(df, scope)
    elif page == "Women vs. men":
        scope = st.sidebar.selectbox("Region", ["World"] + REGIONS)
        by_sex(df, scope)
    elif page == "Country focus":
        country_focus(df)
    elif page == "Conclusions":
        conclusions()
    else:
        about()
    st.sidebar.caption("MSBA382 \u00b7 WHO data \u00b7 consultant deliverable")


if __name__ == "__main__":
    main()
