"""
Moving Less, Weighing More — physical inactivity & obesity
MSBA382 Healthcare Analytics | consultant dashboard
Two views: a one-page descriptive Overview, and a simple linear Predict tab.
"""
import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

DATA = os.path.join(os.path.dirname(__file__), "mobility_master.csv")
CORAL, TEAL, MUTED, INK = "#D85A30", "#1D9E75", "#8A8A82", "#262626"
REGIONS = ["Africa", "Americas", "Eastern Mediterranean", "Europe",
           "South-East Asia", "Western Pacific"]
YEAR = 2022


@st.cache_data
def load():
    return pd.read_csv(DATA)


@st.cache_data
def fit(df):
    d = df[df["Year"] == YEAR].dropna(subset=["inactivity", "obesity"]).copy()
    b, a = np.polyfit(d["inactivity"], d["obesity"], 1)
    pred = a + b * d["inactivity"]
    r2 = 1 - ((d["obesity"] - pred) ** 2).sum() / ((d["obesity"] - d["obesity"].mean()) ** 2).sum()
    d["rank"] = d["inactivity"].rank(ascending=False).astype(int)
    return float(a), float(b), float(r2), d


def quartile_medians(df):
    s = df[df["Year"] == YEAR].dropna(subset=["inactivity", "obesity"]).copy()
    s["band"] = pd.qcut(s["inactivity"], 4, labels=["a", "b", "c", "d"])
    m = s.groupby("band", observed=True)["obesity"].median()
    return m.iloc[0], m.iloc[-1]


def password():
    try:
        secret = st.secrets["app_password"]
    except Exception:
        secret = "move2026"
    if st.session_state.get("ok"):
        return True
    st.markdown("<div style='max-width:430px;margin:8vh auto 0;text-align:center;'>"
                "<h1>Moving Less, Weighing More</h1>"
                "<p style='color:#8A8A82;'>Physical inactivity and obesity across the "
                "world. Enter the password to continue.</p></div>", unsafe_allow_html=True)
    c = st.columns([1, 2, 1])[1]
    with c:
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


def scatter(d, a, b, show_lebanon=True):
    fig = px.scatter(d, x="inactivity", y="obesity", hover_name="Entity",
                     color="who_region",
                     labels={"inactivity": "adults insufficiently active (%)",
                             "obesity": "adults obese (%)", "who_region": ""})
    xs = np.array([d["inactivity"].min(), d["inactivity"].max()])
    fig.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines",
                  line=dict(color=INK, width=2, dash="dash"), name="trend", showlegend=False))
    if show_lebanon and (d["Code"] == "LBN").any():
        leb = d[d["Code"] == "LBN"]
        fig.add_trace(go.Scatter(x=leb["inactivity"], y=leb["obesity"], mode="markers+text",
                      text=["Lebanon"], textposition="top center",
                      marker=dict(size=13, color="black"), showlegend=False))
    fig.update_layout(height=430, margin=dict(t=30, b=0, l=0, r=0),
                      legend=dict(orientation="h", y=1.15, font=dict(size=11)))
    return fig


def ranked_bars(d):
    top = d.nlargest(12, "inactivity").sort_values("inactivity")
    fig = go.Figure()
    fig.add_bar(y=top["Entity"], x=top["inactivity"], orientation="h",
                name="Inactivity", marker_color=TEAL)
    fig.add_bar(y=top["Entity"], x=top["obesity"], orientation="h",
                name="Obesity", marker_color=CORAL)
    fig.update_layout(barmode="group", height=460, margin=dict(t=30, l=0, r=0),
                      xaxis_title="% of adults",
                      legend=dict(orientation="h", y=1.06, title=""))
    return fig


def world_map(df, metric):
    col = "inactivity" if metric.startswith("Inactivity") else "obesity"
    rng = (0, 65) if col == "inactivity" else (0, 70)
    snap = df[df["Year"] == YEAR].dropna(subset=[col])
    fig = px.choropleth(snap, locations="Code", color=col, hover_name="Entity",
                        color_continuous_scale="OrRd", range_color=rng,
                        labels={col: metric})
    fig.update_layout(height=400, margin=dict(t=0, b=0, l=0, r=0),
                      coloraxis_showscale=False,
                      geo=dict(showframe=False, projection_type="natural earth"))
    return fig


def overview(df, a, b, d):
    least, most = quartile_medians(df)
    leb_rank = int(d[d["Code"] == "LBN"]["rank"].iloc[0]) if (d["Code"] == "LBN").any() else None

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Countries", d["Code"].nunique())
    k2.metric("Obesity \u2014 most inactive", f"{most:.0f}%")
    k3.metric("Obesity \u2014 most active", f"{least:.0f}%")
    k4.metric("Lebanon inactivity rank", f"#{leb_rank}" if leb_rank else "\u2014")

    region = st.selectbox("Filter the relationship & ranking by region",
                          ["All regions"] + REGIONS)
    dd = d if region == "All regions" else d[d["who_region"] == region]

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Obesity rises as activity falls**")
        st.plotly_chart(scatter(dd, a, b), use_container_width=True)
    with right:
        metric = st.radio("Map", ["Inactivity", "Obesity"], horizontal=True,
                          label_visibility="collapsed")
        st.plotly_chart(world_map(df, metric), use_container_width=True)

    st.markdown("**Are the most inactive countries also the most obese?**")
    st.plotly_chart(ranked_bars(dd), use_container_width=True)

    st.markdown("**Key insights**")
    st.markdown(
        f"- Obesity climbs with inactivity \u2014 the most-inactive countries average "
        f"~{most:.0f}% obesity vs ~{least:.0f}% in the most active.\n"
        "- The same places top both: the Gulf and Lebanon's Eastern Mediterranean region lead on each.\n"
        "- But it's an association, not a rule \u2014 South Korea and India are highly inactive yet lean, so diet and wealth matter too.\n"
        "- Why it matters: obesity is a gateway to heart disease, type 2 diabetes and other serious conditions.")


def predict(df, a, b, r2, d):
    st.markdown("#### Can activity level predict obesity?")
    st.markdown(f"A simple linear model fit across {len(d)} countries (2022):")
    st.markdown(f"### obesity % = {a:.1f} + {b:.2f} × inactivity %")

    m1, m2, m3 = st.columns(3)
    m1.metric("Each +10 pts inactivity", f"+{b*10:.1f} pts obesity")
    m2.metric("Variation explained (R\u00b2)", f"{r2*100:.0f}%")
    m3.metric("Strength", "moderate")

    fig = px.scatter(d, x="inactivity", y="obesity", hover_name="Entity",
                     opacity=0.5, color_discrete_sequence=[MUTED],
                     labels={"inactivity": "adults insufficiently active (%)",
                             "obesity": "adults obese (%)"})
    xs = np.array([d["inactivity"].min(), d["inactivity"].max()])
    fig.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines",
                  line=dict(color=CORAL, width=3), name="model", showlegend=False))
    fig.update_layout(height=400, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Try it**")
    x = st.slider("If a country's adult inactivity were\u2026 (%)", 5, 70, 40)
    st.metric("Predicted obesity", f"{a + b*x:.1f}%")

    st.info("Activity alone explains only about "
            f"{r2*100:.0f}% of the differences in obesity between countries "
            "\u2014 a real signal, but a rough predictor. Diet, wealth and the food "
            "environment account for most of the rest, which is why the cloud of "
            "points is wide around the line.")


def main():
    st.set_page_config(page_title="Moving Less, Weighing More", layout="wide")
    if not password():
        return
    df = load()
    a, b, r2, d = fit(df)

    st.title("Moving less, weighing more")
    st.caption("Across ~190 countries, the less adults move, the more obese they "
               "are \u2014 and obesity drives heart disease and diabetes. WHO data, 2022.")

    tab1, tab2 = st.tabs(["Overview", "Predict obesity"])
    with tab1:
        overview(df, a, b, d)
    with tab2:
        predict(df, a, b, r2, d)


if __name__ == "__main__":
    main()
