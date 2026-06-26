# The Spending Paradox — Health Analytics Dashboard

A single-screen Streamlit dashboard asking whether higher health spending
actually buys longer lives. Built for MSBA382 Healthcare Analytics.

## The story (one screen, top to bottom)

Two worlds, one chart deck:

- **KPIs** — the paradox in numbers for two highlighted countries.
- **1 · More money, more life — up to a point.** Life expectancy vs spending,
  every country, coloured by health-service access (UHC). Steep where spending
  buys access, flat once access is near-universal.
- **2 · The relentless rise.** Spending per person over time.
- **3 · Inside the rich-country club.** Among countries spending ≥ $4k, access
  is universal and more money no longer buys life; points coloured by obesity
  show heavier countries lagging.
- **4 · Value for money.** Years lived above/below what each country's spending
  predicts. Big spenders sink to the bottom; the US is last.

## Headline findings (2019)

- Across 192 countries, access (UHC) tracks life expectancy at r ≈ 0.84.
- Among rich countries, spending more correlates with life expectancy at
  r ≈ −0.30 — negative. Money stops buying life once access is universal.
- Obesity tracks the rich-country shortfall at r ≈ −0.47. The US (40% obese,
  vs Japan 4.5%) lives 6.2 years less than its spending predicts — worst in
  the sample.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Reads the four CSVs in `data/`. No internet needed.

## Password

Opens behind a gate. Create `.streamlit/secrets.toml`:

```toml
password = "your-password-here"
```

Falls back to `health2026` if unset. On Streamlit Community Cloud set it under
App settings → Secrets instead of committing the file.

## Publish (Streamlit Community Cloud, free)

1. Push this folder (including `data/`) to a public GitHub repo.
2. share.streamlit.io → New app → point at the repo and `app.py`.
3. Add the `password` secret. Deploy. The public URL is your submission link.

## Submission data file

Sidebar → **Download merged data (CSV)** gives the cleaned, merged country-year
table the dashboard runs on. Use it as your project data file.

## Files

- `app.py` — dashboard
- `data.py` — load, clean, merge, value-gap metric
- `smoke_test.py` — offline pipeline + narrative test
- `data/` — the four source CSVs (Our World in Data)
- `requirements.txt`, `README.md`

## A note on claims

Relationships are correlational. The rich-country gaps also reflect inequality,
diet, demographics, and other factors beyond the health system. Obesity is shown
as one visible contributor, not a sole cause.
