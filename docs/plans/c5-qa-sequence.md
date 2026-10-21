```mermaid
sequenceDiagram
    actor Customer
    participant ShopController
    participant OrderRepository
    participant Order
    participant QuestionRepository
    participant OrderTemplate as order_detail.html

    Customer->>ShopController: Open own order
    ShopController->>OrderRepository: getById(orderId)
    OrderRepository-->>ShopController: Order
    ShopController->>Order: belongsTo(userId from session)
    Order-->>ShopController: true / false
    alt order belongs to customer
        ShopController->>QuestionRepository: getByOrder(orderId)
        QuestionRepository-->>ShopController: List of Question
        ShopController->>OrderTemplate: render(order, questions)
        OrderTemplate-->>ShopController: HTML page
        ShopController-->>Customer: Show order with questions and answers
    else not the customer's order
        ShopController-->>Customer: 404 Not found
    end

    Customer->>ShopController: Submit new question
    ShopController->>OrderRepository: getById(orderId)
    OrderRepository-->>ShopController: Order
    ShopController->>Order: belongsTo(userId from session)
    Order-->>ShopController: true / false
    alt order belongs to customer
        ShopController->>QuestionRepository: add(question)
        QuestionRepository-->>ShopController: Saved
        ShopController-->>Customer: Show order with new question (OPEN)
    else not the customer's order
        ShopController-->>Customer: 404 Not found
    end
```
