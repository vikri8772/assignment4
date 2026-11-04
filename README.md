# Ekte Mat Online

INFO212 assignment 4: a first version of the ordering system for Ekte Mat AS, a fictional catering company in Bergen. Customers order catering online and admins manage food items, orders and questions.

- Design diagrams: [docs/plans/README.md](docs/plans/README.md)
- Built with Flask (MVC) and **Neo4j** as the database (assignment 5). Graph model: [docs/plans/neo4j-graph-model.md](docs/plans/neo4j-graph-model.md)

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

## Neo4j

The app stores its data in a local Neo4j database. Install it once:

- **macOS:** `brew install neo4j`
- **Windows:** install [Neo4j Desktop](https://neo4j.com/download/), create a local database and start it.

Then give the `neo4j` user a password. On macOS, before the first start:

```bash
neo4j-admin dbms set-initial-password ektemat-dev
```

In Neo4j Desktop you choose the password when you create the database.

Copy the settings file and change `NEO4J_PASSWORD` if you chose another password. `.env` is not committed.

```bash
cp .env.example .env
```

Start Neo4j (on macOS; in Neo4j Desktop, press Start):

```bash
neo4j start
```

The Neo4j Browser at http://localhost:7474 shows the graph. Try `MATCH (n) RETURN n`. Stop the database with `neo4j stop`.

## Seed

Fills Neo4j with synthetic sample data: events, diets, food items, test users, orders and questions. **This deletes all existing data.** Neo4j must be running.

```bash
python seed.py
```

To start over with an empty database instead, run `flask --app app init-db`. It deletes all nodes and creates the constraints.

The seeded food items get their pictures from `app/static/img/food/`. These food photos are taken from recipe websites for illustration in this student project and are not ours. Pictures that admins upload are saved in `app/static/uploads/`, which is not committed.

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

The tests need Neo4j running, and they **empty the database**. Run `python seed.py` afterwards to get the sample data back.

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
