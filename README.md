# Moving Less, Weighing More

MSBA382 Healthcare Analytics dashboard. Examines how adult physical inactivity
relates to obesity across ~190 countries (WHO data, 2000–2022), and frames
obesity as a gateway to heart disease and type 2 diabetes.

## Files
- `app.py` — the Streamlit dashboard (password-gated, 8 views)
- `mobility_master.csv` — joined dataset (inactivity + obesity, by country/year/sex)
- `requirements.txt` — dependencies
- `.streamlit/config.toml` — theme

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```
Default password: `move2026` (change via `.streamlit/secrets.toml` → `app_password = "..."`).

## Publish (Streamlit Community Cloud)
1. Push this folder to a public GitHub repo.
2. share.streamlit.io → New app → pick the repo → main file `app.py`.
3. Advanced → Secrets → paste `app_password = "yourpassword"` → Deploy.
The public URL is your dashboard link.

## Sources
WHO Global Health Observatory — insufficient physical activity (adults 18+,
age-standardised) and adult obesity (BMI ≥ 30). Joined on ISO-3 code and year.
