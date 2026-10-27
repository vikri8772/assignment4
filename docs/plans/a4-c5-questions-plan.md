# A4 Answer questions and C5 Questions about an order – plan

## Context
Pablo builds C5 (a customer asks questions about their own order and sees the answers) and A4 (an admin sees all questions and answers each one once) on branch `pablo`, which is up to date with `main`. `skeleton-plan.md` leaves `Question`, `Answer` and `QuestionRepository` to the C5 and A4 owners, so they are built here.
- **C4 is already built** (Vilde). `account/order_detail.html` has a placeholder under "Questions" for C5, and `account.my_order_detail` already gives the same 404 for a missing order and someone else's order. C5 reuses that check.
- **Orders exist** (`orders` table, `OrderRepository`, seed orders), so questions can point to real orders right away.

Design: `domain-qa-class.md`, `c5-qa-sequence.md`, `a4-answer-question-sequence.md`, `c5-question-status-state.md`. The code follows those diagrams and the existing patterns: snake_case, `uuid4().hex` IDs, datetimes stored as ISO TEXT, and only repositories touch SQLite. The plan is saved as `docs/plans/a4-c5-questions-plan.md` and linked from `docs/plans/README.md` before any code is written (team rule).

## 1. Domain model – `app/models/question.py` (new)
- `QuestionStatus` enum: OPEN, ANSWERED, with a `label` ("Open", "Answered"), like `OrderStatus`.
- `MAX_TEXT_LENGTH = 1000`, used for both questions and answers (like `MAX_GUESTS` in `order.py`).
- `AlreadyAnswered(Exception)`: a question can only be answered once (`c5-question-status-state.md`).
- `Answer` dataclass: `text`, `answered_by` (the admin's user id), `answered_at: datetime`.
- `Question` dataclass: `order_id`, `asked_by` (the customer's user id), `text`, `asked_at: datetime` (now, without microseconds, as in `Order`), `status=OPEN`, `given_answer: Answer | None = None`, `id`.
  - The attribute can't be called `answer`, because that is the method's name. It is `given_answer` in the code and `givenAnswer` in the diagram.
  - `is_answered()`: `status == ANSWERED`.
  - `answer(text, admin: User)`: raises `AlreadyAnswered` if already answered; otherwise sets `given_answer = Answer(text, admin.id, now)` and `status = ANSWERED`. Text checks (empty, too long) are done in the controller, as for the order form.

## 2. Storage – `app/models/schema.sql` and `app/models/question_repository.py` (new)
- Table `question`, dropped **first** in the DROP list, because it points to `orders` and `users`. The comment "Questions get their tables when that feature is built" at the top is removed.
  - `id` TEXT PRIMARY KEY, `order_id` → orders ON DELETE CASCADE, `asked_by` → users, `text`, `asked_at` TEXT (ISO), `status` TEXT ('OPEN'/'ANSWERED'), and nullable `answer_text`, `answered_by` → users, `answered_at` TEXT. The three answer columns are NULL while the question is open. The answer is stored in the same row because a question has 0..1 answers.
- `QuestionRepository(db)`, in the same style as `OrderRepository` (`with self.db:` transactions, a `_to_question(row)` helper that builds the `Answer` when `answer_text` is not NULL):
  - `get_by_id(id)`: a Question, or None.
  - `get_by_order(order_id)`: oldest first, so it reads like a conversation (C5).
  - `get_open()`: only OPEN questions, oldest first (the one waiting longest on top).
  - `get_all()`: open first, then newest first (A4): `ORDER BY status = 'ANSWERED', asked_at DESC`.
  - `add(question)` and `update(question)` (saves status and the answer columns).

## 3. C5 Questions on my order – `app/controllers/account.py`
Both routes use `@login_required`. See `c5-qa-sequence.md`.
- A helper `_get_own_order_or_404(order_id)` with the existing check (`order is None or not order.belongs_to(g.user.id)` → 404), used by both routes, so `my_order_detail` and the new route share one rule.
- `GET /account/orders/<order_id>` (`my_order_detail`): also passes `questions=QuestionRepository(get_db()).get_by_order(order.id)`.
- `POST /account/orders/<order_id>/questions` (`ask_question`): 404 as above, before anything is saved. The text is stripped; empty or longer than 1000 characters → flash the error and re-render the order page with the typed text and status 400; nothing is saved. Otherwise `add(Question(order.id, g.user.id, text))`, flash "Your question is sent. We will answer it here.", and redirect to `my_order_detail` (Post/Redirect/Get).

## 4. A4 Answer questions – `app/controllers/admin.py`
All routes use `@admin_required`. See `a4-answer-question-sequence.md`.
- `GET /admin/questions` (`questions`): `get_all()` → `admin/questions.html`, a table with status badge, asked at, customer, order (event and date, linking to `admin.order_detail`), the start of the question, and a link to answer/view it. Customer names come from a dict like `_customers_for`, and orders from `OrderRepository.get_by_id`. Empty-state message when there are no questions.
- `GET /admin/questions/<question_id>` (`question_detail`): → `admin/question_form.html` with the question, the customer, a link to the order, and either the answer form (if OPEN) or the saved answer (if ANSWERED). 404 if the question doesn't exist.
- `POST /admin/questions/<question_id>/answer` (`answer_question`): 404 if missing. If `is_answered()` (or `answer()` raises `AlreadyAnswered`) → flash "This question is already answered." and re-render with status 400; the old answer is kept. Empty or too long text → flash and re-render with the typed text and 400. Otherwise `question.answer(text, g.user)`, `update`, flash, and redirect to `admin.questions` (as in the sequence diagram).
- Helper `_get_question_or_404(question_id)`, like `_get_order_or_404`.

## 5. Templates and styles
- `account/_questions.html` (new), included from `account/order_detail.html` in place of the C5 placeholder: each question with its date and status badge, and the answer under it (or "Not answered yet"), then a form with a `<textarea name="text" maxlength="1000" required>` and an "Ask a question" button, posting to `account.ask_question`. It needs `order`, `questions` and an optional `question_text` (kept after an error).
- `admin/questions.html` and `admin/question_form.html` (new), in the style of `admin/orders.html` and `admin/order_detail.html` (`table.orders`, `.order-facts`).
- `base.html`: a "Questions" link in the admin nav, after "Orders".
- `style.css`: badges `.question-open` and `.question-answered`, and a small style for the answer block.
- Note: `test_order_page_has_no_admin_buttons` in `tests/test_my_orders.py` asserts there is no `<button` on the customer's order page. The "Ask a question" button breaks it, so that test is changed to check there are no status-change forms (`/admin/` in the page) instead.

## 6. Seed data – `seed.py`
- A `QUESTIONS` list with 3 synthetic questions on the seeded orders, referring to orders by their index in `ORDERS`:
  - Kari, wedding order: "Can the cake for the children be made without milk?" – open.
  - Kari, julebord order: "Can we get the food delivered at 17:00 instead of 18:00?" – answered by the admin.
  - Ola, conference order: "Is the wrap for the speaker with sesame allergy packed separately?" – open.
- Answered questions use `Question.answer(text, admin)` and then set a fixed `answered_at`, so the seed stays deterministic. The print line also counts questions.
- `test_seed.py`: checks that the questions are created and that 1 of them is answered.

## 7. Tests (new files in `tests/`)
- `test_domain_question.py`: a new question is OPEN and not answered; `answer()` sets the answer, admin id, time and ANSWERED; answering twice raises `AlreadyAnswered` and keeps the first answer; `QuestionStatus.label`.
- `test_question_repository.py`: add/get round-trip for open and answered questions; `get_by_order` only returns that order's questions, oldest first; `get_open` skips answered ones; `get_all` puts open first, then newest; `update` saves the answer; an unknown ID returns None; deleting an order deletes its questions (ON DELETE CASCADE).
- `test_questions.py` (routes):
  - C5: login is required (redirect to login); the order page shows the questions and answers; asking a question saves it as OPEN and redirects; empty text and 1001 characters give 400 and save nothing; asking on someone else's order and on an unknown order gives 404 and saves nothing; the other customer's questions are not shown.
  - A4: a customer gets 403 and a logged-out visitor is redirected on all three routes; the list shows open questions before answered ones; the detail page shows the form for an open question; answering saves the answer and redirects to the list; answering an answered question gives 400 and keeps the first answer; empty answer gives 400; unknown question gives 404; the customer sees the answer on their order page afterwards; admins get the "Questions" nav link.

## 8. Diagrams
- `domain-qa-class.md`: add `+givenAnswer: Answer` to `Question`, and `AlreadyAnswered` raised by `answer()`. `questionId` stays as it is, because the orders diagram also uses `orderId` for `Order.id`. Anything else that ends up different from the diagram is updated in the same commit as the code.

## 9. Commits on branch `pablo` (one per step, `pytest` green each time)
1. Plan doc + README link.
2. Question domain class + tests + class diagram update.
3. Table + QuestionRepository + tests.
4. Seed questions + seed test.
5. C5 questions on my order + tests (incl. the changed `test_my_orders.py` check).
6. A4 admin question pages + nav link + tests.
Then push `pablo` and open a pull request to `main` (only after Pablo says so).

## Verification
- `pytest` passes, both the new tests and all existing ones.
- `python seed.py`, then `flask --app app run --debug`:
  - As `kari@example.test`, open My orders → the wedding order, see the open question, ask a new one, and see it as Open. An empty question gives an error. Opening one of Ola's order URLs gives 404.
  - As `admin@ektemat.test`, open Questions: open questions are at the top. Open Kari's new question, answer it, and see it marked Answered in the list. Posting the answer form again (e.g. a second tab) gives "already answered".
  - Back as Kari, the answer is shown under the question.
- Screenshots of the customer's order page with questions and the admin questions list and form, for the report.
