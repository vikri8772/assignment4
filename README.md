# Ekte Mat Online

INFO212 assignment 4: a first version of the ordering system for Ekte Mat AS, a fictional catering company in Bergen. Customers order catering online and admins manage food items, orders and questions.

- Design diagrams: [docs/plans/README.md](docs/plans/README.md)
- Built with Flask (MVC) and SQLite, moving to Neo4j in assignment 5.

## Install

Requires Python 3.10 or newer. Run these commands from the project folder.

```bash
python -m venv .venv
```

Activate the virtual environment. On Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Then install the packages:

```bash
pip install -r requirements.txt
```

## Seed

Creates the database with synthetic sample data: events, diets, food items and test users. **This deletes all existing data.**

```bash
python seed.py
```

To start over with an empty database instead, run `flask --app app init-db`.

## Run

```bash
flask --app app run --debug
```

Open http://127.0.0.1:5000. Test logins (synthetic, from `seed.py`):

| Role | E-mail | Password |
|---|---|---|
| Admin | admin@ektemat.test | admin1234 |
| Customer | kari@example.test | kunde1234 |
| Customer | ola@example.test | kunde1234 |

Optional: set the environment variable `SECRET_KEY` to keep people logged in when the server restarts. Never commit it.

## Test

```bash
pytest
```

## Project structure

```
app/
  models/        # domain classes + repositories (the only code that touches the database)
  controllers/   # Flask blueprints: shop, account, admin
  templates/     # Jinja2 views: shop/, account/, admin/
  static/        # CSS, JS, uploaded images
tests/
seed.py
```

To add a feature, follow the pattern in [docs/plans/skeleton-plan.md](docs/plans/skeleton-plan.md).
