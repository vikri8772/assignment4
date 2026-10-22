# A1 Edit food item – sequence diagram

How an admin opens an existing food item, changes it and saves it. Creating, publishing and deleting items are in `a1-manage-items-sequence.md`.

````mermaid
sequenceDiagram
    actor Admin
    participant AdminController
    participant FoodItemRepository
    participant FoodItem
    participant EditTemplate as admin/item_form.html

    Admin->>AdminController: Open edit page
    AdminController->>FoodItemRepository: getById(id)
    alt item found
        FoodItemRepository-->>AdminController: FoodItem
        AdminController->>EditTemplate: render(item)
        EditTemplate-->>AdminController: Form with current values
        AdminController-->>Admin: Show unedited form
    else item not found
        FoodItemRepository-->>AdminController: None
        AdminController-->>Admin: 404 Not found
    end

    Admin->>AdminController: Submit changes
    AdminController->>AdminController: validate input
    Note right of AdminController: name required, price > 0,<br/>minOrder ≥ 1, at least one event
    alt input valid
        AdminController->>FoodItemRepository: getById(id)
        FoodItemRepository-->>AdminController: FoodItem
        AdminController->>FoodItem: setName(), setPrice(), setMinOrder() ...
        AdminController->>FoodItemRepository: update(item)
        FoodItemRepository-->>AdminController: Saved
        AdminController-->>Admin: Show food item list with changes
    else input invalid
        AdminController->>EditTemplate: render(item, errors)
        AdminController-->>Admin: Show form with error messages
    end
````
