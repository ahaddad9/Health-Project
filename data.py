"""
Data layer for the health spending paradox dashboard.

Reads four local OWID CSVs (bundled in ./data), cleans them to real
countries, merges into one country-year table, and adds the metrics the
two-world story needs:

  value_gap  -> years lived above/below what spending predicts (efficiency)
  life_per_1k-> life expectancy bought per $1,000 of spending

The "two worlds":
  - Across all countries, life expectancy rises with access (UHC) and with
    spending (which buys access at low income).
  - Among rich countries, access is universal (UHC ceiling) and more spending
    no longer buys life. Efficiency, not budget, separates them. Obesity is a
    visible contributing factor.
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

FILES = {
    "health_pc": "annual-healthcare-expenditure-per-capita.csv",
    "life_exp": "life-expectancy-unwpp.csv",
    "uhc": "universal-health-coverage-index.csv",
    "obesity": "share-of-adults-defined-as-obese.csv",
}

DEFAULT_HIGHLIGHT = ["United States", "Japan"]
RICH_THRESHOLD = 4000  # PPP int-$ per person: "access is universal" club


def _tidy(path: Path, name: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    val = [c for c in df.columns if c not in ("Entity", "Code", "Year")][0]
    df = df[df["Code"].notna()]
    df = df[df["Code"].str.fullmatch(r"[A-Z]{3}")]   # real countries only
    return df.rename(columns={val: name})[["Entity", "Year", name]]


def _add_value_gap(df: pd.DataFrame) -> pd.DataFrame:
    """Per year, fit life_exp ~ a + b*ln(spend) across countries; the residual
    is how many years a country lives above/below its spending prediction."""
    df = df.copy()
    df["value_gap"] = np.nan
    for yr, g in df.groupby("Year"):
        m = g["health_pc"].notna() & g["life_exp"].notna() & (g["health_pc"] > 0)
        if m.sum() < 8:
            continue
        b, a = np.polyfit(np.log(g.loc[m, "health_pc"]), g.loc[m, "life_exp"], 1)
        pred = a + b * np.log(g.loc[m, "health_pc"])
        df.loc[g.loc[m].index, "value_gap"] = g.loc[m, "life_exp"] - pred
    return df


def load_data(data_dir: Path | None = None) -> pd.DataFrame:
    d = data_dir or DATA_DIR
    frames = {k: _tidy(d / fn, k) for k, fn in FILES.items()}
    df = frames["health_pc"].merge(frames["life_exp"], on=["Entity", "Year"], how="inner")
    df = df.merge(frames["uhc"], on=["Entity", "Year"], how="left")
    df = df.merge(frames["obesity"], on=["Entity", "Year"], how="left")
    df["life_per_1k"] = df["life_exp"] / (df["health_pc"] / 1000.0)
    df = _add_value_gap(df)
    return df.sort_values(["Entity", "Year"]).reset_index(drop=True)


def year_bounds(df: pd.DataFrame) -> tuple[int, int]:
    return int(df["Year"].min()), int(df["Year"].max())


def cross_section(df: pd.DataFrame, year: int) -> pd.DataFrame:
    return df[(df["Year"] == year)
             & df["health_pc"].notna() & df["life_exp"].notna()].copy()
