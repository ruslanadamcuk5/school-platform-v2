# Отчёт о тестировании API журнала (journal)

| Параметр | Значение |
|---|---|
| Код документа | ШК-10-09 |
| Версия | 0.1 |
| Статус | Рабочий |
| Дата | 29.10.2026 |
| Объект испытаний | `/api/v1/journal/*`: расписание, оценки, посещаемость, сводка |
| Стенд | Локальная среда разработки, Windows, Python 3.13 |
| Инструменты | pytest, httpx/ASGITransport, ruff |

## 1. Цель
Подтвердить работоспособность журнала: недельное расписание, выставление
оценок и посещаемости, массовое заполнение, сводка, роли и мультитенантность.

## 2. Состав автоматических тестов
Файл: `backend/tests/test_journal_api.py`.

| ID | Тест | Проверяемое поведение | Результат |
|---|---|---|---|
| JRN-01 | `test_journal_routes_are_in_openapi` | Все маршруты `/journal/*` объявлены | Пройден |
| JRN-02 | `test_journal_requires_authentication` | Запрос без токена — 401 | Пройден |
| JRN-03 | `test_student_schedule_uses_class_membership` | Расписание класса ученика, названия предмета и класса | Пройден |
| JRN-04 | `test_student_cannot_read_another_student_entries` | Чужие записи — 403 | Пройден |
| JRN-05 | `test_parent_must_pass_child_id` | Родитель без `student_id` — 400 | Пройден |
| JRN-06 | `test_admin_saves_grade_and_attendance` | Оценка 9 и `present` сохранены, имена подставлены | Пройден |
| JRN-07 | `test_bulk_grading_creates_entries` | Массовое выставление: `created=2` | Пройден |
| JRN-08 | `test_journal_summary_groups_grades_and_attendance` | Средний балл 8.5, counts `present/absent` | Пройден |
| JRN-09 | `test_schedule_rejects_end_before_start` | `end_time <= start_time` — 422 | Пройден |
| JRN-10 | `test_teacher_cannot_edit_foreign_class_schedule` | Чужой класс — 403 | Пройден |
| JRN-11 | `test_existing_entry_is_updated_not_duplicated` | Upsert по ключу, дубль не создаётся | Пройден |
| JRN-12 | `test_date_range_is_validated` | `date_from > date_to` — 400 | Пройден |

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
| Pytest | `42 passed, 2 warnings` |
| Новые тесты журнала | 12 |
| Критичные дефекты | Не выявлены |

Предупреждения относятся к `python-jose` (`datetime.utcnow()`), не влияют на
функциональность.

## 5. Сценарии для ручной проверки на Stage
1. Открыть расписание класса, добавить урок, изменить время и удалить.
2. Проверить, что `end_time <= start_time` отклоняется.
3. Учитель открывает только свои классы; чужой класс — 403.
4. Ученик видит расписание своего класса и свои оценки.
5. Родитель открывает журнал ребёнка с `student_id`; без него — 400.
6. Выставить оценку и посещаемость одному ученику, затем повторно — проверить
   обновление без дубля.
7. Массово заполнить журнал класса, проверить `created/updated`.
8. Открыть сводку: средний балл, количество оценок и отметок посещаемости.
9. Проверить изоляцию школ: ученик/учитель другой школы не видит данные.
10. Проверить `date_from/date_to` и пагинацию записей.

## 6. Вывод
Домен `journal` реализован: расписание, оценки, посещаемость, массовое
выставление и сводка. Автотесты зелёные. Для приёмки требуется прогнать
сценарии на Stage с реальной PostgreSQL и импортированным расписанием.
