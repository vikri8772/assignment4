```mermaid
classDiagram
    direction TB

    class Customer {
        +String customerId
        +String name
        +String email
    }

    class Administrator {
        +String administratorId
        +String name
    }

    class AuthenticationService {
        +register(String name, String email, String password)
        +login(String email, String password)
    }

    class Order {
        +String orderId
        +DateTime submittedAt
        +Date eventDate
        +int numberOfGuests
        +String deliveryAddress
        +OrderStatus orderStatus
        +PaymentStatus paymentStatus
        +calculateTotal() Decimal
        +updateOrderStatus(OrderStatus status)
        +updatePaymentStatus(PaymentStatus status)
    }

    class GuestGroup {
        +String groupId
        +String groupName
        +int numberOfGuests
        +String allergyNotes
        +String dietaryNotes
    }

    class OrderItem {
        +String itemName
        +int quantity
        +Decimal unitPrice
        +calculateSubtotal() Decimal
    }

    class OrderService {
        +submitOrder(Order order) Order
        +getOrders(OrderStatus status, Date eventDate) Order[]
        +getCustomerOrders(String customerId) Order[]
        +getOrder(String orderId) Order
    }

    class OrderStatus {
        <<enumeration>>
        SUBMITTED
        APPROVED
        IN_PREPARATION
        DELIVERED
        REJECTED
        CANCELLED
    }

    class PaymentStatus {
        <<enumeration>>
        NOT_PAID
        DEPOSIT_PAID
        INVOICED
        PAID
    }

    Customer "1" -- "0..*" Order : places
    Customer ..> AuthenticationService : registers or logs in
    Customer ..> OrderService : submits and views own orders
    Administrator ..> OrderService : lists and filters all orders
    Administrator ..> Order : manages statuses
    OrderService ..> Order : submits and retrieves
    Order "1" *-- "1..*" OrderItem : contains
    Order "1" *-- "1..*" GuestGroup : groups guests
    Order --> OrderStatus : has
    Order --> PaymentStatus : has

    note for GuestGroup "Record allergies and dietary requirements per group.\nGroup guest counts must sum to the order guest count."
    note for OrderService "Login is required before submission.\nValidate event date, guest count and delivery address.\nCustomers may access only their own orders.\nStatus and event-date filters are optional."
    note for Order "Order and payment statuses are independent.\nPayment status is tracked manually; no payment processing."
    ```
