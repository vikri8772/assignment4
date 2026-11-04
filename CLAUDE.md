# Ekte Mat Online

INFO212 obligatory assignment 4. A first version of the ordering system for Ekte Mat AS, a fictional catering company in Bergen. It replaces ordering by e-mail, phone and Excel.

Design diagrams (Mermaid) are in `docs/plans/`. `docs/plans/README.md` lists requirements and which diagrams belong to each one. Read the ones that apply before changing a feature.

## Architecture (MVC)

Flask backend with Jinja2 templates. The layers must stay visible in the folder structure:

    app/
      models/        # domain classes + repository classes (the ONLY code that touches storage)
      controllers/   # Flask blueprints: shop, account, admin
      templates/     # Jinja2 views: shop/, account/, admin/
      static/        # CSS, JS, uploaded images
    tests/

- Controllers call repositories and domain classes. They never access storage directly.
- Storage is Neo4j. Only the repository classes (`FoodItemRepository`, `OrderRepository`, ...) and `app/models/db.py` touch it; nothing outside `app/models/` imports `neo4j`.
- The graph model (nodes, relationships, constraints) is in `docs/plans/neo4j-graph-model.md`. Constraints are created by `init_db()` in `app/models/db.py`.
- Repositories get a `Database` from `get_db()` and run Cypher with `db.query()` / `db.query_one()`. Write each save as one Cypher statement, so it is saved completely or not at all. Neo4j has no foreign keys: `MATCH` referenced nodes and raise `IntegrityError` (from `db.py`) when one is missing.
- Protect routes with `@login_required` or `@admin_required` from `app/controllers/auth.py`. The logged-in user is `g.user`.
- How to add a feature (domain class, table, repository, seed data, tests): `docs/plans/skeleton-plan.md`.

## Run and test
Activate `.venv` first. Full setup steps, including installing Neo4j and `.env`, are in `README.md`.

    pip install -r requirements.txt
    neo4j start                     # Neo4j must run for the app, seed.py and pytest
    python seed.py                  # wipes the database and loads synthetic test data
    flask --app app run --debug     # http://127.0.0.1:5000
    pytest                          # also wipes the database: run seed.py afterwards

Test logins are listed in `seed.py` and `README.md`.

## Team rules
- Work on your own branch and merge into `main` through a pull request.
- Plan every larger feature in plan mode first, and commit the agreed plan to `docs/plans/` before building it.
- Use synthetic data only.
- Never commit secrets or API keys (including a Claude API key). Keep them in `.env`, which is in `.gitignore`.
- Add or update tests for every feature, and run `pytest` before you push.
