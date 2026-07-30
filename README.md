# Star Citizen Tracker

![Star Citizen Tracker](assets/hero_banner.jpg)

A private, multiuser operations dashboard for **Star Citizen** built with Streamlit and Supabase.

The application combines contract tracking, mining and ore inventory, commodity trading, mining locations, blueprint readiness, saved records, account management, and export tools in one responsive web interface.

**Live application:** [https://sc-tracker-tool.streamlit.app/](https://sc-tracker-tool.streamlit.app/)


## Premium interface transformation

The application now uses a unified product design system based on the approved
Purchase Locations concept:

- Warm off-white application background
- White rounded content cards
- Olive navigation and action accents
- Minimal borders and no heavy shadows
- Compact top-level page headings instead of image-heavy banners
- Icon-led sidebar navigation
- Unified metric cards, tabs, inputs, forms, charts, and alerts
- Compact quick-access cards on the Dashboard
- Minimal purchase and sale location lists with direct **Use in Tracker**
  actions
- Compact item-shop purchase rows instead of wide spreadsheet tables
- Detailed UEX terminal fields moved into a collapsed advanced-data section
- Green and red reserved for positive and negative monetary meaning
- Existing authentication, Supabase data, calculations, exports, UEX data,
  loot records, and migrations preserved

### Deploying the redesigned version

For the visual redesign, replace:

```text
app.py
.streamlit/config.toml
README.md
```

No new database migration is required for the design transformation. Existing
projects should still have migrations through
`schema_migration_v9_loot_and_shops.sql` applied.

## Current Release Highlights

This version includes the complete redesign and functionality upgrades developed for the tracker:

- Professional light interface using the chartreuse accent `#98FB17`
- Flat buttons and tabs with no gradients or drop shadows
- Visible four-sided outlines on text fields, dropdowns, number inputs, text areas, checkboxes, radio groups, and file uploaders
- Persistent login using an encrypted browser refresh-token cookie
- Remembered account email and optional keep-signed-in behavior
- Password recovery, password change, display name, profile picture, and timezone settings
- Compact inline submission confirmations instead of large success popups
- Contracts, ore, and commodity activity included in the Dashboard
- Verified ore and commodity calculations shared across records, graphs, inventory, and exports
- Commodity Trading shortcut added to the Dashboard
- Commodity Ledger added to Saved Records
- Live UEX market and mining-location data
- SC Trade Tools directory integration with optional licensed API access
- SC Craft Tools blueprint database integration
- Excel, CSV ZIP, and optional filled Google Sheets exports
- U.S. timezone options plus support for additional IANA timezones
- Responsive desktop and mobile layouts


## Loot and Shop Finder

The **Loot & Shops** page combines live item-store information with a
community-maintained acquisition table.

### Item Shop Finder

The live shop finder uses UEX item categories, item metadata, and terminal
prices to display:

- Item
- Category and section
- Manufacturer
- Size
- System and environment
- Full terminal location
- Price paid by the player
- Price paid by the terminal when buying from the player
- Game version
- Last update
- Wiki link

The table can be searched, filtered by system, limited to currently
purchasable listings, and downloaded as CSV.

### Shared Loot Table

Authenticated users can record:

- Item name and category
- Acquisition type
- System and location
- Specific room or area
- Container, boss, mission, or reward source
- Rarity
- Mission or event
- Patch version
- Verification status and date
- Notes
- Shared or private visibility

Shared records are visible to every authenticated app user. Private records
remain visible only to the account that created them. Users can update or
delete only their own entries.

Run `schema_migration_v9_loot_and_shops.sql` once before using the shared
loot table. The live UEX shop finder does not depend on that migration.



## Asset Image Reintegration

The packaged artwork in `assets/` is integrated into the modern interface
without reverting the current typography, borders, controls, calculations, or
page structure.

The current image placements include:

- `dashboard_banner.jpg` for the Dashboard welcome area
- `hero_banner.jpg` for authentication and account recovery
- `contracts_banner.jpg` for Contracts and Blueprints
- `ore_banner.jpg` for the Ore Ledger and Mining Locations
- `records_banner.jpg` for Records, Commodities, and Loot & Shops
- `export_banner.jpg` for Export Data
- `edit_banner.jpg` for the Profile page
- Feature images for the Dashboard workspace shortcuts
- `star_citizen_logo_black.png` in the sidebar brand
- `sidebar_art.jpg` in the sidebar operations card

Images use responsive cover cropping, gradient overlays, and fixed-height
containers so they remain readable without stretching or changing the
application's modern layout.

## Main Features

### Dashboard

The Dashboard provides a quick overview of the signed-in user's activity.

It includes:

- Total earnings over time
- Net contribution by source
- Contract earnings by type
- Ore value by mineral
- Commodity purchase, sale, loss, and net-profit performance
- Activity mix across contracts, ore, and commodities
- Contract take-home
- Ore sales and on-hand SCU
- Commodity sales, on-hand SCU, and net cash flow
- Total recorded spending
- Overall net profit
- Date-range and record-search filters
- Shortcut cards for Contracts, Ore, Commodities, Saved Records, and Mining Locations

### Contract Calculator

Record and calculate contract activity using:

- Contract name
- Contract type
- Offer group
- System or area
- Total payout
- Expenses
- Crew size
- Individual share
- Notes

Contract math:

```text
Net payout = Total payout - Expenses
Individual share = Net payout / Crew members
```

### Ore Ledger

Track mined, purchased, and sold ores or gems.

Each entry supports:

- Ore or mineral
- Activity type
- SCU quantity
- Price per SCU or total cargo value
- Location
- Notes
- Verified value
- Cash effect
- On-hand inventory

Ore math:

```text
Verified value = SCU quantity × Unit price

On hand = Mined SCU + Bought SCU - Sold SCU

Ore trade net = Sales revenue - Purchase cost
```

Older value-only records remain visible, but their SCU quantity must be entered manually before they can affect inventory.

### Commodities

The Commodities workspace includes:

- Market Snapshot
- Trade Routes
- Route Planner
- My Trade Tracker
- SC Trade Tools
- Cargo Calculator
- Best player purchase price
- Best player sale price
- Maximum spread
- Estimated gross profit
- Matching terminals
- Buy and sell location tables
- Shipment-loss tracking
- Commodity inventory
- Trade history
- CSV downloads
- Data-health diagnostics

Commodity math:

```text
Cargo value = SCU quantity × Unit price

Bought cash effect = -(Cargo value + Fees)

Sold cash effect = Cargo value - Fees

Lost or destroyed cash effect = -(Cargo value + Fees)

On hand = Bought SCU - Sold SCU - Lost SCU

Net cash flow = Sales revenue - Purchase cost - Recorded losses
```

Commodity submissions are verified by reading the saved record back from Supabase before the app confirms success.

### Mining Locations

Search and filter mining locations using:

- Ore or gem
- Resource type
- System
- Environment
- Planet, moon, station, asteroid, or space
- Mining method
- Location search
- Spawn information and occurrence data

The page uses live UEX relationships when available and includes a packaged fallback dataset in `data/mining_locations.csv`.

### Blueprints

The Blueprints area includes:

- Embedded SC Craft Tools database
- External database link when embedding is blocked
- Personal blueprint tracker
- Blueprint ownership
- Copies owned
- Planned builds
- Acquisition location
- Required ores and gems
- Material-readiness comparison against the Ore Ledger
- Blueprint editing and deletion

### Saved Records

View and manage:

- Contracts
- Ore Ledger records
- Commodity Ledger records

The management area supports editing and permanent deletion of saved records.

### Export Data

Export the user's complete tracker data as:

- Formatted Excel workbook
- CSV ZIP package
- Individual CSV files
- Optional automatically populated Google Sheet

The complete workbook can include:

- Summary
- Contracts
- Ore Ledger
- Ore Inventory
- Commodity Ledger
- Commodity Inventory

## User Accounts and Security

The application uses Supabase Authentication and Row Level Security.

Account features include:

- Email and password sign-in
- New account registration
- Password-reset email
- Password update
- Remembered email
- Optional persistent login
- Encrypted browser refresh-token storage
- Display name
- Profile image
- Timezone selection
- Secure sign-out

Each user's private records are filtered by their Supabase user ID.

Never commit `.streamlit/secrets.toml`, API tokens, cookie passwords, or service-account credentials to GitHub.

## Technology Stack

- Python
- Streamlit
- Supabase
- PostgreSQL
- Pandas
- Plotly
- XlsxWriter
- Google Sheets API
- UEX API
- SC Trade Tools
- SC Craft Tools
- Pillow
- Encrypted Streamlit cookies

## Project Structure

```text
star-citizen-tracker/
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── assets/
│   ├── commodity_feature.jpg
│   ├── contracts_banner.jpg
│   ├── contracts_feature.jpg
│   ├── dashboard_banner.jpg
│   ├── edit_banner.jpg
│   ├── export_banner.jpg
│   ├── fleet_feature.jpg
│   ├── hero_banner.jpg
│   ├── ore_banner.jpg
│   ├── ore_feature.jpg
│   ├── records_banner.jpg
│   ├── records_feature.jpg
│   ├── sidebar_art.jpg
│   └── star_citizen_logo_black.png
├── data/
│   └── mining_locations.csv
├── app.py
├── requirements.txt
├── schema.sql
├── schema_migration_v2.sql
├── schema_migration_v3_blueprints.sql
├── schema_migration_v3_blueprints_repair.sql
├── schema_migration_v4_commodity_tracker.sql
├── schema_migration_v5_profile_avatars.sql
├── schema_migration_v6_commodity_math_repair.sql
├── schema_migration_v7_ore_math_repair.sql
├── schema_migration_v8_ore_schema_cache_repair.sql
├── schema_migration_v9_loot_and_shops.sql
├── commodity_sales_verification.sql
└── README.md
```

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/star-citizen-tracker.git
cd star-citizen-tracker
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Supabase

Create a Supabase project.

For a new database, run:

```text
schema.sql
```

Run the file in the Supabase SQL Editor.

For an existing tracker database, apply only the migrations that have not already been run:

```text
schema_migration_v2.sql
schema_migration_v3_blueprints.sql
schema_migration_v4_commodity_tracker.sql
schema_migration_v5_profile_avatars.sql
schema_migration_v6_commodity_math_repair.sql
schema_migration_v7_ore_math_repair.sql
schema_migration_v8_ore_schema_cache_repair.sql
schema_migration_v9_loot_and_shops.sql
```

Use `schema_migration_v3_blueprints_repair.sql` only when the original blueprint migration failed or the blueprint tables and policies require repair.

Do not repeatedly run migrations that have already completed successfully unless the file explicitly uses safe repair logic.

### 5. Configure Streamlit Secrets

Copy:

```text
.streamlit/secrets.toml.example
```

to:

```text
.streamlit/secrets.toml
```

Then add the required values:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "your-supabase-anon-or-publishable-key"
COOKIE_PASSWORD = "replace-with-a-long-random-secret"
APP_PUBLIC_URL = "https://sc-tracker-tool.streamlit.app/"
```

Optional UEX live data:

```toml
UEX_API_TOKEN = "your-private-uex-token"
UEX_CLIENT_VERSION = "1.0.0"
```

Optional SC Trade Tools licensed data:

```toml
SC_TRADE_TOOLS_TOKEN = "your-private-sc-trade-tools-token"
```

Optional populated Google Sheets export:

```toml
GOOGLE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY\\n-----END PRIVATE KEY-----\\n",
  "client_email": "service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "your-certificate-url"
}
'''
```

### 6. Configure Supabase Authentication URLs

In Supabase:

```text
Authentication → URL Configuration
```

Set the Site URL to:

```text
https://sc-tracker-tool.streamlit.app/
```

Add this Redirect URL:

```text
https://sc-tracker-tool.streamlit.app/**
```

For local testing, also add:

```text
http://localhost:8501/**
```

### 7. Run locally

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Streamlit Community Cloud Deployment

1. Push the project files to GitHub.
2. Keep `app.py` in the repository root.
3. Connect the repository to Streamlit Community Cloud.
4. Set the entrypoint to `app.py`.
5. Copy the private values into the app's Streamlit Secrets settings.
6. Reboot the application after changing dependencies, Secrets, or database migrations.

Do not upload the real `.streamlit/secrets.toml` file.

## Live Data and Refresh Behavior

### UEX

UEX provides live mining and commodity information when `UEX_API_TOKEN` is configured.

The application caches supported live responses for approximately 14 minutes. The commodity market section can refresh every 15 minutes while the page remains open.

### SC Trade Tools

Public directory data can be used without a private token.

A valid licensed token may unlock selected commodity transaction and market-report endpoints:

```toml
SC_TRADE_TOOLS_TOKEN = "your-private-token"
```

Availability and permitted use depend on SC Trade Tools' current API access and terms.

### SC Craft Tools

The Blueprint page embeds:

```text
https://sc-craft.tools/
```

Some browsers or providers may block embedded viewing. The application also provides an external-link option.

### Google Sheets

Without a Google service account, download the Excel workbook and import it into Google Sheets.

With `GOOGLE_SERVICE_ACCOUNT_JSON`, the app can create a populated Google Sheet automatically.

## Database Migration Summary

| File | Purpose |
|---|---|
| `schema.sql` | Complete database setup for a new deployment |
| `schema_migration_v2.sql` | Adds ore quantity support |
| `schema_migration_v3_blueprints.sql` | Creates the private blueprint tracker |
| `schema_migration_v3_blueprints_repair.sql` | Repairs blueprint tables or policies when needed |
| `schema_migration_v4_commodity_tracker.sql` | Creates the commodity transaction ledger |
| `schema_migration_v5_profile_avatars.sql` | Adds profile-avatar storage and policies |
| `schema_migration_v6_commodity_math_repair.sql` | Repairs commodity totals, cash effects, constraints, and triggers |
| `schema_migration_v7_ore_math_repair.sql` | Repairs ore unit prices, values, cash effects, constraints, and triggers |
| `schema_migration_v8_ore_schema_cache_repair.sql` | Guarantees missing ore columns exist, rebuilds the trigger and RLS policies, and refreshes the Supabase/PostgREST schema cache |
| `schema_migration_v9_loot_and_shops.sql` | Adds the authenticated shared/private community loot table and its Row Level Security policies |



### Version 8 ore schema-cache repair

Version 7 referenced `quantity_scu` without guaranteeing that the column
existed first. On a legacy database without that column, PostgreSQL aborted
the transaction and rolled the entire migration back.

Run `schema_migration_v8_ore_schema_cache_repair.sql` as one complete query.
The migration creates every required ore column before referencing it,
rebuilds the calculation trigger and Row Level Security policies, refreshes
PostgREST's schema cache, and returns two verification results. The first
result must list `quantity_scu`, `unit_price`, `total_value`, and
`cash_effect`.

## Troubleshooting

### The app logs out after refreshing

Confirm that:

- `COOKIE_PASSWORD` is set and remains unchanged
- The user selected the keep-signed-in option
- Browser cookies are allowed
- The application is being opened from the configured `APP_PUBLIC_URL`

Changing `COOKIE_PASSWORD` invalidates previously stored encrypted cookies.

### Password-reset links return to the wrong page

Update:

```toml
APP_PUBLIC_URL = "https://sc-tracker-tool.streamlit.app/"
```

Then confirm the same address is permitted in Supabase Authentication URL Configuration.

### Commodity sales do not appear

Run:

```text
schema_migration_v6_commodity_math_repair.sql
```

Then use:

```text
commodity_sales_verification.sql
```

to confirm that Bought, Sold, and Lost records are stored in Supabase.

The verification query should show `incomplete_math_rows = 0` after all rows have valid quantities and prices.

### Ore inventory shows 0 SCU

Run:

```text
schema_migration_v7_ore_math_repair.sql
schema_migration_v8_ore_schema_cache_repair.sql
schema_migration_v9_loot_and_shops.sql
```

Older records that stored only aUEC value cannot be assigned an accurate SCU quantity automatically. Edit those records under:

```text
Saved Records → Manage Records → Ore Entry
```

### Blueprints do not load

Confirm the blueprint migration completed.

Use:

```text
schema_migration_v3_blueprints_repair.sql
```

when the original migration failed or the database table is missing.

The external SC Craft Tools site may also block iframe embedding. Use the external-link button when necessary.

### Google Sheets opens blank

Automatic populated Sheets require `GOOGLE_SERVICE_ACCOUNT_JSON`.

Without that secret, download the Excel workbook and import it into Google Sheets manually.

### A control has a missing outline

Confirm that the latest `app.py` and `.streamlit/config.toml` are deployed together, then reboot the Streamlit app.

The current interface draws a complete perimeter around the Streamlit control wrapper to avoid clipped top and bottom borders.



### Commodity listing identification update

UEX terminal tables now retain and display the commodity name on every row.
The **Best Places to Buy**, **Best Places to Sell**, **All Matching Terminal
Listings**, and filtered market CSV include a dedicated `Commodity` column.
The currently selected commodity is used as a fallback when the UEX price
response does not return a commodity-name field.



### Number-input alignment and live ore calculation update

Number-input help icons are now styled separately from decrement and increment
controls, preventing tooltip buttons from stretching into rectangular boxes.
Paired numeric fields align along the same bottom edge throughout the Ore
Ledger entry panel.

The Ore Ledger entry area now uses live Streamlit widgets rather than a form,
so the verified SCU, unit-price, total-value, and cash-effect calculation
updates immediately as the user changes a value.



### Standard green and red chart colors

Dashboard charts now use conventional data colors while the surrounding app
retains its chartreuse interface theme. Positive values, earnings, revenue,
and mined activity use standard green. Negative values, costs, losses, and
sold-series comparisons use standard red.



### Combined commodity purchase and sale entry

The Commodity Trade Tracker now uses one combined entry panel for quantity,
price, fees, purchase or departure location, sale or destination location,
shipment reference, and notes. The prior activity dropdown and duplicate save
buttons were removed.

Two action buttons appear together at the bottom:

- **Save Commodity Purchase**
- **Save Commodity Sale**

Either button saves every field in the combined panel. When **Shipment
destroyed or lost** is selected, either action button records the entry as a
lost or destroyed shipment.



### Automatic graph scaling and category colors

Dashboard bar charts now calculate their axis limits from the current values
on every Streamlit rerun. Additional range is reserved for value labels, so
larger totals do not clip against the plot boundary or legend.

Green and red are reserved for signed monetary meaning. Positive money uses
green and negative money uses red. Categorical series use distinct colors:

- Contracts: blue
- Ore and mining categories: orange or teal
- Commodities and other categories: purple
- Ore actions use separate teal, orange, and purple series

## Major Update History

### Account and session upgrades

- Added remembered email
- Added encrypted persistent login
- Added password recovery
- Added change-password controls
- Added profile name, profile picture, and timezone settings
- Added authentication-screen toolbar spacing
- Restored safe timezone fallback behavior

### Dashboard and analytics upgrades

- Added contracts, ore, and commodities to combined earnings
- Added commodity performance graphs
- Added source-contribution reporting
- Added overall spending and net-profit summaries
- Added Dashboard shortcut cards
- Added filters and search
- Corrected date and timezone rendering

### Commodity upgrades

- Added UEX and SC Trade Tools market intelligence
- Added route planning
- Added buy, sell, and lost-shipment records
- Added on-hand inventory
- Added Saved Records support
- Added database read-back verification
- Added verified quantity, unit price, cargo value, and cash-effect math
- Added Excel, CSV, and Google Sheets commodity exports

### Ore upgrades

- Added SCU inventory
- Added price-per-SCU and total-value entry methods
- Added verified value and cash effect
- Added legacy-record warnings
- Added ore database triggers and constraints
- Added Saved Records management and exports

### Blueprint upgrades

- Added live SC Craft Tools database
- Added personal blueprint ownership tracker
- Added planned builds and material readiness
- Added profile-isolated Supabase storage

### Interface upgrades

- Replaced the original blue palette with chartreuse and green shades
- Added the sampled accent color `#98FB17`
- Removed button and tab gradients
- Removed button and tab shadows
- Improved text contrast
- Added visible control outlines
- Added responsive layouts
- Replaced large success alerts with compact inline confirmations

## Data and Rights Notice

This is an unofficial fan-made tool and is not affiliated with, sponsored by, or endorsed by Cloud Imperium Games or Roberts Space Industries.

Star Citizen, Roberts Space Industries, Cloud Imperium, and related names, logos, game imagery, and trademarks belong to their respective owners.

UEX, SC Trade Tools, and SC Craft Tools are independent third-party services. Their data, branding, availability, licensing requirements, and terms remain controlled by those providers.

Only use images, logos, screenshots, API data, or other assets when you have permission or a lawful basis to do so. Replace repository assets when required by the applicable owner or platform.

Market values, locations, spawn information, routes, and game mechanics can change after a Star Citizen update. Verify important information before making in-game decisions.

## Privacy and Security Notes

- User data is stored in Supabase
- Row Level Security is used to isolate each user's records
- Passwords are handled by Supabase Authentication
- Refresh tokens are stored in an encrypted browser cookie only when the user chooses to remain signed in
- API keys and service-account credentials must remain in Streamlit Secrets
- Do not commit private credentials to GitHub
- Rotate any token that has been exposed publicly

## Status

The tracker is actively evolving alongside Star Citizen, UEX, SC Trade Tools, SC Craft Tools, Streamlit, and Supabase.

Because third-party APIs and game data can change, occasional maintenance may be required after provider updates or major game patches.


## Modern product interface v2

This release replaces legacy banner imagery with a text-and-icon design system and modernizes the complete Streamlit interface. It adds stronger visual hierarchy, larger typography, visible control borders, elevated cards, segmented tabs, improved data tables, refined navigation, responsive layouts, and app-style list rows. Supabase tables, migrations, authentication, UEX integrations, calculations, and saved user data remain unchanged.
