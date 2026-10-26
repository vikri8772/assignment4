# C2 Cart and C3 Checkout – plan

## Context
Torben builds C2 (cart with minimum quantities) and C3 (order form with notes per guest group) on branch `Torben`, which is up to date with `main`.
- **C2 hasn't been built yet.** The menu only has a placeholder (`{# C2 adds an "Add to cart" button here. #}`). The cart follows `c2-cart-activity.md`: add, change and remove items, with each item's minimum quantity and the 10,000 maximum checked.
- **C3** follows `c3-order-form-activity.md` and `c3-checkout-sequence.md`. `OrderRepository.add()` (Vilde's) already saves an order, its lines and its guest groups in one transaction, so C3 needs no new storage code.
- **C4 My orders is already built** by Vilde and isn't changed. C3 uses its order page (`account.my_order_detail`) as the order confirmation.

Design: `c2-cart-activity.md`, `c3-order-form-activity.md`, `c3-checkout-sequence.md`, `c4-my-orders-sequence.md`, `domain-orders-class.md`. The plan is saved as `docs/plans/c2-c3-checkout-plan.md` and linked from `docs/plans/README.md` before any code is written (team rule).

## 1. Cart domain class – `app/models/cart.py` (new)
- `Cart`: wraps a dict `{food_item_id: quantity}`, so it fits in the Flask session. `Cart.from_dict(d)` / `to_dict()`.
- `set_quantity(item: FoodItem, qty)`: 0 removes the item; otherwise it uses the existing `FoodItem.accepts_quantity()` (min_order..MAX_QUANTITY in `app/models/food.py`) and raises `ValueError` with a readable message.
- `is_empty()`, `item_ids()`.
- `to_order_lines(items)`: turns the cart into `OrderLine`s, copying name and price from the current `FoodItem`s.
- Cart has no storage of its own; the controller keeps `cart.to_dict()` in `session["cart"]`. The login already keeps the session (comment in `account.login`), so the cart survives login, as C3 requires.

## 2. Order validation – `app/models/order.py`
- `Order.problems(today) -> list[str]`, using the rules in `c3-checkout-sequence.md`: event date not in the past, guests 1–10,000, delivery address 5–200 characters, at least one order line, at least one guest group, every group has a name and ≥1 guest, and the group sizes add up to `number_of_guests`. `today` is a parameter so the tests don't depend on the date.
- Add `problems()` to `domain-orders-class.md` and `Cart` to `domain-food-class.md` (or the orders diagram), so the diagrams match the code.

## 3. Controller – `app/controllers/shop.py`
- `POST /cart/add` (`item_id`, `quantity`): the item must exist and be published. Invalid quantity → flash the error. Redirect to the cart.
- `GET /cart`: the cart lines with subtotals and a total; quantity fields to change the quantity (0 removes) via `POST /cart/update`; a "Go to checkout" button. Items that were unpublished or deleted since they were added are dropped with a flash message.
- `GET /checkout` (`@login_required`): admins are sent to `admin.orders` (as `my_orders` does). An empty cart → flash and redirect to the cart. Otherwise renders `shop/checkout.html`: cart summary, an event type dropdown (`FoodItemRepository.get_events()`), event date, number of guests, delivery address, and 5 guest group rows (name, guests, allergy notes, dietary notes). Empty rows are ignored, so there's no JavaScript.
- `POST /checkout`: reads the form into an `Order` (unknown event or non-numbers become error messages, not 500), then `order.problems(date.today())`. If there are problems, re-render the form with the values and the errors (400). Otherwise `OrderRepository.add(order)`, empty the cart, flash "Thank you, your order is submitted", and redirect to `account.my_order_detail` (C4) — this is the order confirmation.

## 4. Templates and styles
- `shop/menu.html`: replace the C2 placeholder with a small form (quantity starting at `min_order`, "Add to cart").
- `shop/cart.html`, `shop/checkout.html` (new), in the style of the existing `table.orders` and `.form`.
- `base.html`: a "Cart (n)" link for everyone who isn't an admin.
- `style.css`: only small additions if needed.

## 5. Tests
- `tests/test_cart.py`: `Cart` domain (below minimum, above 10,000, 0 removes, order lines with price), and the routes: add, change, remove, an unpublished item is refused.
- `tests/test_domain_order.py`: each rule in `problems()`, plus a valid order with no problems.
- `tests/test_checkout.py`: logged-out → redirect to login and the cart is still there after logging in; empty cart → back to the cart; invalid form → 400 with messages and nothing saved; valid form → order saved with lines and groups, the cart is emptied, redirect to the C4 page, and the order is in `/account/orders` (C4); an admin is sent to the admin orders.

## 6. Commits on `Torben` (one per step, `pytest` green each time; commit only when Torben says so)
1. Plan doc + README link.
2. Cart class + `Order.problems()` + domain tests + diagram updates.
3. Cart pages + menu button + tests.
4. Checkout + confirmation to My orders + tests.
Then push `Torben` and open a PR to `main` only when Torben asks.

## Verification
- `pytest` passes (new and existing tests).
- `python seed.py`, `flask --app app run --debug`, then in the browser: as a logged-out visitor, add items (try one below the minimum), open the cart, change and remove an item, go to checkout → login as `kari@example.test` → the cart is kept → submit with errors (date in the past, group sizes don't add up) → fix → confirmation page in My orders → the order is listed in My orders and in the admin Orders list.
