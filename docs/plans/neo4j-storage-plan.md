# Neo4j as the storage layer – plan

## Context
Assignment 4 allows the storage layer to be built in Neo4j now. If it is, the submission also counts as assignment 5 (say so on the report's front page). Today all data is in SQLite. The group followed the MVC rule: only the four repository classes and `app/models/db.py` touch storage, and controllers only call `get_db()` and repositories. So the change is limited to the model layer. Controllers, templates and domain classes stay as they are.

Vilde does all of it on branch `vilde`, with one pull request to `main`. The four repositories depend on each other (User → FoodItem → Order → Question), so the app only works again when all four are converted. Push and open the PR when all tests pass.

Local setup is done: Neo4j 2026.10.1 is installed with Homebrew, the password is set, and it runs on `bolt://localhost:7687` (browser: http://localhost:7474).

This plan is committed as `docs/plans/neo4j-storage-plan.md`, together with the graph model diagram, before any code.

## 1. Graph data model – `docs/plans/neo4j-graph-model.md` (new, Mermaid)
```
(:User {id, name, email, passwordHash, role})
(:Event {name})   (:Diet {name})
(:FoodItem {id, name, desc, price, minOrder, picturePath, published, allergens: [..]})
    -[:SERVED_AT]->(:Event)    -[:SUITS]->(:Diet)
(:User)-[:PLACED]->(:Order {id, eventDate, numberOfGuests, deliveryAddress, createdAt, orderStatus, paymentStatus})
(:Order)-[:FOR_EVENT]->(:Event)
(:Order)-[:CONTAINS {position, itemName, quantity, unitPrice}]->(:FoodItem)
(:Order)-[:HAS_GROUP {position}]->(:GuestGroup {groupName, numberOfGuests, allergyNotes, dietaryNotes})
(:User)-[:ASKED]->(:Question {id, text, askedAt, status, answerText, answeredAt})-[:ABOUT]->(:Order)
(:User)-[:ANSWERED]->(:Question)
```
- What were link tables in SQLite (`food_item_event`, `order_line`, ...) become relationships. An order line is a relationship with properties.
- Prices are stored as strings (`Decimal` without rounding errors). Dates and times are ISO strings, as in SQLite, so sorting and date filters work the same.
- Allergens stay a list property: they are a fixed list (`ALLERGENS` in `food.py`) and nothing else points to them.
- Constraints: `id` is unique on User, FoodItem, Order and Question; `User.email` is unique; `Event.name` and `Diet.name` are unique.

## 2. Connection – `app/models/db.py`, `app/__init__.py`, config
- `requirements.txt`: add `neo4j` (Python driver, pinned) and `python-dotenv`.
- Config from the environment, read from `.env` (already in `.gitignore`) with `python-dotenv`: `NEO4J_URI` (default `bolt://localhost:7687`), `NEO4J_USER` (default `neo4j`), `NEO4J_PASSWORD`. Commit a `.env.example` with the local development values. The `DATABASE` (SQLite file) setting is removed.
- `db.py` keeps the same functions, so controllers don't change:
  - `get_db()`: one driver per app, one session per request on `flask.g`, closed in `close_db()`.
  - `init_db()`: deletes all nodes (`MATCH (n) DETACH DELETE n`) and creates the constraints (`IF NOT EXISTS`). Replaces `schema.sql`, which is deleted.
  - `flask --app app init-db` still works.
  - `IntegrityError(Exception)`: our own error, raised by repositories when a referenced node is missing or a unique constraint is broken (Neo4j has no foreign keys). It replaces `sqlite3.IntegrityError`.
- No module outside `app/models/` imports `neo4j`, same rule as for `sqlite3` today.

## 3. Repositories (same public methods, same return values)
Each write is one Cypher statement, so it is saved completely or not at all, like `with self.db:` today. Referenced nodes are found with `MATCH`. If one is missing, nothing is created and `IntegrityError` is raised.
- `UserRepository`: `get_by_id`, `get_by_email`, `add`. A duplicate e-mail gives `IntegrityError`.
- `FoodItemRepository`: `get_all`, `get_by_id`, `get_published_items`, `add`, `update` (replaces the SERVED_AT/SUITS relationships), `delete`, `is_used_in_orders`, `get_events`, `add_event`, `get_diets`, `add_diet`. `delete` refuses an item that an order CONTAINS (`IntegrityError`), like the missing ON DELETE CASCADE today.
- `OrderRepository` (Vilde's): `get_by_id`, `get_by_user` (newest first), `find(status, from_date, to_date)` (by event date), `add` (order + CONTAINS + HAS_GROUP in one statement; unknown user, event or food item → `IntegrityError`), `update`.
- `QuestionRepository`: `get_by_id`, `get_by_order`, `get_open`, `get_all` (open first, then newest), `add`, `update`.

## 4. Tests
- `tests/conftest.py`: the `app` fixture no longer makes a temporary SQLite file. It runs `init_db()` against the local Neo4j before each test. If Neo4j isn't running, pytest stops with the message "Start Neo4j with: neo4j start".
- **Important:** `pytest` and `seed.py` both empty the local database. Run `python seed.py` after `pytest` to get the sample data back. (Neo4j Community has only one database.)
- Only tests that use SQL directly change; all other ~215 tests stay unchanged, which shows the repository interface held:
  - `test_db.py`: constraints exist, a duplicate id is refused, `init-db` works.
  - `test_food_item_repository.py`, `test_order_repository.py`: `IntegrityError` from `app.models.db`, and Cypher instead of `SELECT` in two checks.
  - `test_questions.py`, `test_question_repository.py`: `DELETE` statements become Cypher.

## 5. Seed, docs and report
- `seed.py`: no change expected (it uses `init_db()` and the repositories).
- `README.md`: install and start Neo4j (Homebrew on macOS, Neo4j Desktop on Windows), set the password, copy `.env.example` to `.env`, and the note that tests empty the database.
- `CLAUDE.md`: storage is Neo4j, the graph model diagram, and run order `neo4j start` → `seed.py` → `flask run`.
- `docs/plans/README.md`: links to the plan and the graph model.
- Report: front page "Neo4j: yes"; the graph model diagram in part 3.

## 6. Commits on `vilde`
1. Plan + graph model diagram.
2. Connection, config, `init_db`, constraints, `conftest`, `test_db` + `UserRepository`.
3. `FoodItemRepository` + its tests.
4. `OrderRepository` + its tests.
5. `QuestionRepository` + its tests.
6. README, CLAUDE.md, `.env.example`, remove `schema.sql`.

Between steps 2 and 5 the tests of repositories not yet converted fail. That is expected. Nothing is pushed until all tests pass after step 5.

## Verification
- `pytest`: all tests pass against Neo4j.
- `python seed.py`, then `flask --app app run --debug --port 5001`: test every page once as admin and as customer (menu, cart, checkout, my orders, questions, food items, picture, orders, answer).
- In the Neo4j browser (http://localhost:7474), `MATCH (n) RETURN n` shows the graph. A screenshot of it goes in the report.
