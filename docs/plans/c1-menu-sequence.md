# C1 Menu – sequence diagram

How the customer sees the published food items grouped by event type.

````mermaid
sequenceDiagram
    actor Customer
    participant ShopController
    participant FoodItemRepository
    participant MenuTemplate as shop/menu.html

    Customer->>ShopController: Open menu page
    Note right of ShopController: Events are a fixed list created by seed.py<br/>(Event in domain-food-class)
    loop For each Event
        ShopController->>FoodItemRepository: getPublishedItems(event)
        FoodItemRepository-->>ShopController: List of FoodItem
    end
    ShopController->>MenuTemplate: render(items grouped by event)
    MenuTemplate-->>ShopController: HTML page
    ShopController-->>Customer: Show food cards grouped by event
````
