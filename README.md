# Star Citizen Tracker

A browser-based Streamlit app for:

- Contract payout calculations and crew splits
- Mined, bought, and sold ore records
- Interactive tables and Plotly graphs
- Editing and deleting mistakes
- CSV exports
- Private Supabase login and row-level security

## 1. Create the Supabase database

1. Create a free Supabase project.
2. Open **SQL Editor**.
3. Open `schema.sql` from this project.
4. Paste the full script into a new query.
5. Select **Run**.

The script creates both tables and Row Level Security policies so each
signed-in account can only access its own rows.

## 2. Get the Supabase connection values

In Supabase, open the project's API settings and copy:

- Project URL
- Publishable key or legacy anon key

Do not use a secret or service-role key in this app.

## 3. Test locally, optional

Copy `.streamlit/secrets.toml.example` to:

`.streamlit/secrets.toml`

Replace the placeholders with the Supabase URL and key.

Install and run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 4. Upload to GitHub

Create a GitHub repository and upload:

- `app.py`
- `schema.sql`
- `requirements.txt`
- `.gitignore`
- `.streamlit/secrets.toml.example`
- `README.md`

Do not upload a real `.streamlit/secrets.toml` file.

## 5. Deploy through Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud with GitHub.
2. Create a new app.
3. Select the GitHub repository.
4. Set the entrypoint file to `app.py`.
5. Open Advanced settings and add:

```toml
SUPABASE_URL = "your project URL"
SUPABASE_KEY = "your publishable or anon key"
```

6. Deploy.

## 6. First login

Open the deployed app, choose **Create account**, and create the private
login you will use on your computer, phone, and tablet.

Depending on the Supabase Auth settings, you may need to confirm your
email before signing in.

## Existing Colab data

Keep the current Google Drive SQLite database as a backup. The old
records can be migrated after the online app is confirmed working.
