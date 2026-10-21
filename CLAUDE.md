# Ekte Mat Online

INFO212 obligatory assignment 4. A first version of the ordering system for Ekte Mat AS, a fictional catering company in Bergen. It replaces ordering by e-mail, phone and Excel.

- **Customer site:** a menu grouped by event type (C1), a cart that enforces minimum order quantities (C2), an order form with notes per guest group (C3), "My orders" (C4), and questions about an order (C5).
- **Admin panel:** food items (A1), item images with a preview before saving (A2), an order list with filters and per-order status management (A3), and answers to customer questions (A4).

Design diagrams (Mermaid) are in `docs/plans/`. Read the ones that apply before changing a feature.

## Architecture (MVC)

Flask backend with Jinja2 templates. The layers must stay visible in the folder structure:

```
app/
  models/        # domain classes + repository classes (the ONLY code that touches storage)
  controllers/   # Flask blueprints: shop, account, admin
  templates/     # Jinja2 views: shop/, account/, admin/
  static/        # CSS, JS, uploaded images
tests/
seed.py
```

- Controllers call repositories and domain classes. They never access storage directly.
- Storage is SQLite for now. Neo4j will replace it in assignment 5, so keep all storage code behind the repository classes (`FoodItemRepository`, `OrderRepository`, ...).
- Order status: submitted → approved → in preparation → delivered, or rejected/cancelled (`docs/plans/A3orders_statemachine.md`). Payment status is tracked separately from order status.

## Running and testing

<!-- Update these commands when the skeleton exists -->
```bash
python -m venv .venv
pip install -r requirements.txt
python seed.py        # synthetic food items, an admin and test customers
flask --app app run
pytest
```

## Team rules

- Each member works on their own branch and merges into `main` through a pull request. Every member must commit.
- Plan every larger feature in plan mode first, and commit the agreed plan to `docs/plans/` before building it.
- Use synthetic data only.
- Never commit secrets or API keys (including a Claude API key). Keep them in `.env`, which is in `.gitignore`.
- Add or update tests for every feature, and run `pytest` before you push.
- Keep this file short and true. Update it when the layout or commands change.
