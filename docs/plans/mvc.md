# MVC overview

All controllers, views and models in Ekte Mat Online and how they connect. Controllers only reach storage through the repository classes, so SQLite can be swapped for Neo4j in assignment 5.

````mermaid
flowchart LR
    Customer([Customer]) --> ShopController
    Customer --> AccountController
    Admin([Admin]) --> AdminController

    subgraph Controller [Controller]
        ShopController["ShopController<br/>menu, cart, checkout"]
        AccountController["AccountController<br/>login, my orders, questions"]
        AdminController["AdminController<br/>items, images, orders, answers"]
    end

    AdminCheck["Every AdminController route<br/>requires user.isAdmin()"] -.- AdminController

    subgraph View [View]
        subgraph ShopViews [templates/shop]
            shopMenu[menu.html]
            shopCart[cart.html]
            shopCheckout[checkout.html]
        end
        subgraph AccountViews [templates/account]
            accLogin[login.html]
            accOrders[orders.html]
            accOrderDetail["order_detail.html<br/>(with questions)"]
        end
        subgraph AdminViews [templates/admin]
            admItems[items_overview.html]
            admItemForm[item_form.html]
            admOrders[orders.html]
            admOrderDetail[order_detail.html]
            admQuestions[questions.html]
            admQuestionForm[question_form.html]
        end
        subgraph Static [static]
            uploads[uploads/]
        end
    end

    subgraph Model [Model]
        subgraph FoodModel [Food items]
            FoodItem
            Event
            Diet
            FoodItemRepository
        end
        subgraph OrderModel [Users and orders]
            User
            Role
            Order
            OrderLine
            GuestGroup
            UserRepository
            OrderRepository
        end
        subgraph QAModel [Questions]
            Question
            Answer
            QuestionRepository
        end
    end

    ShopController --> ShopViews
    AccountController --> AccountViews
    AdminController --> AdminViews
    AdminController --> uploads

    ShopController --> FoodModel
    ShopController --> OrderModel
    AccountController --> OrderModel
    AccountController --> QAModel
    AdminController --> FoodModel
    AdminController --> OrderModel
    AdminController --> QAModel

    FoodItemRepository --> Storage[(Database)]
    UserRepository --> Storage
    OrderRepository --> Storage
    QuestionRepository --> Storage
````
