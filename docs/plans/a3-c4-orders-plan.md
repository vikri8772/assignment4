# A3 Orders (admin) and C4 My orders – plan

## Context
Vilde is responsible for A3 (admin order list, filters, order and payment status) and C4 (a customer's own orders). The skeleton on `main` has food items, users and login, but no orders yet. `docs/plans/skeleton-plan.md` leaves `Order` to the C3, C4 and A3 owners. Vilde builds it first, on branch `vilde`. C3 can then reuse `OrderRepository.add()` to save new orders.

The design is already in `docs/plans/`: `domain-orders-class.md`, `a3-order-management-sequence.md`, `a3-order-status-state.md`, `a3-payment-status-state.md` and `c4-my-orders-sequence.md`. The code follows those diagrams and the existing patterns: snake_case, `uuid4().hex` IDs, `Decimal` prices stored as TEXT, and only repositories touch SQLite.

This plan is committed as `docs/plans/a3-c4-orders-plan.md` before any code (team rule), and linked from `docs/plans/README.md`.

## 1. Domain model – `app/models/order.py` (new)
- `OrderStatus` enum: SUBMITTED, APPROVED, IN_PREPARATION, DELIVERED, REJECTED, CANCELLED, with a `label` for display (e.g. "In preparation").
- `PaymentStatus` enum: NOT_PAID, DEPOSIT_PAID, INVOICED, PAID, with `label`.
- Transition tables, copied from the two state diagrams:
  - Order: SUBMITTED → APPROVED/REJECTED; APPROVED → IN_PREPARATION/CANCELLED; IN_PREPARATION → DELIVERED/CANCELLED; the rest are final.
  - Payment: NOT_PAID → DEPOSIT_PAID/INVOICED; DEPOSIT_PAID → INVOICED; INVOICED → PAID; PAID is final.
- `InvalidTransition(Exception)`.
- `GuestGroup` dataclass: `group_name`, `number_of_guests`, `allergy_notes`, `dietary_notes`. Allergies are stored per group, not per named guest (GDPR note).
- `OrderLine` dataclass: `food_item_id`, `item_name`, `quantity`, `unit_price: Decimal`, plus `subtotal()`.
- `Order` dataclass: `user_id`, `event: Event`, `event_date: date`, `number_of_guests`, `delivery_address`, `lines`, `guest_groups`, `order_status=SUBMITTED`, `payment_status=NOT_PAID`, `created_at: datetime`, `id`.
  - Methods: `belongs_to(user_id)`, `total()`, `allowed_next_statuses()`, `change_status(new)`, `allowed_next_payment_statuses()`, `change_payment_status(new)`. The two `change_*` methods raise `InvalidTransition`.
- Update `domain-orders-class.md`: add `userId`, `event` and `allowedNextPaymentStatuses()`, so the diagram still matches the code.

## 2. Storage – `app/models/schema.sql` and `app/models/order_repository.py` (new)
- Tables. `"order"` is an SQL keyword, so the table is `orders`. The new tables are dropped at the top of the file, before `food_item`/`users`, because of the foreign keys.
  - `orders`: id, user_id → users, event_name → event, event_date TEXT (ISO), number_of_guests, delivery_address, created_at TEXT (ISO), order_status, payment_status.
  - `order_line`: order_id → orders ON DELETE CASCADE, position, food_item_id → food_item (no cascade, so an ordered item can't be deleted), item_name, quantity, unit_price TEXT.
  - `guest_group`: order_id → orders ON DELETE CASCADE, position, group_name, number_of_guests, allergy_notes, dietary_notes.
- `OrderRepository(db)`, in the same style as `FoodItemRepository` (`with self.db:` transactions, a `_to_order(row)` helper):
  - `get_by_id(id)`: an Order with its lines and groups, or None.
  - `get_by_user(user_id)`: newest first (C4).
  - `find(status=None, from_date=None, to_date=None)`: sorted by event date (A3). Each filter is optional.
  - `add(order)`: order, lines and groups in one transaction (C3 will use this).
  - `update(order)`: saves the header fields, including both statuses.
- `FoodItemRepository.is_used_in_orders()` is left to the A1 owner. Now that the tables exist, it is a one-line query.

## 3. A3 Admin – `app/controllers/admin.py`
All routes use `@admin_required`.
- `GET /admin/orders`: query parameters `status`, `from`, `to`. A filter value that isn't valid is ignored and shown with a flash message, not turned into a 500 error. Renders `admin/orders.html`: a filter form, plus a table with event date, customer, event, guests, status, payment status and total, each row linking to its order.
- `GET /admin/orders/<id>`: renders `admin/order_detail.html` with the customer (`UserRepository.get_by_id`), lines, guest groups with allergies highlighted, and the total. There is one button per allowed next order status and per allowed next payment status, so invalid choices are never offered. 404 if the order doesn't exist.
- `POST /admin/orders/<id>/status` and `POST /admin/orders/<id>/payment`: read the order, call `change_status` / `change_payment_status` and `update`, flash the result and redirect back (Post/Redirect/Get). On `InvalidTransition` or an unknown value: flash an error and return 400; nothing is saved.
- Nav in `base.html`: admins get an "Orders" link.

## 4. C4 My orders – `app/controllers/account.py`
Both routes use `@login_required`.
- `GET /account/orders`: `get_by_user(g.user.id)` → `account/orders.html`, a table with event date, event, guests, status, payment status, total and a link per order, plus an empty-state message.
- `GET /account/orders/<id>`: 404 if the order is missing or `not order.belongs_to(g.user.id)`. It's the same 404 in both cases, so nobody can probe other customers' order IDs. Renders `account/order_detail.html` with lines, guest groups, statuses, total and an empty "Questions" section with a comment for C5.
- Nav: logged-in users get a "My orders" link.

## 5. Seed data and styles
- `seed.py`: an `ORDERS` list with about 5 synthetic orders for Kari and Ola. They cover several order statuses (submitted, approved, in preparation, delivered, cancelled) and payment statuses, and different event dates. Prices are taken from the seeded food items. This makes A3 and C4 testable without C3.
- `style.css`: a small table style, status badges and a highlight for allergy notes.

## 6. Tests (new files in `tests/`)
- `test_domain_order.py`: `total()`, `belongs_to()`, every allowed transition for both machines, and that disallowed transitions (e.g. DELIVERED → SUBMITTED, PAID → NOT_PAID) raise `InvalidTransition`.
- `test_order_repository.py`: add/get round-trip including lines and groups, `get_by_user` newest first and only that user's orders, `find` with each filter and all combined, `update` saves statuses, and an unknown ID returns None.
- `test_admin_orders.py`: a customer gets 403 and a logged-out visitor is redirected; the list filters by status and date; the detail page shows only valid buttons; a valid status change is saved; an invalid one gives 400 and leaves the order unchanged; payment status is changed; an unknown order gives 404.
- `test_my_orders.py`: login is required, a customer sees only their own orders, the other customer's order gives 404, and the detail page shows lines, guest groups and statuses.
- `test_seed.py`: also checks that the orders are created.

## 7. Commits on branch `vilde` (one per step, `pytest` green each time)
1. Plan doc + README link.
2. Order domain class + tests + class diagram update.
3. Tables + OrderRepository + tests.
4. Seed orders.
5. A3 admin pages + tests.
6. C4 my orders pages + tests.
Then push `vilde` and open a pull request to `main` (only after Vilde says so).

## Verification
- `pytest` passes, both the new tests and all existing ones.
- `python seed.py`, then `flask --app app run --debug`:
  - As `admin@ektemat.test`, open Orders, filter by status and dates, open an order, move it Submitted → Approved → In preparation → Delivered, and set payment Not paid → Invoiced → Paid. Only valid buttons are shown.
  - As `kari@example.test`, open My orders and see only Kari's orders with the new status. Opening one of Ola's order URLs gives 404.
- Screenshots of the order list, order page and My orders for the report (section 2).
