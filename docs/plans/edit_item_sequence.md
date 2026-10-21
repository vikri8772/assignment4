````mermaid
sequenceDiagram
    actor Admin
    participant AdminController
    participant FoodItemRepository
    participant FoodItem
    participant EditTemplate as item_form.html

    Admin->>AdminController: Open edit page
    AdminController->>FoodItemRepository: getById(id)
    FoodItemRepository-->>AdminController: FoodItem
    AdminController->>EditTemplate: render(item)
    EditTemplate-->>AdminController: Form with current values
    AdminController-->>Admin: Show unedited form

    Admin->>AdminController: Submit changes 
    AdminController->>FoodItemRepository: getById(id)
    FoodItemRepository-->>AdminController: FoodItem
    AdminController->>FoodItem: setName(), setPrice(), setMinOrder() ...
    AdminController->>FoodItemRepository: update(item)
    FoodItemRepository-->>AdminController: Saved
    AdminController-->>Admin: Show food item list with changes
````
