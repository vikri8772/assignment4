# A1 Food items, A2 Item images, C1 Menu – plan

## Context
Maja builds A1 (admin manages food items), A2 (admin uploads a picture per item, with a preview) and C1 (customers see the menu grouped by event). This is the upload option of A2, with no AI image generation. The skeleton on `main` already has `FoodItem`, `Event`, `Diet`, `FoodItemRepository`, login with `admin_required`, and seed data. So these features are mostly controllers and templates. Branch: `maja`.

Design: `a1-manage-items-sequence.md`, `a1-edit-item-sequence.md`, `a2-item-image-sequence.md`, `c1-menu-sequence.md`, `domain-food-class.md`.

## Decisions
- **Allergens are a fixed checklist**: the 14 allergens that EU law requires to be labelled. They are an `ALLERGENS` list in `app/models/food.py`, so the form, the validation and the menu all use the same list. The seed's `"shellfish"` becomes `"crustaceans"` so it matches the list.
- **Diets and events** are checklists too, from `get_diets()` and `get_events()`.
- **Delete waits for orders.** An item that is in an order must not be deleted. Vilde's branch adds the order tables, and her plan leaves `is_used_in_orders()` to the A1 owner. Delete is built last (step 5), after her PR is merged into `main`. Until then the admin can unpublish an item to hide it.
- **New items start unpublished** (as in the diagram). Publish and Unpublish are buttons in the item list, not a field in the form.
- **Validation lives in the admin controller**, as in the diagrams: name required, price > 0 (at most 2 decimals), minimum order from 1 to `MAX_QUANTITY`, at least one event. Errors are shown in the form, and what the admin typed is kept.
- **Images** go into `app/static/uploads/` with a generated unique name. Only jpg/png, at most 5 MB. JavaScript checks this first for the preview, and the controller checks it again. `picture_path` stores the path relative to `static/` (e.g. `uploads/3f2a….png`). Uploaded files are not committed (already in `.gitignore`), so seeded items show a placeholder until someone uploads a picture.
- **Upload folder is a config setting** (`UPLOAD_FOLDER`), so tests save files in a temporary folder instead of the real one.
- **No changes to `schema.sql`**. The tables already have everything needed.
- **Avoiding merge conflicts with Vilde.** Her branch also changes `admin.py`, `base.html`, `style.css` and `seed.py`. We keep our admin routes in a "food items" part at the top of `admin.py` and add our CSS at the end of `style.css`. Whoever merges second fixes the small conflicts.

## Steps (pause and commit after each one)
1. **C1 Menu.** `shop.menu()` gets the events and, for each one, the published items (`get_published_items(event)`, as in the diagram). Events with no items are skipped. `shop/menu.html` shows a heading per event with a row of cards: picture (or placeholder), name, description, price in NOK, minimum order, allergens and diet labels, plus links at the top to jump to each event. CSS for the cards.
   *Check it:* `/` shows the seeded items under each event, and Hjortegryte (unpublished) is missing.
2. **A1 Item list + publish/unpublish.** `admin/items_overview.html` shows all items in a table (name, price, minimum order, events, published yes/no) with Edit and Publish/Unpublish buttons, plus a "New item" link. POST routes `/admin/items/<id>/publish` and `/unpublish` use `FoodItem.publish()` / `unpublish()` and `update()`, and return 404 for an unknown id.
   *Check it:* publish Hjortegryte, and it appears on the menu.
3. **A1 Create and edit.** One template, `admin/item_form.html`, for both: text fields plus checklists for events, diets and allergens. Routes `/admin/items/new` and `/admin/items/<id>/edit` (GET shows the form, POST validates and saves). A helper in `admin.py` reads and validates the form, so the two routes share the rules.
   *Check it:* create an item with a missing name or price 0 and see the errors; edit an item's price and see it on the menu.
4. **A2 Image upload with preview.** A file field in `item_form.html`, and `static/js/image_preview.js` shows the chosen picture next to the current one, or an error if it's the wrong type or too big. A "Remove" button resets the choice. On Save, the controller checks the file again, saves it with a unique name and sets `picture_path`. `MAX_CONTENT_LENGTH` stops huge uploads.
   *Check it:* upload a picture, see the preview, save, and see it in the admin list and on the menu card.
5. **A1 Delete (after Vilde's orders are in `main`).** Merge `main` into `maja`. Add `FoodItemRepository.is_used_in_orders(id)` and a POST route `/admin/items/<id>/delete` with a confirm step in the browser. If the item is in an order, show "Item is used in orders – unpublish it instead".
   *Check it:* delete a new item; try to delete an ordered item and get the message.
6. **Wrap up.** Run `pytest`, push, and open a PR to `main`.

## Files
- `app/models/food.py`: `ALLERGENS` list.
- `app/__init__.py`: `UPLOAD_FOLDER` and `MAX_CONTENT_LENGTH` config.
- `app/controllers/shop.py`, `app/controllers/admin.py`.
- `app/templates/shop/menu.html`, `app/templates/admin/items_overview.html`, `app/templates/admin/item_form.html` (new).
- `app/static/js/image_preview.js` (new), `app/static/css/style.css`.
- `seed.py`: `"shellfish"` → `"crustaceans"`.
- Step 5: `app/models/food_item_repository.py`.

Reused: `FoodItemRepository` (`get_all`, `get_by_id`, `get_published_items`, `get_events`, `get_diets`, `add`, `update`), `FoodItem.publish()/unpublish()`, `MAX_QUANTITY`, `admin_required`, `get_db()`, flash messages in `base.html`, the `.form` CSS.

## Tests
- `tests/test_menu.py`: published items are shown under the right events, unpublished items are hidden, events without items are skipped.
- `tests/test_admin_items.py`: customers get 403; list shows all items; publish/unpublish; create and edit with valid input; each validation rule gives an error; unknown id gives 404.
- `tests/test_admin_images.py`: a small PNG is saved in the temporary upload folder and `picture_path` is set; a wrong file type is rejected; editing without a new file keeps the old picture.
- Step 5: `is_used_in_orders` and delete, in the repository and admin tests.
- `tests/test_domain_food.py`: seed allergens are all in `ALLERGENS`.

## Verification
- `pytest` passes after every step.
- `python seed.py`, then `flask --app app run --debug`: check each step's *Check it* in the browser, logged in as `admin@ektemat.test`. Take screenshots of the menu, item list, item form and image preview for the report.
