# API пилотного контура

| Параметр | Значение |
|---|---|
| Код документа | ШК-03-03 |
| Версия | 0.1 |
| Статус | Рабочий |
| Дата | 27.10.2026 |
| Базовый URL (пилот) | `https://school-platform-v2.185.31.40.24.nip.io` |
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

## 5. Системные

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | liveness/readiness + проверка БД |
| GET | `/api/v1/health` | то же в версионированном пространстве |
| GET | `/api/v1/meta` | версия, языки, feature flags |
| GET | `/` | краткая информация о сервисе |

`/health` возвращает `200`, если БД доступна, и `503` со статусом `degraded`,
если нет. В ответе нет секретов, только `jwt_ready` и версия.

## 6. Роли

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

## 7. Совместимость со старым API

Старый контур `edu-math` имеет `/api/v1` для Android. На время параллельной
эксплуатации сохраняются совместимые маршруты или адаптер. Полный перечень
соответствия — в документе ШК-02-05 «Карта миграции».

## 8. Ограничения пилота

- Нет rate limiting на уровне приложения (включён флаг, middleware — следующий этап).
- Нет Redis-кэша и фоновых задач в текущем контуре.
- Пароль супер-администратора хранится только в `.env` пилота.
- Для промышленного контура нужны WAF, аудит-логи в защищённом хранилище,
  резервное копирование и сертифицированный ЦОД.
