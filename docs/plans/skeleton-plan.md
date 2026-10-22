# Code skeleton – plan

The shared foundation every feature builds on: the Flask app, the database, all domain classes and repositories, login, and the base layout. Features (C1–C5, A1–A4) are **not** part of this plan. Each one is built later on its own branch, following the same pattern.

## Decisions
- **Python naming.** The class diagrams list public attributes (no getters or setters) in camelCase. In the code we use the same attributes in snake_case (`item.min_order`) and snake_case methods for behaviour (`accepts_quantity()`, `is_admin()`, `belongs_to()`, `allowed_next_statuses()`).
- **IDs** are `uuid4().hex` strings, as in the diagrams, so they carry over unchanged to Neo4j.
- **Prices** are `Decimal` in Python and stored as TEXT in SQLite, so no rounding errors.
- **Repositories** take a database connection. Only code in `app/models/` imports `sqlite3`.
- **Secrets.** `SECRET_KEY` is read from `.env` with `python-dotenv`. `.env.example` is committed; `.env` never is.
- **Passwords** are hashed with `werkzeug.security`. Login keeps the session so the cart survives (C3), and logout clears it.

## Steps
1. Smallest Flask app: `create_app()`, one route, `base.html`.
2. Blueprints `shop`, `account`, `admin` with placeholder pages and the nav.
3. First domain class (`FoodItem`, `Event`, `Diet`) and the first pytest tests.
4. Database: `schema.sql`, `db.py`, a test fixture with a temporary database.
5. First repository: `FoodItemRepository`.
6. Users and login: `User`, `UserRepository`, `login_required`, `admin_required`, the login and register pages.
7. `seed.py` with synthetic events, diets, food items and users, `.env.example`, and run instructions in the README.

## Left for the feature owners
The skeleton covers what A1, A2 and C1 need, plus login, which every feature needs. The rest of the model is built together with the features that use it:
- **Orders** (`Order`, `OrderLine`, `GuestGroup`, the status state machines, `OrderRepository`) belong with C3, C4 and A3. All three need `Order`, so agree on who builds it first.
- **Questions** (`Question`, `Answer`, `QuestionRepository`) belong with C5 and A4.
- `FoodItemRepository.is_used_in_orders()` (needed for deleting items in A1) is added once the order tables exist.

Follow the same pattern: domain class and tests in `app/models/`, tables in `schema.sql`, a repository class, and seed data in `seed.py`.

## Verification
- `pytest` passes after every step from step 3 on.
- The app runs with `flask --app app run`. The seeded admin can open `/admin/`, a customer gets 403 there, and a new user can register.
