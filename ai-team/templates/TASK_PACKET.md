# Task packet — заполнить до вызова агента

- TASK_ID:
- FINDING_IDS:
- ATTEMPT_ID:
- ROLE:
- ROLE_PHASE (если QA: TEST_AUTHOR / VERIFY_CANDIDATE):
- INVOCATION_REF (только реальный ID/ссылка runtime; не придумывать):
- ABSOLUTE_WORKTREE_PATH:
- ABSOLUTE_TEAM_RULES_PATH:
- BASELINE_SHA (полные 40 hex):
- QA_COMMIT_SHA (если есть):
- CANDIDATE_SHA (для проверки):
- INTEGRATION_BASE_SHA:

## Цель и исходный сценарий

## Проверяемые acceptance criteria

## Non-goals

## Замороженный contract

## Разрешённые production paths

## Разрешённые test paths

## Зарезервированные ресурсы и владелец

## Состояние prerequisites

## Входные artifacts

## Команды и environment (только synthetic credentials)

## Выходные artifacts / writable output directory

## Запрещённые операции

No push/deploy/protected-main merge/production DB. Не выходить за scope. Не редактировать рабочую копию другого агента и общий ledger. Не создавать subagents.

## Требуемый ответ

STATUS, CHECKED_SHA, FACTS_WITH_REFERENCES, COMMANDS_AND_REAL_RESULTS, CHANGED_FILES_IF_ALLOWED, BLOCKERS, NEXT_ACTION.
