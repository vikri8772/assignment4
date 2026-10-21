# A3 Orders – state machine

```mermaid
stateDiagram-v2
    %% Delivery / order status
    state "In preparation" as InPreparation

    [*] --> Submitted
    Submitted --> Approved: Approve order
    Submitted --> Rejected: Reject order
    Approved --> InPreparation: Start preparation
    Approved --> Cancelled: Cancel order
    InPreparation --> Delivered: Deliver order
    InPreparation --> Cancelled: Cancel order

    Rejected --> [*]
    Cancelled --> [*]
    Delivered --> [*]
```
