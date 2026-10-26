# Design diagrams

Mermaid diagrams for Ekte Mat Online. Read the ones for a feature before you change it.

File names follow `<feature>-<topic>-<type>.md`, for example `c3-checkout-sequence.md`.

## Plans

- [skeleton-plan.md](skeleton-plan.md) – the code skeleton (app, database, domain classes, login)
- [a1-a2-c1-plan.md](a1-a2-c1-plan.md) – A1 food items, A2 item images and C1 menu (Maja)
- [a3-c4-orders-plan.md](a3-c4-orders-plan.md) – orders: the Order model, A3 admin order pages and C4 my orders

## Overview

| Diagram | What it shows |
|---|---|
| [mvc.md](mvc.md) | Controllers, views and models, and how they connect |
| [domain-orders-class.md](domain-orders-class.md) | `User` + `Role`, orders, guest groups, order lines |
| [domain-food-class.md](domain-food-class.md) | Food items, events, diets |
| [domain-qa-class.md](domain-qa-class.md) | Questions and answers |

## Customer site

| Requirement | Diagrams |
|---|---|
| C1 Menu by event type | [c1-menu-sequence.md](c1-menu-sequence.md) |
| C2 Cart with minimum quantities | [c2-cart-activity.md](c2-cart-activity.md) |
| C3 Order form with notes per guest group | [c3-order-form-activity.md](c3-order-form-activity.md), [c3-checkout-sequence.md](c3-checkout-sequence.md) |
| C4 My orders | [c4-my-orders-sequence.md](c4-my-orders-sequence.md) |
| C5 Questions about an order | [c5-qa-sequence.md](c5-qa-sequence.md), [c5-question-status-state.md](c5-question-status-state.md), [domain-qa-class.md](domain-qa-class.md) |

## Admin panel

| Requirement | Diagrams |
|---|---|
| A1 Food items | [a1-manage-items-sequence.md](a1-manage-items-sequence.md), [a1-edit-item-sequence.md](a1-edit-item-sequence.md), [domain-food-class.md](domain-food-class.md) |
| A2 Item images with preview | [a2-item-image-sequence.md](a2-item-image-sequence.md) |
| A3 Orders, filters and status | [a3-order-management-sequence.md](a3-order-management-sequence.md), [a3-order-status-state.md](a3-order-status-state.md), [a3-payment-status-state.md](a3-payment-status-state.md) |
| A4 Answer questions | [a4-answer-question-sequence.md](a4-answer-question-sequence.md), [c5-question-status-state.md](c5-question-status-state.md), [domain-qa-class.md](domain-qa-class.md) |
