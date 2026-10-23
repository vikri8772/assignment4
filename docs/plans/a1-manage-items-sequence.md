# A1 Manage food items – sequence diagram

How an admin creates, publishes/unpublishes and deletes food items. Editing an item is in `a1-edit-item-sequence.md`.

````mermaid
sequenceDiagram
    actor Admin
    participant AdminController
    participant FoodItemRepository
    participant FoodItem
    participant ListTemplate as admin/items_overview.html
    participant FormTemplate as admin/item_form.html

    Note over Admin,FormTemplate: Create a new food item
    Admin->>AdminController: Open "New item"
    AdminController->>FormTemplate: render(empty form, events, diets)
    FormTemplate-->>AdminController: HTML page
    AdminController-->>Admin: Show empty form

    Admin->>AdminController: Submit new item
    AdminController->>AdminController: validate input
    Note right of AdminController: name required, price > 0,<br/>minOrder ≥ 1, at least one event
    alt input valid
        AdminController->>FoodItem: new FoodItem(name, desc, price, minOrder, ...)
        AdminController->>FoodItemRepository: add(item)
        FoodItemRepository-->>AdminController: Saved (unpublished)
        AdminController-->>Admin: Show item list with new item
    else input invalid
        AdminController->>FormTemplate: render(form, errors)
        AdminController-->>Admin: Show form with error messages
    end

    Note over Admin,FormTemplate: Publish / unpublish
    Admin->>AdminController: Click publish or unpublish
    AdminController->>FoodItemRepository: getById(id)
    alt item found
        FoodItemRepository-->>AdminController: FoodItem
        AdminController->>FoodItem: publish() / unpublish()
        AdminController->>FoodItemRepository: update(item)
        FoodItemRepository-->>AdminController: Saved
        AdminController-->>Admin: Show item list with new status
    else item not found
        FoodItemRepository-->>AdminController: None
        AdminController-->>Admin: 404 Not found
    end

    Note over Admin,FormTemplate: Delete
    Admin->>AdminController: Click delete and confirm
    AdminController->>FoodItemRepository: isUsedInOrders(id)
    alt not used in any order
        AdminController->>FoodItemRepository: delete(id)
        AdminController-->>Admin: Show item list without item
    else used in orders
        AdminController-->>Admin: Error: item is used in orders, unpublish it instead
    end
````
