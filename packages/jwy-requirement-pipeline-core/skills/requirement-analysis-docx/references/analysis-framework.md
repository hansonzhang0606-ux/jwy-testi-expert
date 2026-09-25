# Requirement Analysis Framework

Use this checklist when analyzing requirements.

## Core Understanding

- What business problem is being solved?
- Who is the user, caller, client, tenant, role, or system actor?
- What interface, page, task, state, or data object is affected?
- Is this a new rule, replacement rule, or supplement to existing logic?
- What is the expected output or user-visible effect?

## Ambiguity Triggers

Flag and clarify these terms: 支持, 优化, 自动, 默认, 及时, 可配置, 按规则, 异常情况, 有记录, 近 N 个月, 大于/小于, 管理员, 用户可查看, 满足其一, 生效, 历史数据.

## Required Analysis Dimensions

- Time range: rolling days, natural months, full months, inclusive/exclusive boundaries.
- Amount/data metric: source table, amount field, tax-included/excluded, rounding, currency/unit.
- Boundary values: equal to threshold, null, zero, negative, max value, duplicate data.
- Data quality: no data, delayed data, partial query failure, stale cache, inconsistent upstream data.
- Scope: specified client IDs, other clients, tenants, organizations, tax entities, historical tasks.
- Permissions: who can trigger, view, modify, retry, or override.
- State changes: task status, record creation, field update, audit log, notification.
- Compatibility: old rules, existing APIs, downstream consumers, batch jobs, retries.
- Exceptions: timeout, upstream error, invalid input, missing mapping, concurrent updates.
- Acceptance: positive, negative, boundary, non-scope, failure, and regression cases.

## Priority Guidance

- P0: Blocks development, data calculation, interface contract, or acceptance testing.
- P1: Affects edge cases, historical behavior, compatibility, or operational handling.
- P2: Improves completeness, observability, or future maintainability.
