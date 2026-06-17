# Measles Burden Explorer

A consultant dashboard for MSBA382 Healthcare Analytics. It examines the global
measles burden and tests one thesis: measles resurges wherever first-dose (MCV1)
coverage falls below the ~95% needed for herd immunity, with risk rising sharply
under ~80%.

## What's inside

| File | Purpose |
|------|---------|
| `app.py` | The Streamlit dashboard (8 views + password gate) |
| `measles_master.csv` | Cleaned, joined dataset (194 countries, 1980–2024) |
| `requirements.txt` | Python dependencies |
| `.streamlit/config.toml` | Theme |
| `.streamlit/secrets.toml.example` | Password template |

## Views

Overview · Trends · Coverage vs. incidence · Map · Country deep-dive ·
Program comparison · Outbreak prediction · Data & methodology.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Default password is `measles2026`. To change it, create `.streamlit/secrets.toml`
with `app_password = "your-password"`.

## Publish (Streamlit Community Cloud)

1. Push this folder to a public GitHub repository.
2. Go to share.streamlit.io, sign in with GitHub, and click **New app**.
3. Pick the repo and set the main file to `app.py`.
4. Under **Advanced settings → Secrets**, paste:
   `app_password = "your-password"`
5. Deploy. The public URL is your dashboard link for submission.

## Data sources

- Reported measles cases — Our World in Data, from the WHO Global Health Observatory.
- MCV1 / DTP3 / Polio coverage — Our World in Data, from WHO/UNICEF estimates (WUENIC).
- Population — World Bank.

Cases joined to coverage and population on ISO-3 country code and year.
Incidence = reported cases ÷ population × 1,000,000.
