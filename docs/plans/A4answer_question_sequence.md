```mermaid
sequenceDiagram
    actor Admin
    participant AdminController
    participant QuestionRepository
    participant Question
    participant ListTemplate as questions.html
    participant FormTemplate as question_form.html

    Admin->>AdminController: Open questions list
    AdminController->>QuestionRepository: getAll()
    QuestionRepository-->>AdminController: List of Question
    AdminController->>ListTemplate: render(questions)
    ListTemplate-->>AdminController: HTML page
    AdminController-->>Admin: Show questions (open first)

    Admin->>AdminController: Open one question
    AdminController->>QuestionRepository: getById(id)
    QuestionRepository-->>AdminController: Question
    AdminController->>FormTemplate: render(question)
    FormTemplate-->>AdminController: Answer form
    AdminController-->>Admin: Show question and answer form

    Admin->>AdminController: Submit answer
    AdminController->>QuestionRepository: getById(id)
    QuestionRepository-->>AdminController: Question
    AdminController->>Question: answer(text, admin)
    AdminController->>QuestionRepository: update(question)
    QuestionRepository-->>AdminController: Saved
    AdminController-->>Admin: Show questions list (now ANSWERED)
```