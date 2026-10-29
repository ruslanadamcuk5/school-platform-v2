# Карта миграции существующего функционала

| Параметр | Значение |
|---|---|
| Код документа | ШК-02-05 |
| Версия | 0.4 |
| Статус | Рабочий |
| Дата | 29.10.2026 |
| Источник анализа | `C:\Users\adamrv\Documents\edu-math` (read-only) |
| Целевой контур | `C:\Users\adamrv\Documents\school-platform-v2` |

## Назначение

Документ фиксирует инвентаризацию работающей системы Flask/SQLite и
соответствие «старое → новое» для платформы FastAPI/PostgreSQL/React/Flutter.
Старый контур **не изменяется и не останавливается** до отдельного решения о
переключении трафика.

## 1. Источник и границы анализа

| Параметр | Значение |
|---|---|---|
| Стек | Python 3, Flask, SQLite, Jinja2, Vanilla JS, Kotlin/Compose |
| База | `data/math_tutor.db`, 37 таблиц |
| Роли | `admin`, `teacher`, `student`, `parent` |
| Предметы | 8 |
| Темы | 259 |
| Учебники | 10 |
| Связи «учебник — тема» | 248 |
| Методики/объяснения | 63 |
| Пользователи | 10 (1 admin, 2 teacher, 6 student, 1 parent) |
| Ученические профили | 3 |
| Работы | 4 |
| Попытки прохождения | 15 |
| Аудит | 17 записей |

Анализ выполнялся только чтением. Контрольные суммы и резервная копия SQLite
фиксируются перед фактическим переносом данных.

## 2. Инвентаризация старого контура

### 2.1. Таблицы (37)

| Группа | Таблицы |
|---|---|
| Пользователи и роли | `users`, `learner_accounts`, `parent_children`, `api_tokens` |
| Ученики и прогресс | `learners`, `attempts`, `topic_progress`, `method_progress`, `badges`, `daily_answers`, `play_sessions` |
| Организация | `cities`, `schools`, `school_classes`, `class_students` |
| Контент | `subjects`, `topics`, `methods`, `textbooks`, `textbook_topics`, `courses`, `course_topics`, `course_classes` |
| Работы и оценки | `assignments`, `assignment_results`, `schedules` |
| Библиотека | `library_books`, `library_book_classes`, `library_recommendations`, `library_recommendation_done` |
| Уведомления | `app_notifications` |
| ИИ | `ai_settings`, `ai_explanations`, `ai_quizzes`, `ai_requests` |
| Служебные | `app_meta`, `audit_log` |

### 2.2. Маршруты

| Модуль | Веб-маршруты | JSON API `/api/v1` |
|---|---|---|
| Главная/карта | `/`, `/map`, `/profile`, `/family`, `/daily` | `/meta`, `/map`, `/daily` |
| Аутентификация | `/login`, `/register`, `/logout`, `/profile/account`, `/parent/children` | `/auth/login`, `/auth/logout`, `/auth/me`, `/learners`, `/learners/switch` |
| Ученик | `/topic/<slug>`, `/topic/<slug>/quiz`, `/topic/<slug>/complete`, `/textbook` | `/topics`, `/topics/<slug>`, `/topics/<slug>/quiz`, `/topics/<slug>/read`, `/books/<id>` |
| Игра/тренажёр | `/play/<slug>`, `/boss/<slug>`, `/play/<slug>/result`, `/daily/start` | `/play/start`, `/play/<id>/answer`, `/play/<id>/hint`, `/play/<id>/switch-method`, `/play/<id>/result`, `/daily/start` |
| Учитель | `/teacher`, `/teacher/classes/<id>`, `/teacher/students`, `/teacher/courses`, `/teacher/works`, `/teacher/schedule`, `/teacher/textbooks` | `/teacher/dashboard`, `/teacher/classes`, `/teacher/students`, `/teacher/schedule`, `/teacher/assignments`, `/teacher/library` |
| Ученик (кабинет) | `/student`, `/student/works`, `/student/works/<id>`, `/student/textbooks`, `/student/schedule`, `/student/badges` | `/assignments`, `/assignments/<id>/submit`, `/assignments/<id>/result` |
| Родитель | `/parent`, `/parent/dashboard`, `/parent/assignments`, `/parent/learner/<id>`, `/parent/learner/<id>/export.csv`, `/parent/settings` | `/parent/dashboard`, `/parent/children`, `/parent/children/<id>`, `/parent/link`, `/parent/children/<id>/export`, `/parent/assignments`, `/parent/library` |
| Библиотека | `/library`, `/library/upload`, `/library/<id>`, `/library/recommendations` | `/library`, `/library/books/<id>`, `/teacher/library`, `/teacher/library/<id>/recommend` |
| Администратор | `/admin`, `/admin/cities`, `/admin/schools`, `/admin/classes`, `/admin/subjects`, `/admin/courses`, `/admin/users`, `/admin/textbooks`, `/admin/audit`, `/admin/ai` | `/admin/stats`, `/admin/users`, `/admin/orgs`, `/admin/topics`, `/admin/textbooks`, `/admin/ai`, `/admin/audit` |
| ИИ | `/ai/explain/<slug>`, `/ai/assistant` | `/ai/status`, `/ai/explain/<slug>`, `/ai/assistant` |
| Уведомления | `/notifications` | `/notifications`, `/notifications/<id>/read`, `/notifications/read-all` |
| Мобильное обновление | `/download/android`, `/api/v1/app/version` | `/app/version` |

### 2.3. Шаблоны

| Группа | Шаблоны | Новый интерфейс |
|---|---|---|
| Общие | `base`, `welcome`, `profile`, `family`, `map`, `daily`, `result`, `notifications`, `cabinet` | React layout + router |
| Ученик | `topic`, `topic_reading`, `topic_quiz`, `topic_quiz_result`, `textbook`, `play`, `student/*` | React student app + Flutter |
| Учитель | `teacher/dashboard`, `teacher/classes`, `teacher/students`, `teacher/courses`, `teacher/works`, `teacher/schedule`, `teacher/textbooks` | React teacher app + Flutter |
| Родитель | `parent/dashboard`, `parent/learner`, `parent/assignments`, `parent/settings`, `parent/gate` | React parent app + Flutter |
| Администратор | `admin/dashboard`, `admin/users`, `admin/schools`, `admin/classes`, `admin/subjects`, `admin/courses`, `admin/textbooks`, `admin/audit`, `admin/ai` | React admin app |
| Библиотека | `library/*` | React library + Flutter |
| Ошибки | `errors/400`, `404`, `413`, `500` | React error boundaries + API errors |

### 2.4. Отчёты и выгрузки

| Отчёт | Старая реализация | Новое соответствие |
|---|---|---|
| Сводка администратора | `admin/dashboard`: пользователи, роли, города, школы, классы, предметы, курсы, учебники, работы, активность за 14 дней, топ школ, последние события аудита | `GET /api/v1/admin/stats`, `analytics.daily_snapshots`, отчётные выборки |
| Результаты работы | `teacher/works/<id>` + `assignment_results` | `assessment.submissions`, `journal.entries`, экспорт |
| Результаты ученика | `student/work_result` | `assessment.submissions`, `assessment.answers` |
| Выгрузка прогресса родителем | CSV `parent/learner/<id>/export.csv`: 9 колонок, разделитель `;`, BOM UTF-8, до 5000 попыток | `GET /api/v1/parent/children/{id}/export` (CSV/XLSX), `analytics` |
| Библиотека | статистика книг и рекомендаций | `lms.library_items`, `analytics` |
| ИИ | количество запросов, ошибки, кэш объяснений | `ai.requests`, `ai.results`, `ai.settings` |
| Аудит | `audit_log` (17 записей) | `audit.events` |
| Версия мобильного приложения | `app_release` + `app_meta` | `system.app_versions`, `GET /api/v1/app/version` |

### 2.5. Роли и доступ

| Старая роль | Новые роли | Примечание |
|---|---|---|
| `admin` | `superadmin`, `admin` | Глобальный администратор разделяется на платформенного и школьного |
| `teacher` | `teacher`, `methodologist` | Методист получает доступ к контенту |
| `student` | `student` | Сохраняется |
| `parent` | `parent` | Сохраняется |
| — | `psychologist`, `secretary` | Новые роли для психолога и делопроизводителя |

Правило: `superadmin` не привязан к школе, остальные роли обязаны иметь
`school_id`. Доступ к чужим `school_id` запрещён на уровне API.

## 3. Матрица миграции таблиц

| Старая таблица | Новый домен/таблица | Правило переноса | Статус |
|---|---|---|---|
| `users` | `iam.users` | Прямой перенос, `role` → code, `patronymic` → `middle_name`, добавить `locale`, `preferences` | Пилот: схема готова |
| `learners` | `iam.users` + `lms.student_profiles` | Ученик без аккаунта становится профилем; PIN-хэш не переносится, ребёнок входит через аккаунт/код | Запланировано |
| `learner_accounts` | `iam.user_relations`/`lms.student_profiles` | Связь ученического профиля с аккаунтом | Запланировано |
| `parent_children` | `iam.user_relations` | `relation` → `relation_type`, добавить `is_primary` | Запланировано |
| `api_tokens` | `iam.sessions`/`iam.api_tokens` | Хэши токенов; старые токены отозвать | Запланировано |
| `cities` | `org.regions` + `org.cities` | Регион из строки, город отдельно; название в JSONB | Запланировано |
| `schools` | `org.schools` | `director` → `director_name`, название в JSONB | Пилот: схема готова |
| `school_classes` | `org.classes` | `grade` → `number`, `teacher_id` → `curator_id`, уникальность сохранить | Пилот: схема готова |
| `class_students` | `org.class_students` | Добавить `left_at`, `status`; проверять активные дубли | Пилот: `org.class_memberships` |
| `subjects` | `lms.subjects` | `slug` → `code`, `name` в JSONB (`ru`, `be`, `en`) | API: чтение |
| `topics` | `lms.topics` | `grade` → `class_number`, `content_json` → `lessons`, сохранить `kind`, `order_index` | API: чтение |
| `methods` | `lms.methods` + `lms.lesson_blocks` | Объяснения и шаги → `lms.methods`, блоки урока → `lms.lesson_blocks` | API: чтение |
| `textbooks` | `lms.textbooks` + `lms.files` | PDF в объектное хранилище, метаданные в БД, checksum | API: чтение |
| `textbook_topics` | `lms.textbook_topics` | `page_start/page_end` → `page_from/page_to` | API: чтение |
| `courses` | `lms.courses` | Добавить `school_id`, `owner_id`, статус | API: чтение |
| `course_topics` | `lms.course_topics` | Прямой перенос с `enabled` | API: чтение |
| `course_classes` | `lms.course_classes` | Прямой перенос | API: чтение |
| `assignments` | `assessment.quizzes` + `assessment.assignments` + `assessment.questions` + `assessment.answer_options` | Работа разделяется на шаблон теста и назначение классу/ученику | API: чтение/запись |
| `assignment_results` | `assessment.submissions` + `assessment.answers` | `answers` JSONB разложить по вопросам, сохранить score/max | API: чтение/запись |
| `schedules` | `journal.lesson_schedule` | `weekday` + `lesson_no` + время → интервал; добавить `valid_from/to` | Запланировано |
| `library_books` | `lms.library_items` | `owner_id`, предмет, класс, описание | Запланировано |
| `library_book_classes` | `lms.library_item_classes` | Прямой перенос | Запланировано |
| `library_recommendations` | `lms.recommendations` | `target_kind` → `target_type`, `student_id/class_id` | Запланировано |
| `library_recommendation_done` | `lms.recommendation_status` | `done_at` + `student_id` | Запланировано |
| `app_notifications` | `communication.notifications` | `kind` → `type`, добавить канал и `read_at` | Запланировано |
| `audit_log` | `audit.events` | Прямой перенос, `details` в JSONB | Пилот: схема готова |
| `ai_settings` | `ai.settings` | Ключ API шифровать, не хранить в открытом виде | Запланировано |
| `ai_explanations` | `ai.results` | Кэш объяснений с моделью и темой | Запланировано |
| `ai_quizzes` | `assessment.quizzes` (ai_generated) | Сохранить payload и модель | Запланировано |
| `ai_requests` | `ai.requests` | Прямой перенос, добавить latency/tokens | Запланировано |
| `app_meta` | `system.settings` | Ключ-значение → JSONB | Запланировано |
| `attempts` | `assessment.attempts`/`analytics.events` | Сохранить все попытки, `mode`, `hints_used` | Запланировано |
| `topic_progress` | `analytics.topic_progress` | Агрегат по ученику и теме | Запланировано |
| `method_progress` | `analytics.method_progress` | Агрегат по методике | Запланировано |
| `badges` | `lms.badges`/`lms.user_badges` | Справочник + выдача | Запланировано |
| `daily_answers` | `analytics.daily_answers` | Прямой перенос | Запланировано |
| `play_sessions` | `assessment.play_sessions` | Прямой перенос, состояние раунда в JSONB | Запланировано |

## 4. Матрица миграции API

| Старый API | Новый API | Изменение |
|---|---|---|
| `POST /api/v1/auth/login` | `POST /api/v1/auth/login` | JSON, JWT access + refresh, без cookie-сессии |
| `GET /api/v1/auth/me` | `GET /api/v1/auth/me` | JWT Bearer |
| `POST /api/v1/auth/logout` | `POST /api/v1/auth/logout` | Отзыв refresh-токена |
| — | `POST /api/v1/auth/refresh` | Новый: ротация refresh-токена |
| `GET /api/v1/meta` | `GET /api/v1/meta` | Версия, языки, feature flags |
| `GET /api/v1/topics` | `GET /api/v1/lms/topics` | Пагинация, фильтры, JSONB-локали |
| `POST /api/v1/play/*` | `POST /api/v1/assessment/play/*` | Сохранить контракт для Flutter после адаптера |
| `GET /api/v1/admin/stats` | `GET /api/v1/admin/stats` | Обязательный `school_id` для superadmin |
| `GET /api/v1/admin/orgs` | `GET /api/v1/org/*` | Разделение на школы/классы |
| `GET /api/v1/parent/children/<id>/export` | `GET /api/v1/parent/children/{id}/export` | CSV/XLSX, потоковая выгрузка |
| `GET /api/v1/app/version` | `GET /api/v1/app/version` | Сохранить совместимость для Android |

Старые пути, необходимые Android-клиенту, поддерживаются через адаптер или
редирект после согласования. Период параллельной работы — не менее одного
релиза.

## 5. Порядок миграции

1. Заморозить эталонную копию SQLite и снять контрольные суммы.
2. Развернуть пустую PostgreSQL и применить Alembic.
3. Перенести справочники: регионы, города, школы, классы, предметы.
4. Перенести пользователей и связи родитель-ребёнок.
5. Перенести контент: темы, методики, учебники, файлы.
6. Перенести работы, результаты, попытки, прогресс, бейджи.
7. Перенести библиотеку, уведомления, ИИ-кэш, аудит.
8. Сверить количества, суммы, выборочные записи и отчёты.
9. Провести функциональную приёмку по ролям.
10. Включить новый контур для пилотной школы; старый оставить доступным.

## 6. Контроль качества миграции

| Проверка | Критерий |
|---|---|
| Количество строк | Совпадение по каждой таблице, кроме явно исключённых |
| Уникальность | Нет дублей логинов, классов, связей, тем |
| Ссылочная целостность | Нет «сирот» по FK |
| Пароли | Все пользователи могут войти или получают ссылку сброса |
| Файлы | Количество и checksum PDF совпадают |
| Отчёты | CSV родителя, сводка администратора, результаты работ совпадают |
| Права | Каждая роль видит только свои данные и свою школу |
| Производительность | p95 основных запросов не хуже старого контура |
| Аудит | Все административные действия пишутся в `audit.events` |

## 7. Текущий статус

| Компонент | Статус |
|---|---|
| Инвентаризация таблиц, маршрутов, шаблонов, ролей, отчётов | **Выполнено** |
| Карта миграции | **Выполнено, версия 0.2** |
| FastAPI skeleton, `/health`, OpenAPI | **Выполнено** |
| SQLAlchemy 2.0 async + Alembic | **Выполнено** |
| JWT, RBAC, multi-tenancy по `school_id` | **Выполнено (пилот)** |
| Миграции доменов `lms`, `assessment`, `journal`, `analytics`, `ai`, `communication` | **Выполнено** |
| Импорт старой SQLite (`app.db.import_legacy`) | **Реализован, требует прогона на Stage** |
| API учебного контента (`/lms/*`) | **Выполнено (чтение)** |
| API тестов и работ (`/assessment/*`) | **Выполнено (создание, назначение, сдача, результаты)** |
| Перенос данных старого контура | **В процессе** |
| React-интерфейс | **Не начато** |
| Flutter-клиенты | **Не начато** |

## 8. Риски и меры

| Риск | Мера |
|---|---|
| Скрытые зависимости в шаблонах и JS | Трассировка маршрутов, покрытие API-тестами |
| Различие бизнес-логики оценок | Зафиксировать 10-балльную шкалу и правила округления в тестах |
| Потеря PDF и изображений | Перенос в S3, checksum, проверка количества |
| Дубли логинов при слиянии | Предварительный отчёт конфликтов, ручное разрешение |
| Простой при переключении | Параллельный контур, переключение после приёмки |
| Утечка ПДн | Минимизация, шифрование, аудит, согласие, доступ по ролям |

## 9. Критерии готовности миграции

- Все старые функции доступны в новом контуре или имеют согласованный аналог.
- Данные перенесены без потерь; расхождения объяснены и подписаны.
- Роли и права проверены по матрице.
- Старые URL/API, нужные мобильному клиенту, имеют совместимые редиректы.
- Отчёты сверены с эталоном.
- Проведена приёмка по ролям и подписан акт миграции.
- Старый контур остаётся доступным до окончания параллельной эксплуатации.
