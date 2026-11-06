# Индекс эндпоинтов API

> Сгенерировано `scripts/gen_api_index.py`. Не редактировать вручную.
> Дата генерации: 06.11.2026.
> Версия OpenAPI: `0.9.0`. Путей: 174; операций: 235.

## Как пользоваться
1. Найдите маршрут по тегу, пути или summary.
2. Для деталей откройте `docs/03-architecture/03-api.md` или `/openapi.json`.
3. Не читайте весь файл: используйте поиск по строке.

## admin
- `GET` `/api/v1/admin/audit` — Журнал аудита
- `GET` `/api/v1/admin/settings/cache` — Настройки кеша доступа
- `PATCH` `/api/v1/admin/settings/cache` — Изменить настройки кеша доступа
- `POST` `/api/v1/admin/settings/cache/test` — Проверить подключение к кешу
- `GET` `/api/v1/admin/stats` — Сводка по школе
- `GET` `/api/v1/admin/users` — Пользователи школы
- `POST` `/api/v1/admin/users` — Создание пользователя школы

## analytics
- `GET` `/api/v1/analytics/export.csv` — Выгрузка аналитики школы в CSV
- `GET` `/api/v1/analytics/overview` — Сводная аналитика школы

## assessment
- `GET` `/api/v1/assessment/assignments` — Список работ
- `POST` `/api/v1/assessment/assignments` — Назначить работу
- `GET` `/api/v1/assessment/assignments/{assignment_id}` — Карточка работы
- `DELETE` `/api/v1/assessment/assignments/{assignment_id}` — Архивировать работу
- `POST` `/api/v1/assessment/assignments/{assignment_id}/close` — Закрыть работу
- `POST` `/api/v1/assessment/assignments/{assignment_id}/publish` — Опубликовать работу
- `GET` `/api/v1/assessment/assignments/{assignment_id}/result` — Результат ученика
- `GET` `/api/v1/assessment/assignments/{assignment_id}/results` — Результаты работы для учителя
- `POST` `/api/v1/assessment/assignments/{assignment_id}/retry` — Начать новую попытку
- `POST` `/api/v1/assessment/assignments/{assignment_id}/submit` — Сдать работу
- `GET` `/api/v1/assessment/quizzes` — Список тестов
- `POST` `/api/v1/assessment/quizzes` — Создать тест
- `GET` `/api/v1/assessment/quizzes/{quiz_id}` — Карточка теста
- `PATCH` `/api/v1/assessment/quizzes/{quiz_id}` — Изменить тест

## auth
- `POST` `/api/v1/auth/login` — Вход по логину и паролю
- `POST` `/api/v1/auth/logout` — Выход из системы
- `GET` `/api/v1/auth/me` — Текущий пользователь
- `POST` `/api/v1/auth/refresh` — Обновление access-токена

## communication
- `GET` `/api/v1/communication/notifications` — List Notifications
- `POST` `/api/v1/communication/notifications` — Create Notification
- `POST` `/api/v1/communication/notifications/{notification_id}/read` — Mark Notification Read

## documents
- `GET` `/api/v1/documents/requests` — List School Document Requests
- `POST` `/api/v1/documents/requests` — Create Document Request
- `GET` `/api/v1/documents/requests/mine` — List My Document Requests
- `POST` `/api/v1/documents/requests/{request_id}/cancel` — Cancel Document Request
- `POST` `/api/v1/documents/requests/{request_id}/process` — Process Document Request

## education
- `GET` `/api/v1/education/higher/competencies` — Профессиональные компетенции
- `POST` `/api/v1/education/higher/competencies` — Создать компетенцию
- `PATCH` `/api/v1/education/higher/competencies/{competency_id}` — Изменить компетенцию
- `GET` `/api/v1/education/higher/credit-transfers` — Перезачёт кредитов
- `POST` `/api/v1/education/higher/credit-transfers` — Создать перезачёт кредитов
- `PATCH` `/api/v1/education/higher/credit-transfers/{transfer_id}` — Изменить решение о перезачёте кредитов
- `GET` `/api/v1/education/higher/curricula` — Учебные планы профессиональной ступени
- `POST` `/api/v1/education/higher/curricula` — Создать учебный план
- `GET` `/api/v1/education/higher/curricula/{curriculum_id}` — Учебный план с компонентами
- `PATCH` `/api/v1/education/higher/curricula/{curriculum_id}` — Изменить учебный план
- `GET` `/api/v1/education/higher/curricula/{curriculum_id}/competency-matrix` — Матрица компетенций учебного плана
- `PUT` `/api/v1/education/higher/curricula/{curriculum_id}/competency-matrix` — Заменить матрицу компетенций учебного плана
- `POST` `/api/v1/education/higher/curricula/{curriculum_id}/components` — Добавить дисциплину, модуль или практику
- `PATCH` `/api/v1/education/higher/curricula/{curriculum_id}/components/{component_id}` — Изменить компонент учебного плана
- `DELETE` `/api/v1/education/higher/curricula/{curriculum_id}/components/{component_id}` — Удалить компонент учебного плана
- `GET` `/api/v1/education/higher/groups` — Учебные группы и классы ступени
- `GET` `/api/v1/education/higher/overview` — Сводка ступени: Высшее образование
- `GET` `/api/v1/education/higher/practice-contracts` — Договоры с предприятиями
- `POST` `/api/v1/education/higher/practice-contracts` — Заключить договор с предприятием
- `PATCH` `/api/v1/education/higher/practice-contracts/{contract_id}` — Изменить договор с предприятием
- `PATCH` `/api/v1/education/higher/practice-diary/{entry_id}` — Изменить или утвердить запись дневника
- `GET` `/api/v1/education/higher/practice-placements` — Практиканты и места практики
- `POST` `/api/v1/education/higher/practice-placements` — Назначить практику обучающемуся
- `PATCH` `/api/v1/education/higher/practice-placements/{placement_id}` — Изменить практику обучающегося
- `POST` `/api/v1/education/higher/practice-placements/{placement_id}/assessment` — Оценить практику обучающегося
- `GET` `/api/v1/education/higher/practice-placements/{placement_id}/diary` — Дневник практики
- `POST` `/api/v1/education/higher/practice-placements/{placement_id}/diary` — Добавить запись дневника практики
- `GET` `/api/v1/education/higher/practice-places` — Предприятия и организации для практики
- `POST` `/api/v1/education/higher/practice-places` — Добавить предприятие для практики
- `PATCH` `/api/v1/education/higher/practice-places/{place_id}` — Изменить предприятие для практики
- `GET` `/api/v1/education/higher/profiles` — Академические профили обучающихся
- `POST` `/api/v1/education/higher/profiles` — Создать академический профиль обучающегося
- `PATCH` `/api/v1/education/higher/profiles/{profile_id}` — Изменить академический профиль обучающегося
- `GET` `/api/v1/education/higher/programs` — Образовательные программы и специальности
- `POST` `/api/v1/education/higher/programs` — Создать образовательную программу
- `PATCH` `/api/v1/education/higher/programs/{program_id}` — Изменить образовательную программу
- `GET` `/api/v1/education/higher/programs/{program_id}/competencies` — Компетенции образовательной программы
- `PUT` `/api/v1/education/higher/programs/{program_id}/competencies` — Заменить матрицу компетенций программы
- `GET` `/api/v1/education/higher/sessions` — Экзаменационные сессии
- `POST` `/api/v1/education/higher/sessions` — Создать экзаменационную сессию
- `PATCH` `/api/v1/education/higher/sessions/{session_id}` — Изменить экзаменационную сессию
- `GET` `/api/v1/education/higher/sessions/{session_id}/statements` — Зачётные и экзаменационные ведомости сессии
- `POST` `/api/v1/education/higher/sessions/{session_id}/statements` — Создать зачётную ведомость
- `GET` `/api/v1/education/higher/staff-profiles` — Академические профили преподавателей
- `POST` `/api/v1/education/higher/staff-profiles` — Создать академический профиль преподавателя
- `PATCH` `/api/v1/education/higher/staff-profiles/{profile_id}` — Изменить академический профиль преподавателя
- `GET` `/api/v1/education/higher/statements/{statement_id}` — Зачётная ведомость с результатами
- `PATCH` `/api/v1/education/higher/statements/{statement_id}` — Изменить или утвердить ведомость
- `POST` `/api/v1/education/higher/statements/{statement_id}/records/bulk` — Внести результаты студентов в ведомость
- `GET` `/api/v1/education/higher/students/{profile_id}/transcript` — Зачётная книжка и перезачёт кредитов
- `GET` `/api/v1/education/primary/curricula` — Учебные планы профессиональной ступени
- `GET` `/api/v1/education/primary/curricula/{curriculum_id}` — Учебный план с компонентами
- `GET` `/api/v1/education/primary/groups` — Учебные группы и классы ступени
- `GET` `/api/v1/education/primary/overview` — Сводка ступени: Начальное образование
- `GET` `/api/v1/education/primary/profiles` — Академические профили обучающихся
- `GET` `/api/v1/education/primary/programs` — Образовательные программы и специальности
- `GET` `/api/v1/education/primary/staff-profiles` — Академические профили преподавателей
- `GET` `/api/v1/education/secondary/curricula` — Учебные планы профессиональной ступени
- `GET` `/api/v1/education/secondary/curricula/{curriculum_id}` — Учебный план с компонентами
- `GET` `/api/v1/education/secondary/groups` — Учебные группы и классы ступени
- `GET` `/api/v1/education/secondary/overview` — Сводка ступени: Среднее образование
- `GET` `/api/v1/education/secondary/profiles` — Академические профили обучающихся
- `GET` `/api/v1/education/secondary/programs` — Образовательные программы и специальности
- `GET` `/api/v1/education/secondary/staff-profiles` — Академические профили преподавателей
- `GET` `/api/v1/education/vocational/competencies` — Профессиональные компетенции
- `POST` `/api/v1/education/vocational/competencies` — Создать компетенцию
- `PATCH` `/api/v1/education/vocational/competencies/{competency_id}` — Изменить компетенцию
- `GET` `/api/v1/education/vocational/credit-transfers` — Перезачёт кредитов
- `POST` `/api/v1/education/vocational/credit-transfers` — Создать перезачёт кредитов
- `PATCH` `/api/v1/education/vocational/credit-transfers/{transfer_id}` — Изменить решение о перезачёте кредитов
- `GET` `/api/v1/education/vocational/curricula` — Учебные планы профессиональной ступени
- `POST` `/api/v1/education/vocational/curricula` — Создать учебный план
- `GET` `/api/v1/education/vocational/curricula/{curriculum_id}` — Учебный план с компонентами
- `PATCH` `/api/v1/education/vocational/curricula/{curriculum_id}` — Изменить учебный план
- `GET` `/api/v1/education/vocational/curricula/{curriculum_id}/competency-matrix` — Матрица компетенций учебного плана
- `PUT` `/api/v1/education/vocational/curricula/{curriculum_id}/competency-matrix` — Заменить матрицу компетенций учебного плана
- `POST` `/api/v1/education/vocational/curricula/{curriculum_id}/components` — Добавить дисциплину, модуль или практику
- `PATCH` `/api/v1/education/vocational/curricula/{curriculum_id}/components/{component_id}` — Изменить компонент учебного плана
- `DELETE` `/api/v1/education/vocational/curricula/{curriculum_id}/components/{component_id}` — Удалить компонент учебного плана
- `GET` `/api/v1/education/vocational/groups` — Учебные группы и классы ступени
- `GET` `/api/v1/education/vocational/overview` — Сводка ступени: Среднее специальное образование
- `GET` `/api/v1/education/vocational/practice-contracts` — Договоры с предприятиями
- `POST` `/api/v1/education/vocational/practice-contracts` — Заключить договор с предприятием
- `PATCH` `/api/v1/education/vocational/practice-contracts/{contract_id}` — Изменить договор с предприятием
- `PATCH` `/api/v1/education/vocational/practice-diary/{entry_id}` — Изменить или утвердить запись дневника
- `GET` `/api/v1/education/vocational/practice-placements` — Практиканты и места практики
- `POST` `/api/v1/education/vocational/practice-placements` — Назначить практику обучающемуся
- `PATCH` `/api/v1/education/vocational/practice-placements/{placement_id}` — Изменить практику обучающегося
- `POST` `/api/v1/education/vocational/practice-placements/{placement_id}/assessment` — Оценить практику обучающегося
- `GET` `/api/v1/education/vocational/practice-placements/{placement_id}/diary` — Дневник практики
- `POST` `/api/v1/education/vocational/practice-placements/{placement_id}/diary` — Добавить запись дневника практики
- `GET` `/api/v1/education/vocational/practice-places` — Предприятия и организации для практики
- `POST` `/api/v1/education/vocational/practice-places` — Добавить предприятие для практики
- `PATCH` `/api/v1/education/vocational/practice-places/{place_id}` — Изменить предприятие для практики
- `GET` `/api/v1/education/vocational/profiles` — Академические профили обучающихся
- `POST` `/api/v1/education/vocational/profiles` — Создать академический профиль обучающегося
- `PATCH` `/api/v1/education/vocational/profiles/{profile_id}` — Изменить академический профиль обучающегося
- `GET` `/api/v1/education/vocational/programs` — Образовательные программы и специальности
- `POST` `/api/v1/education/vocational/programs` — Создать образовательную программу
- `PATCH` `/api/v1/education/vocational/programs/{program_id}` — Изменить образовательную программу
- `GET` `/api/v1/education/vocational/programs/{program_id}/competencies` — Компетенции образовательной программы
- `PUT` `/api/v1/education/vocational/programs/{program_id}/competencies` — Заменить матрицу компетенций программы
- `GET` `/api/v1/education/vocational/sessions` — Экзаменационные сессии
- `POST` `/api/v1/education/vocational/sessions` — Создать экзаменационную сессию
- `PATCH` `/api/v1/education/vocational/sessions/{session_id}` — Изменить экзаменационную сессию
- `GET` `/api/v1/education/vocational/sessions/{session_id}/statements` — Зачётные и экзаменационные ведомости сессии
- `POST` `/api/v1/education/vocational/sessions/{session_id}/statements` — Создать зачётную ведомость
- `GET` `/api/v1/education/vocational/staff-profiles` — Академические профили преподавателей
- `POST` `/api/v1/education/vocational/staff-profiles` — Создать академический профиль преподавателя
- `PATCH` `/api/v1/education/vocational/staff-profiles/{profile_id}` — Изменить академический профиль преподавателя
- `GET` `/api/v1/education/vocational/statements/{statement_id}` — Зачётная ведомость с результатами
- `PATCH` `/api/v1/education/vocational/statements/{statement_id}` — Изменить или утвердить ведомость
- `POST` `/api/v1/education/vocational/statements/{statement_id}/records/bulk` — Внести результаты студентов в ведомость
- `GET` `/api/v1/education/vocational/students/{profile_id}/transcript` — Зачётная книжка и перезачёт кредитов

## iam
- `GET` `/api/v1/groups` — Группы пользователей
- `POST` `/api/v1/groups` — Создать группу
- `GET` `/api/v1/groups/permissions` — Каталог прав платформы
- `GET` `/api/v1/groups/{group_id}` — Карточка группы
- `PATCH` `/api/v1/groups/{group_id}` — Изменить группу
- `DELETE` `/api/v1/groups/{group_id}` — Отключить группу
- `POST` `/api/v1/groups/{group_id}/members` — Добавить пользователей в группу
- `DELETE` `/api/v1/groups/{group_id}/members/{user_id}` — Исключить пользователя из группы
- `PUT` `/api/v1/groups/{group_id}/permissions/{permission_code}` — Назначить право группе
- `DELETE` `/api/v1/groups/{group_id}/permissions/{permission_code}` — Снять право с группы
- `GET` `/api/v1/me/permissions` — Действующие права пользователя
- `GET` `/api/v1/me/services` — Доступные пользователю сервисы

## journal
- `GET` `/api/v1/journal/classes` — Классы, доступные в журнале
- `GET` `/api/v1/journal/classes/{class_id}/students` — Ученики класса для журнала
- `GET` `/api/v1/journal/entries` — Записи журнала
- `POST` `/api/v1/journal/entries` — Выставить оценку или отметить посещаемость
- `POST` `/api/v1/journal/entries/bulk` — Массово выставить оценки и посещаемость
- `PATCH` `/api/v1/journal/entries/{entry_id}` — Изменить запись журнала
- `DELETE` `/api/v1/journal/entries/{entry_id}` — Удалить запись журнала
- `GET` `/api/v1/journal/schedule` — Расписание
- `POST` `/api/v1/journal/schedule` — Добавить или заменить урок в расписании
- `PATCH` `/api/v1/journal/schedule/{item_id}` — Изменить урок расписания
- `DELETE` `/api/v1/journal/schedule/{item_id}` — Удалить урок расписания
- `GET` `/api/v1/journal/summary` — Сводка оценок и посещаемости

## library
- `GET` `/api/v1/library` — Библиотека пользователя
- `POST` `/api/v1/library/books` — Добавить пособие в библиотеку
- `GET` `/api/v1/library/books/{book_id}` — Карточка книги
- `PATCH` `/api/v1/library/books/{book_id}` — Изменить книгу и доступ классов
- `DELETE` `/api/v1/library/books/{book_id}` — Удалить книгу из библиотеки
- `POST` `/api/v1/library/books/{book_id}/recommend` — Порекомендовать книгу классу или ученикам
- `GET` `/api/v1/library/catalog` — Пособия и темы для рекомендаций
- `GET` `/api/v1/library/manage` — Библиотека учителя: книги, классы и ученики
- `GET` `/api/v1/library/recommendations` — Отправленные рекомендации
- `DELETE` `/api/v1/library/recommendations/{recommendation_id}` — Отозвать рекомендацию
- `POST` `/api/v1/library/recommendations/{recommendation_id}/done` — Отметить рекомендацию выполненной

## lms
- `GET` `/api/v1/lms/courses` — Курсы школы
- `GET` `/api/v1/lms/courses/{course_id}` — Карточка курса
- `GET` `/api/v1/lms/subjects` — Предметы
- `GET` `/api/v1/lms/subjects/{subject_id}` — Карточка предмета
- `GET` `/api/v1/lms/textbooks` — Учебники
- `GET` `/api/v1/lms/textbooks/{textbook_id}` — Карточка учебника
- `GET` `/api/v1/lms/topics` — Каталог тем
- `GET` `/api/v1/lms/topics/by-code/{code}` — Тема по коду
- `GET` `/api/v1/lms/topics/{topic_id}` — Карточка темы

## onboarding
- `GET` `/api/v1/onboarding/me` — Персональная программа обучения
- `GET` `/api/v1/onboarding/me/modules/{module_code}` — Модуль персональной программы
- `POST` `/api/v1/onboarding/me/modules/{module_code}/start` — Начать или продолжить модуль
- `POST` `/api/v1/onboarding/me/modules/{module_code}/steps/{step_code}/complete` — Завершить шаг обучения
- `GET` `/api/v1/onboarding/reports/export.csv` — Выгрузка прогресса обучения
- `GET` `/api/v1/onboarding/reports/summary` — Сводка прохождения обучения
- `GET` `/api/v1/onboarding/reports/users` — Прогресс обучения пользователей
- `POST` `/api/v1/onboarding/reports/users/{user_id}/reset` — Сбросить прогресс обучения пользователя

## org
- `GET` `/api/v1/org/cities` — Города и районы
- `GET` `/api/v1/org/classes` — Классы школы
- `GET` `/api/v1/org/classes/{class_id}` — Карточка класса
- `GET` `/api/v1/org/regions` — Области и регионы
- `GET` `/api/v1/org/schools` — Доступные школы
- `POST` `/api/v1/org/schools` — Создать учреждение образования
- `GET` `/api/v1/org/schools/{school_id}` — Карточка школы
- `PATCH` `/api/v1/org/schools/{school_id}` — Изменить учреждение образования

## other
- `GET` `/health` — Проверка доступности

## safety
- `GET` `/api/v1/safety/appeals` — List School Appeals
- `POST` `/api/v1/safety/appeals` — Create Appeal
- `GET` `/api/v1/safety/appeals/mine` — List My Appeals
- `POST` `/api/v1/safety/appeals/{appeal_id}/close` — Close Appeal
- `POST` `/api/v1/safety/appeals/{appeal_id}/respond` — Respond Appeal
- `GET` `/api/v1/safety/consents` — List Consents
- `POST` `/api/v1/safety/consents` — Create Consent
- `POST` `/api/v1/safety/consents/{consent_id}/revoke` — Revoke Consent
- `GET` `/api/v1/safety/geolocation` — List Geolocation
- `POST` `/api/v1/safety/geolocation` — Create Geolocation Point
- `GET` `/api/v1/safety/incidents` — List School Incidents
- `POST` `/api/v1/safety/incidents` — Create Incident
- `POST` `/api/v1/safety/incidents/{incident_id}/resolve` — Resolve Incident
- `POST` `/api/v1/safety/maintenance/purge` — Purge Expired Data
- `GET` `/api/v1/safety/settings` — Get Safety Settings
- `PUT` `/api/v1/safety/settings` — Update Safety Settings

## system
- `GET` `/` — Информация о сервисе
- `GET` `/api/v1/health` — Проверка доступности
- `GET` `/api/v1/meta` — Метаданные приложения
- `GET` `/api/v1/services` — Каталог сервисов
- `GET` `/api/v1/services/effective` — Действующие сервисы для области
- `GET` `/api/v1/services/{service_code}` — Карточка сервиса
- `GET` `/api/v1/services/{service_code}/activation` — Активация сервиса в области
- `PUT` `/api/v1/services/{service_code}/activation` — Включить или отключить сервис
- `DELETE` `/api/v1/services/{service_code}/activation` — Снять активацию и вернуть наследование
