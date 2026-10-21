# A4 + C5 Questions – class diagram

```mermaid
classDiagram
    class Question {
        -questionId: String
        -text: String
        -askedAt: DateTime
        -status: QuestionStatus
        +getId() String
        +getText() String
        +getAskedAt() DateTime
        +getStatus() QuestionStatus
        +getAnswer() Answer
        +isAnswered() Boolean
        +answer(String text, Administrator admin)
    }

    class Answer {
        -text: String
        -answeredAt: DateTime
        +getText() String
        +getAnsweredAt() DateTime
    }

    class QuestionStatus {
        <<enumeration>>
        OPEN
        ANSWERED
    }

    class QuestionRepository {
        +getById(String id) Question
        +getByOrder(String orderId) List~Question~
        +getOpen() List~Question~
        +getAll() List~Question~
        +add(Question question)
        +update(Question question)
    }

    class Order
    class Customer
    class Administrator

    Customer "1" -- "0..*" Question : asks
    Order "1" -- "0..*" Question : is about
    Question "1" *-- "0..1" Answer : has
    Administrator "1" -- "0..*" Answer : writes
    Question --> QuestionStatus : has
    QuestionRepository ..> Question : stores

    note for Question "A question always belongs to one order.\nCustomers can only ask about their own orders."
```