````mermaid
sequenceDiagram
    actor Customer
    participant AccountController
    participant OrderRepository
    participant Order
    participant ListTemplate as account/orders.html
    participant DetailTemplate as account/order_detail.html

    Customer->>AccountController: Open "My orders"
    alt not logged in
        AccountController-->>Customer: Redirect to /account/login
    else logged in
        AccountController->>OrderRepository: getByUser(userId from session)
        OrderRepository-->>AccountController: List of Order (newest first)
        AccountController->>ListTemplate: render(orders)
        ListTemplate-->>AccountController: HTML page
        AccountController-->>Customer: Show orders with event date, status,<br/>payment status and total
    end

    Customer->>AccountController: Open one order
    AccountController->>OrderRepository: getById(orderId)
    OrderRepository-->>AccountController: Order
    AccountController->>Order: belongsTo(userId from session)
    alt order belongs to customer
        AccountController->>DetailTemplate: render(order)
        AccountController-->>Customer: Show order lines, guest groups<br/>and questions (see C5)
    else not the customer's order
        AccountController-->>Customer: 404 Not found
    end
````
