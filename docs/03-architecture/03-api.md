# API пилотного контура

| Параметр | Значение |
|---|---|
| Код документа | ШК-03-03 |
| Версия | 0.7 |
| Статус | Рабочий |
| Дата | 30.10.2026 |
| Базовый URL (пилот) | `https://school-platform-v2.alwaysdata.net` |
| OpenAPI | `/openapi.json`, `/docs`, `/redoc` |

## 1. Принципы

- REST, JSON UTF-8.
- Версия в пути: `/api/v1`.
- Аутентификация: `Authorization: Bearer <access_token>`.
- Access-токен: JWT RS256, 30 минут.
- Refresh-токен: opaque, 30 дней, хранится в БД только как SHA-256.
- Ротация refresh-токена при обновлении; старый токен отзывается.
- Мультитенантность: `school_id` в JWT и в запросах администратора.
- Ошибки: `{"detail": "..."}`; коды 400/401/403/404/409/422/503.
- Каждый ответ содержит `X-Request-ID`.
- Доменные маршруты `journal`, `assessment`, `library` и `lms` проверяют
  включённость сервиса в области пользователя и наличие группового права;
  при отказе возвращается `403` с указанием сервиса или кода права.
- Если сервис отключён на более конкретном уровне иерархии, его API
  недоступно, даже если право выдано группой.

## 2. Аутентификация

### 2.1. Вход

`POST /api/v1/auth/login`

```json
{
  "login": "admin",
  "password": "***"
}
```

Ответ:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "opaque-token",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_expires_in": 2592000,
  "user": {
    "id": "uuid",
    "school_id": null,
    "login": "admin",
    "role": "superadmin",
    "full_name": "Администратор Платформы"
  }
}
```

### 2.2. Обновление

`POST /api/v1/auth/refresh`

```json
{"refresh_token": "opaque-token"}
```

Возвращает новую пару. Старый refresh-токен становится недействительным.

### 2.3. Выход

`POST /api/v1/auth/logout` с access-токеном и телом
`{"refresh_token": "opaque-token"}`. Refresh-токен отзывается.

### 2.4. Текущий пользователь

`GET /api/v1/auth/me` с access-токеном.

## 3. Организация и тенантность

| Метод | Путь | Правило |
|---|---|---|
| GET | `/api/v1/org/schools` | superadmin — все; остальные — своя школа |
| GET | `/api/v1/org/schools/{id}` | только своя школа, superadmin — любая |
| GET | `/api/v1/org/classes?school_id=` | своя школа; superadmin обязан передать `school_id` |
| GET | `/api/v1/org/classes/{id}` | класс должен принадлежать доступной школе |

Для школьного пользователя `school_id` в query игнорируется, если совпадает, и
даёт `403`, если отличается. Для superadmin отсутствие `school_id` даёт `400`.

## 4. Администрирование

| Метод | Путь | Роли |
|---|---|---|
| GET | `/api/v1/admin/stats?school_id=` | `superadmin`, `admin` |
| GET | `/api/v1/admin/users?school_id=&role=&search=&limit=&offset=` | `superadmin`, `admin` |
| POST | `/api/v1/admin/users?school_id=` | `superadmin`, `admin` |
| GET | `/api/v1/admin/audit?school_id=&limit=&offset=` | `superadmin`, `admin` |

Создание пользователя:

```json
{
  "login": "teacher.ivanova",
  "password": "StrongPass123!",
  "role": "teacher",
  "first_name": "Ирина",
  "last_name": "Иванова",
  "email": "ivanova@example.by"
}
```

Пароль хэшируется bcrypt (12 rounds). `must_change_password=true` для новых
учётных записей. Логин и email уникальны без учёта регистра (`citext`).

## 4.1. Группы, права и сервисы

### 4.1.1. Группы

| Метод | Путь | Право | Назначение |
|---|---|---|---|
| GET | `/api/v1/groups` | `iam.groups.read` | Группы в доступных областях |
| POST | `/api/v1/groups` | `iam.groups.write` | Создать группу |
| GET | `/api/v1/groups/{id}` | `iam.groups.read` | Группа с участниками и правами |
| PATCH | `/api/v1/groups/{id}` | `iam.groups.write` | Изменить группу |
| DELETE | `/api/v1/groups/{id}` | `iam.groups.write` | Отключить группу |
| POST | `/api/v1/groups/{id}/members` | `iam.groups.write` | Добавить пользователей |
| DELETE | `/api/v1/groups/{id}/members/{user_id}` | `iam.groups.write` | Исключить пользователя |
| PUT | `/api/v1/groups/{id}/permissions/{code}` | `iam.groups.write` | Выдать право (`allow`/`deny`) |
| DELETE | `/api/v1/groups/{id}/permissions/{code}` | `iam.groups.write` | Снять право |
| GET | `/api/v1/groups/permissions` | `iam.permissions.read` | Каталог прав |
| GET | `/api/v1/me/permissions` | аутентификация | Действующие права пользователя |
| GET | `/api/v1/me/services` | аутентификация | Доступные сервисы для навигации |

Создание группы:

```json
{
  "code": "teachers",
  "name": "Учителя школы",
  "category": "teachers",
  "scope_type": "school",
  "scope_id": "uuid",
  "parent_id": "uuid"
}
```

Для `scope_type=country` поле `scope_id` можно не передавать: используется
`00000000-0000-0000-0000-000000000000`.

Выдача права:

```http
PUT /api/v1/groups/{group_id}/permissions/journal.grades.write
{"effect": "allow", "expires_at": null}
```

### 4.1.2. Сервисы

| Метод | Путь | Право | Назначение |
|---|---|---|---|
| GET | `/api/v1/services` | `system.services.read` | Каталог сервисов |
| GET | `/api/v1/services/{code}` | `system.services.read` | Карточка сервиса |
| GET | `/api/v1/services/effective?scope_type=&scope_id=` | `system.services.read` | Действующие сервисы области |
| GET | `/api/v1/services/{code}/activation?scope_type=&scope_id=` | `system.services.read` | Активация в области |
| PUT | `/api/v1/services/{code}/activation?scope_type=&scope_id=` | `system.services.write` | Включить/отключить |
| DELETE | `/api/v1/services/{code}/activation?scope_type=&scope_id=` | `system.services.write` | Снять активацию, вернуть наследование |

```http
PUT /api/v1/services/library/activation?scope_type=school&scope_id=uuid
{"enabled": false, "config": {}}
```

Ядровые сервисы (`system`, `iam`, `org`, `audit`) отключить нельзя — `409`.
Проверка области: администратор действует только внутри своей области и её
потомков.

## 5. Учебный контент (LMS)

Все маршруты требуют access-токен. Контент предметов, тем и учебников общий
для платформы; курсы ограничены школой пользователя.

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/v1/lms/subjects` | Список активных предметов |
| GET | `/api/v1/lms/subjects/{id}` | Карточка предмета |
| GET | `/api/v1/lms/topics?subject_id=&grade=&search=&limit=&offset=` | Каталог тем с фильтрами и пагинацией |
| GET | `/api/v1/lms/topics/{id}` | Тема с методиками, уроками и учебниками |
| GET | `/api/v1/lms/topics/by-code/{code}` | Тема по коду (совместимость с Android) |
| GET | `/api/v1/lms/textbooks?subject_id=&grade=&search=&limit=&offset=` | Каталог учебников |
| GET | `/api/v1/lms/textbooks/{id}` | Учебник со связями «тема — страницы» |
| GET | `/api/v1/lms/courses?school_id=&subject_id=&grade=&mine=` | Курсы школы; `mine=true` — курсы учителя |
| GET | `/api/v1/lms/courses/{id}?school_id=` | Курс с темами и классами |

Правила:
- `school_id` обязателен для `superadmin`, для школьных ролей берётся из токена.
- Попытка открыть курс другой школы возвращает `403`.
- Список тем отдаёт только темы со статусом `active`.
- `limit` — от 1 до 200, `offset` — от 0.

## 6. Тесты, работы и результаты (assessment)

| Метод | Путь | Роли | Назначение |
|---|---|---|---|
| POST | `/api/v1/assessment/quizzes` | teacher, methodologist, admin, superadmin | Создать тест с вопросами и вариантами |
| GET | `/api/v1/assessment/quizzes?subject_id=&class_number=&status=&mine=` | staff | Список тестов школы |
| GET | `/api/v1/assessment/quizzes/{id}` | staff | Тест с правильными ответами |
| PATCH | `/api/v1/assessment/quizzes/{id}` | автор, methodologist, admin | Изменить название, статус, лимиты |
| POST | `/api/v1/assessment/assignments` | teacher, methodologist, admin | Назначить тест классу или ученику |
| GET | `/api/v1/assessment/assignments` | все роли | Работы: учитель — свои, ученик — доступные, родитель — детей |
| GET | `/api/v1/assessment/assignments/{id}` | все роли | Карточка работы; родитель передаёт `student_id` |
| POST | `/api/v1/assessment/assignments/{id}/publish` | автор, admin | Опубликовать |
| POST | `/api/v1/assessment/assignments/{id}/close` | автор, admin | Закрыть |
| DELETE | `/api/v1/assessment/assignments/{id}` | автор, admin | Архивировать (без физического удаления) |
| POST | `/api/v1/assessment/assignments/{id}/submit` | student | Сдать работу, автопроверка |
| GET | `/api/v1/assessment/assignments/{id}/result` | student | Последний результат |
| POST | `/api/v1/assessment/assignments/{id}/retry` | student | Новая попытка, если лимит не исчерпан |
| GET | `/api/v1/assessment/assignments/{id}/results` | автор, admin | Результаты класса/учеников |

Правила:
- `school_id` обязателен для `superadmin`, для школьных ролей берётся из токена.
- Ученик видит только опубликованные работы, которые уже начались и назначены
  его классу или лично ему.
- Родитель видит работы и результаты только своих детей; для карточки работы
  обязателен `student_id`.
- Автопроверка поддерживает выбор одного/нескольких вариантов, число, дробь,
  смешанное число, время, текст с альтернативами, чтение темы и диктант
  (сходство ≥ 60 %).
- Просроченная сдача разрешена и помечается `late=true`.
- Повторная попытка создаёт новую запись `assessment.submissions`; история
  попыток сохраняется.
- Идемпотентность сдачи обеспечивается `operation_id`.
- Удаление работы заменено архивированием (`status=archived`) для сохранения
  аудита.

## 7. Журнал: расписание, оценки и посещаемость

| Метод | Путь | Роли | Назначение |
|---|---|---|---|
| GET | `/api/v1/journal/classes` | staff, student, parent | Классы, доступные в журнале |
| GET | `/api/v1/journal/classes/{id}/students` | staff | Ученики класса для выставления оценок |
| GET | `/api/v1/journal/schedule?class_id=&student_id=&on_date=` | все роли | Недельное расписание |
| POST | `/api/v1/journal/schedule` | teacher, methodologist, admin | Добавить или заменить урок |
| PATCH | `/api/v1/journal/schedule/{id}` | teacher, methodologist, admin | Изменить урок |
| DELETE | `/api/v1/journal/schedule/{id}` | teacher, methodologist, admin | Удалить урок |
| GET | `/api/v1/journal/entries?class_id=&subject_id=&student_id=&date_from=&date_to=` | все роли | Записи журнала |
| POST | `/api/v1/journal/entries` | teacher, methodologist, admin | Выставить оценку/посещаемость (upsert) |
| POST | `/api/v1/journal/entries/bulk` | teacher, methodologist, admin | Массовое выставление по классу |
| PATCH | `/api/v1/journal/entries/{id}` | teacher, methodologist, admin | Изменить запись |
| DELETE | `/api/v1/journal/entries/{id}` | teacher, methodologist, admin | Удалить запись |
| GET | `/api/v1/journal/summary?class_id=&subject_id=&student_id=&date_from=&date_to=` | все роли | Средний балл и посещаемость |

Правила:
- Расписание задаётся недельной сеткой: `day_of_week` 1–7, `lesson_no` 1–12,
  `start_time < end_time`, период действия `valid_from/to`.
- Учитель видит и редактирует классы, где он классный руководитель, указан
  в `org.teacher_subjects` или ведёт хотя бы один урок в расписании.
- Ученик видит расписание и записи только своих классов; родитель — только
  выбранного ребёнка (`student_id` обязателен).
- Оценка — целое число 1–10; посещаемость: `present`, `absent`, `sick`,
  `late`, `excused`.
- Запись журнала upsert-ится по `class_id + subject_id + student_id +
  lesson_date`; повторная отправка обновляет оценку/посещаемость.
- Сводка считает количество записей, средний балл (2 знака) и количество
  отметок каждого типа посещаемости.
- Все запросы ограничены `school_id`; `superadmin` обязан передать `school_id`.

## 8. Библиотека

| Метод | Путь | Роли | Назначение |
|---|---|---|---|
| GET | `/api/v1/library` | все роли | Книги, рекомендации и статистика пользователя |
| GET | `/api/v1/library/books/{id}` | по доступу | Карточка книги, темы и рекомендации ученика |
| POST | `/api/v1/library/recommendations/{id}/done` | student | Отметить рекомендацию выполненной |
| GET | `/api/v1/library/manage` | teacher, methodologist, admin | Книги учителя, классы, ученики и предметы |
| POST | `/api/v1/library/books` | teacher, methodologist, admin | Добавить пособие в библиотеку |
| PATCH | `/api/v1/library/books/{id}` | владелец, admin | Изменить книгу и доступ классов |
| DELETE | `/api/v1/library/books/{id}` | владелец, admin | Удалить книгу из библиотеки |
| POST | `/api/v1/library/books/{id}/recommend` | владелец, admin | Рекомендовать книгу/тему классу или ученикам |
| GET | `/api/v1/library/recommendations` | teacher, methodologist, admin | Отправленные рекомендации и прогресс |
| DELETE | `/api/v1/library/recommendations/{id}` | владелец, admin | Отозвать рекомендацию |
| GET | `/api/v1/library/catalog` | teacher, methodologist, admin | Пособия и темы для рекомендаций |

Правила:
- Книга создаётся из платформенного пособия (`lms.textbooks`), но хранится как
  запись библиотеки с владельцем и доступом классам.
- Учитель управляет своими книгами и классами, где он классный руководитель,
  указан в `org.teacher_subjects` или ведёт урок в расписании.
- Администратор и методист управляют книгами своей школы; `superadmin`
  обязан передать `school_id`.
- Ученик видит книги классов, в которых состоит, и книги, рекомендованные ему
  лично или его классу. Родитель — книги выбранного ребёнка.
- Рекомендация может быть на книгу целиком или на тему; повторная рекомендация
  того же адресата пропускается (`skipped`).
- Удаление книги не удаляет платформенное пособие и его темы.
- Отметка «выполнено» хранится в `lms.library_recommendation_status` и
  уникальна по паре «рекомендация + ученик».

## 9. Системные

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | liveness/readiness + проверка БД |
| GET | `/api/v1/health` | то же в версионированном пространстве |
| GET | `/api/v1/meta` | версия, языки, feature flags |
| GET | `/` | краткая информация о сервисе |

`/health` возвращает `200`, если БД доступна, и `503` со статусом `degraded`,
если нет. В ответе нет секретов, только `jwt_ready` и версия.

## 10. Роли

| Код | Назначение |
|---|---|
| `superadmin` | платформа, все школы |
| `admin` | школа |
| `methodologist` | методическая работа, контент |
| `teacher` | классы, работы, библиотека |
| `student` | обучение, работы |
| `parent` | дети, прогресс, документы |
| `psychologist` | психологическая поддержка |
| `secretary` | документы, справки |

RBAC проверяется зависимостью `require_roles`. UI скрывает недоступные
разделы, но API остаётся единственной точкой принудительной проверки.

С версии 0.6 права назначаются **группам** (`iam.groups`), а поле
`users.role` используется только как переходный мост для пользователей, ещё
не добавленных ни в одну группу. Действующие права клиент получает через
`GET /api/v1/me/permissions`, доступные сервисы — через
`GET /api/v1/me/services`. Проверка прав выполняется зависимостью
`require_permission`, проверка включённости сервиса — `require_service`.

## 11. Совместимость со старым API

Старый контур `edu-math` имеет `/api/v1` для Android. На время параллельной
эксплуатации сохраняются совместимые маршруты или адаптер. Полный перечень
соответствия — в документе ШК-02-05 «Карта миграции».

## 12. Ограничения пилота

- Нет rate limiting на уровне приложения (включён флаг, middleware — следующий этап).
- Нет Redis-кэша и фоновых задач в текущем контуре.
- Пароль супер-администратора хранится только в `.env` пилота.
- Для промышленного контура нужны WAF, аудит-логи в защищённом хранилище,
  резервное копирование и сертифицированный ЦОД.
