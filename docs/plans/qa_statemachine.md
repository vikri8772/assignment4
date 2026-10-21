```mermaid
stateDiagram-v2
    [*] --> Open: Customer asks question
    Open --> Answered: Admin answers
    Answered --> [*]
```