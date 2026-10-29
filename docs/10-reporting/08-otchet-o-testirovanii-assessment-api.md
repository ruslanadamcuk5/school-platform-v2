# Отчёт о тестировании API тестов и работ (assessment)

| Параметр | Значение |
|---|---|
| Код документа | ШК-10-08 |
| Версия | 0.1 |
| Статус | Рабочий |
| Дата | 29.10.2026 |
| Объект испытаний | `/api/v1/assessment/*`, сервис автопроверки |
| Стенд | Локальная среда разработки, Windows, Python 3.13 |
| Инструменты | pytest, httpx/ASGITransport, ruff |

## 1. Цель
Подтвердить работоспособность домена оценивания: создание тестов, назначение
работ, сдача учеником, автопроверка, результаты для учителя и родителя,
соблюдение ролей и мультитенантности.

## 2. Состав автоматических тестов
Файлы:
- `backend/tests/test_assessment_api.py` — API и роли;
- `backend/tests/test_grading.py` — правила автопроверки.

| ID | Тест | Проверяемое поведение | Результат |
|---|---|---|---|
| ASM-01 | `test_assessment_routes_are_in_openapi` | Все маршруты `/assessment/*` объявлены | Пройден |
| ASM-02 | `test_assessment_requires_authentication` | Запрос без токена — 401 | Пройден |
| ASM-03 | `test_superadmin_needs_school_scope` | superadmin без `school_id` — 400 | Пройден |
| ASM-04 | `test_teacher_lists_quizzes_with_question_counts` | Список тестов и `question_count` | Пройден |
| ASM-05 | `test_unknown_quiz_returns_404` | Неизвестный тест — 404 | Пройден |
| ASM-06 | `test_student_submission_is_auto_graded` | Сдача, score/max_score, percent, grade, details | Пройден |
| ASM-07 | `test_retry_is_rejected_when_attempts_are_exhausted` | Лимит попыток — 409 | Пройден |
| ASM-08 | `test_normalize_handles_whitespace_case_and_yo` | Нормализация текста | Пройден |
| ASM-09 | `test_single_choice_accepts_text_and_option_id` | Выбор по тексту и UUID варианта | Пройден |
| ASM-10 | `test_multiple_choice_requires_all_correct_options` | Множественный выбор | Пройден |
| ASM-11 | `test_text_and_number_answers_use_payload` | Числа `3,5` и `3.5` | Пройден |
| ASM-12 | `test_fraction_mixed_number_and_time_answers` | Дроби, смешанные числа, время | Пройден |
| ASM-13 | `test_read_task_is_credited_on_submission` | Задание «прочитать» | Пройден |
| ASM-14 | `test_dictation_uses_similarity_threshold` | Диктант, порог 60 % | Пройден |
| ASM-15 | `test_grade_scale_and_summary` | 10-балльная шкала | Пройден |
| ASM-16 | `test_teacher_assigns_quiz_to_class` | Назначение теста классу, `question_count` | Пройден |
| ASM-17 | `test_teacher_cannot_assign_to_another_school_class` | Класс другой школы — 403 | Пройден |

## 3. Команды запуска

```powershell
cd C:\Users\adamrv\Documents\school-platform-v2
.venv\Scripts\python.exe -m ruff check backend/app backend/tests
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

## 4. Результаты

| Проверка | Результат |
|---|---|
| Ruff | `All checks passed!` |
| Pytest | `30 passed, 2 warnings` |
| Новые тесты assessment | 17 |
| Критичные дефекты | Не выявлены |

Предупреждения относятся к `python-jose` (`datetime.utcnow()`), не влияют на
функциональность.

## 5. Сценарии для ручной проверки на Stage
1. Создать тест из 5 вопросов: одиночный выбор, число, дробь, время, текст.
2. Назначить тест классу и ученику.
3. Сдать работу учеником, проверить `score`, `percent`, `grade`, `details`.
4. Повторить сдачу сверх лимита — получить 409.
5. Открыть результаты учителем, проверить список учеников и попытки.
6. Открыть работу родителем с `student_id` своего ребёнка — 200; чужого — 403.
7. Проверить, что ученик другой школы не видит и не сдаёт работу — 403.
8. Проверить идемпотентность: повторный POST с тем же `operation_id`.

## 6. Вывод
Домен `assessment` реализован: тесты, назначения, сдача, автопроверка,
результаты и роли. Автотесты зелёные. Для приёмки требуется прогнать сценарии
на Stage с реальной PostgreSQL и импортированными данными старого контура.
