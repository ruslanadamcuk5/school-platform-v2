# Отчёт о тестировании API учебного контента (LMS)

| Параметр | Значение |
|---|---|
| Код документа | ШК-10-07 |
| Версия | 0.1 |
| Статус | Рабочий |
| Дата | 29.10.2026 |
| Объект испытаний | `/api/v1/lms/*` |
| Стенд | Локальная среда разработки, Windows, Python 3.13 |
| Инструменты | pytest 8.3.4, httpx, FastAPI TestClient/ASGITransport, ruff 0.8.4 |

## 1. Цель
Подтвердить корректность API чтения учебного контента: предметы, темы,
методики, уроки, учебники и курсы, а также соблюдение аутентификации и
мультитенантности.

## 2. Состав автоматических тестов
Файл: `backend/tests/test_lms_api.py`.

| ID | Тест | Проверяемое поведение | Ожидаемый результат | Факт |
|---|---|---|---|---|
| LMS-01 | `test_lms_subjects_are_listed` | Список активных предметов | 200, `code=math` | Пройден |
| LMS-02 | `test_lms_topics_support_filters_and_pagination` | Фильтры `grade`, `search`, пагинация | 200, `total=1`, `limit=10` | Пройден |
| LMS-03 | `test_lms_topic_detail_includes_methods_lessons_and_books` | Тема с методиками, уроками и учебниками | 200, все блоки присутствуют | Пройден |
| LMS-04 | `test_lms_requires_authentication` | Запрос без access-токена | 401 | Пройден |
| LMS-05 | `test_courses_require_school_for_superadmin` | superadmin без `school_id` | 400 | Пройден |
| LMS-06 | `test_lms_routes_are_in_openapi` | Наличие маршрутов в OpenAPI | Все пути объявлены | Пройден |

Дополнительно регрессионные тесты:
- `tests/test_security.py` — 5 тестов JWT/паролей/refresh-токенов.
- `tests/test_openapi.py` — 2 теста OpenAPI и Bearer-схемы.

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
| Pytest | `13 passed, 2 warnings in 9.58s` |
| Покрытие новых маршрутов | 6 тестов LMS API + 2 OpenAPI |
| Критичные дефекты | Не выявлены |

Предупреждения pytest относятся к библиотеке `python-jose` и не влияют на
функциональность: рекомендуется заменить `datetime.utcnow()` в зависимости
при обновлении библиотеки.

## 5. Сценарии для ручной проверки на Stage
1. Открыть `/docs`, убедиться, что группа `lms` отображается.
2. Выполнить вход, получить access-токен.
3. Вызвать `/api/v1/lms/subjects`, `/topics?grade=5`, `/textbooks?grade=5`.
4. Проверить, что школьный пользователь не видит курсы другой школы.
5. Проверить, что запрос без токена возвращает 401.

## 6. Вывод
API учебного контента реализован и проверен автоматическими тестами.
Функционал готов к следующему шагу: API тестов, работ и журнала. Для приёмки
на Stage требуется прогнать сценарии на реальной PostgreSQL с импортированными
данными старого контура.
