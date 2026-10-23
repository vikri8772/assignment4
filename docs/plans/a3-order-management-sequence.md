# A3 Order management – sequence diagram

How an admin lists and filters orders, opens one, and changes its order status and payment status.

````mermaid
sequenceDiagram
    actor Admin
    participant AdminController
    participant OrderRepository
    participant Order
    participant ListTemplate as admin/orders.html
    participant DetailTemplate as admin/order_detail.html

    Note over Admin,DetailTemplate: List and filter
    Admin->>AdminController: Open orders (optional filters: status, from/to event date)
    AdminController->>OrderRepository: find(status, fromDate, toDate)
    OrderRepository-->>AdminController: List of Order (sorted by event date)
    AdminController->>ListTemplate: render(orders, active filters)
    ListTemplate-->>AdminController: HTML page
    AdminController-->>Admin: Show filtered order list

    Note over Admin,DetailTemplate: Open one order
    Admin->>AdminController: Open order
    AdminController->>OrderRepository: getById(orderId)
    OrderRepository-->>AdminController: Order (with lines and guest groups)
    AdminController->>Order: allowedNextStatuses()
    Order-->>AdminController: e.g. [APPROVED, REJECTED]
    AdminController->>DetailTemplate: render(order, allowed statuses)
    AdminController-->>Admin: Show order with only valid status buttons

    Note over Admin,DetailTemplate: Change order status
    Admin->>AdminController: Choose new order status
    AdminController->>OrderRepository: getById(orderId)
    OrderRepository-->>AdminController: Order
    AdminController->>Order: changeStatus(newStatus)
    alt transition allowed (see a3-order-status-state)
        Order-->>AdminController: OK
        AdminController->>OrderRepository: update(order)
        AdminController-->>Admin: Show order with new status
    else transition not allowed
        Order-->>AdminController: InvalidTransition
        AdminController-->>Admin: Error: not allowed from current status
    end

    Note over Admin,DetailTemplate: Change payment status (separate from order status)
    Admin->>AdminController: Choose new payment status
    AdminController->>OrderRepository: getById(orderId)
    OrderRepository-->>AdminController: Order
    AdminController->>Order: changePaymentStatus(newStatus)
    alt transition allowed (see a3-payment-status-state)
        AdminController->>OrderRepository: update(order)
        AdminController-->>Admin: Show order with new payment status
    else transition not allowed
        AdminController-->>Admin: Error message
    end
````
