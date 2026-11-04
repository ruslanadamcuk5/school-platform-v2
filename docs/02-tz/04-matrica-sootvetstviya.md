# Матрица соответствия требованиям

| Параметр | Значение |
|---|---|
| Код документа | ШК-02-04 |
| Версия | 0.5 |
| Статус | Рабочий |
| Дата | 04.11.2026 |

## Назначение
Матрица связывает требования ТЗ с проектными решениями, реализацией и
проверками. Заполняется по мере разработки.

## Формат
| ID требования | Требование | Решение | Компонент | Тест | Статус |
|---|---|---|---|---|---|
| ST-11 | Адаптивные интерфейсы по возрасту | Набор тем и компонентов | Frontend | UI-тесты | Не начато |
| ST-20 | Офлайн-режим | Локальная БД + очередь | Mobile/Web | E2E | Не начато |
| ST-32 | Загрузка фото решения | S3 + API | Assessment | API-тест | Не начато |
| ST-35 | ИИ-проверка фото/аудио | AI-оркестратор | AI | Интеграционный | Не начато |
| PR-01 | Мультидетность | Контекст семьи | Frontend/API | E2E | Не начато |
| PR-14 | GPS-трекинг | Модуль geo | API/Mobile | Тест согласий | Не начато |
| TE-10 | Конструктор уроков | LMS | Backend/Frontend | E2E | Не начато |
| TE-22 | Электронный журнал | Модуль journal | Backend | API-тест | Не начато |
| SA-04 | Расписание | Модуль schedule | Backend | API-тест | Не начато |
| SE-02 | PDF-справки | Генератор документов | Backend | Шаблонный тест | Не начато |
| ME-04 | ИИ-валидация контента | RAG + правила | AI | Тест качества | Не начато |
| PS-01 | Анонимные обращения | Отдельный контур | Backend | Тест приватности | Не начато |
| AD-01 | Иерархия админов | Группы + scope | IAM | Матрица групп | В работе |
| SY-05 | Офлайн-синхронизация | Idempotency + LWW | API | Нагрузочный | Не начато |
| SY-07 | Резервное копирование | PostgreSQL backup | DevOps | Учения | Не начато |
| GB-01 | Права только группам | `iam.groups` + `group_permissions` | IAM | Unit + API | Реализовано |
| GB-02 | Группы на 5 уровнях | `scope_type/scope_id` | IAM | API | Реализовано |
| GB-04 | Наследование | `access.resolve_permissions` | IAM | Unit | Реализовано |
| GB-05 | Конфликты прав | depth + deny | IAM | Unit | Реализовано |
| GB-06 | Перевод между группами | membership API | IAM | Сценарий | В работе |
| GB-10 | `/me/permissions` | API | IAM | API-тест | Реализовано |
| SV-01 | Реестр сервисов | `system.services` + registry | System | API | Реализовано |
| SV-03 | Включение/отключение | `service_activations` | System | API | Реализовано |
| SV-04 | Ядро нельзя отключить | `is_core` | System | Unit | Реализовано |
| SV-06 | `/me/services` | API | System | API-тест | Реализовано |
| SV-10 | Health/OpenAPI | FastAPI | Все | Smoke | Частично |
| EDL-01 | Начальное образование | `primary_education` + классы 1–4 | Education | API | Реализовано |
| EDL-02 | Среднее образование | `secondary_education` + классы 5–11 | Education | API | Реализовано |
| EDL-03 | Среднее специальное образование | `vocational_education` + колледжи | Education | API | Реализовано |
| EDL-04 | Высшее образование | `higher_education` + вузы | Education | API | Реализовано |
| EDL-05 | Включение ступени по области | `service_activations` | System | API | Реализовано |
| EDL-08 | Тип и ступени учреждения | `org.schools` | Org | Unit + API | Реализовано |
| EDL-09 | Ступень должна быть у учреждения | `education_levels` | Education | API | Реализовано |
| PRO-01 | Образовательные программы | `org.education_programs` | Education | API | Реализовано |
| PRO-02 | Группы по программе и курсу | `org.classes` | Education | API | Реализовано |
| PRO-03 | Профиль студента | `student_academic_profiles` | Education | API + UI | Реализовано |
| PRO-04 | Профиль преподавателя | `staff_academic_profiles` | Education | API + UI | Реализовано |
| PRO-05 | Учебные планы и кредиты | `education_curricula`, `curriculum_components` | Education | API + UI | Реализовано |
| PRO-06 | Практика, дневники и договоры с предприятиями | `practice_places`, `practice_contracts`, `practice_placements`, `practice_diary_entries` | Education | API + UI | Реализовано |
| PRO-07 | Зачётные ведомости и сессии | `academic_sessions`, `session_statements`, `statement_records` | Education | API + UI | Реализовано |
| PRO-08 | Перезачёт кредитов и зачётная книжка | `credit_transfers` + transcript API | Education | API + UI | Реализовано |
| PRO-09 | Компетенции и матрица компетенций | `competencies`, `program_competencies`, `component_competencies` | Education | API + UI | Реализовано |

## Правила ведения
- Каждое обязательное требование должно иметь минимум один тест.
- Статусы: не начато, в работе, реализовано, проверено, принято.
- Для юридически значимых требований указывается ссылка на нормативный акт.
- Матрица обновляется перед каждой сдачей этапа.
