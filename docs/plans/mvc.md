````mermaid
flowchart LR
    Customer([Customer]) --> ShopController
    Admin([Admin]) --> AdminController

    subgraph Controller [Controller]
        ShopController
        AdminController
    end

    subgraph View [View]
        subgraph CustomerViews [Customer site]
            menu.html
        end
        subgraph AdminViews [Admin panel]
            items_overview.html
            item_form.html
        end
    end

    subgraph Model [Model]
        FoodItem
        Event
        Diet
        FoodItemRepository
    end

    ShopController --> CustomerViews
    AdminController --> AdminViews
    ShopController --> Model
    AdminController --> Model
    FoodItemRepository --> Storage[(Database)]
````
