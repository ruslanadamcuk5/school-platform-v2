# Отчёт о тестировании групп, прав и реестра сервисов

| Параметр | Значение |
|---|---|
| Код документа | ШК-10-10 |
| Версия | 0.1 |
| Статус | Рабочий |
| Дата | 30.10.2026 |
| Объект испытаний | `iam.groups`, `iam.group_permissions`, `system.services`, `system.service_activations`, `/api/v1/groups/*`, `/api/v1/services/*`, `/api/v1/me/*` |
| Стенд | Локальная среда разработки, Windows, Python 3.13 |
| Инструменты | pytest, ruff, Alembic offline SQL |

## 1. Цель
Подтвердить: права назначаются группам; наследование и конфликты работают
детерминированно; администратор не выходит за свою область; сервисы
включаются и отключаются по иерархии; ядро нельзя отключить; каждый сервис
запускается отдельным приложением.

## 2. Состав автоматических тестов

### 2.1. Разрешение прав и активаций
Файл: `backend/tests/test_access_resolution.py`.

| ID | Тест | Проверяемое поведение | Результат |
|---|---|---|---|
| GB-T01 | `test_most_specific_scope_wins` | Школьный `deny` перекрывает республиканский `allow` | Пройден |
| GB-T02 | `test_class_allow_overrides_school_deny` | Классный `allow` перекрывает школьный `deny` | Пройден |
| GB-T03 | `test_deny_wins_on_the_same_depth` | При равной глубине побеждает `deny` | Пройден |
| GB-T04 | `test_unknown_permission_is_not_granted` | Неизвестное право не выдаётся | Пройден |
| GB-T05 | `test_legacy_bridge_is_explicit` | Переходный мост ролей работает предсказуемо | Пройден |
| GB-T06 | `test_scope_within_rejects_unrelated_scope` | Чужая область отклоняется | Пройден |
| SV-T01 | `test_core_service_is_always_enabled` | Ядровый сервис всегда включён | Пройден |
| SV-T02 | `test_service_default_applies_without_activation` | Без активации действует значение по умолчанию | Пройден |
| SV-T03 | `test_school_can_disable_country_enabled_service` | Школа отключает включённый на стране сервис | Пройден |
| SV-T04 | `test_school_can_enable_country_disabled_service` | Школа включает отключённый на стране сервис | Пройден |
| REG-T01 | `test_registry_permissions_are_unique_and_namespaced` | Права уникальны и принадлежат своему сервису | Пройден |

### 2.2. API групп
Файл: `backend/tests/test_groups_api.py`.

| ID | Тест | Проверяемое поведение | Результат |
|---|---|---|---|
| GB-A01 | `test_group_out_counts_members_and_permissions` | Счётчики участников и прав | Пройден |
| GB-A02 | `test_group_detail_sorts_members_and_permissions` | Сортировка участников и прав | Пройден |
| GB-A03 | `test_country_scope_uses_fixed_identifier` | Страна использует нулевой UUID | Пройден |
| GB-A04 | `test_non_country_scope_requires_identifier` | Без `scope_id` — 422 | Пройден |
| GB-A05 | `test_groups_endpoints_are_published` | Маршруты групп и `/me/*` в OpenAPI | Пройден |

### 2.3. API сервисов
Файл: `backend/tests/test_services_api.py`.

| ID | Тест | Проверяемое поведение | Результат |
|---|---|---|---|
| SV-A01 | `test_country_scope_is_resolved` | Страна разрешается в нулевой UUID | Пройден |
| SV-A02 | `test_unknown_scope_is_rejected` | Неизвестная область — 422 | Пройден |
| SV-A03 | `test_fallback_catalog_contains_every_manifest` | Каталог содержит все манифесты | Пройден |
| SV-A04 | `test_get_service_uses_manifest_fallback` | Карточка сервиса из манифеста | Пройден |
| SV-A05 | `test_core_service_cannot_be_disabled` | Ядро нельзя отключить — 409 | Пройден |
| SV-A06 | `test_optional_service_can_be_enabled_for_country` | Включение сервиса для страны | Пройден |
| SV-A07 | `test_unknown_service_is_rejected` | Неизвестный сервис — 404 | Пройден |
| SV-A08 | `test_effective_services_for_country_returns_catalog` | Действующие сервисы страны | Пройден |

### 2.4. Отдельный запуск сервисов
Файл: `backend/tests/test_service_app.py`.

| ID | Тест | Проверяемое поведение | Результат |
|---|---|---|---|
| MS-T01 | `test_standalone_library_app_mounts_only_library_routes` | Приложение `library` не содержит чужих маршрутов | Пройден |
| MS-T02 | `test_standalone_system_app_mounts_service_catalog` | Приложение `system` содержит каталог сервисов | Пройден |
| MS-T03 | `test_unknown_service_is_rejected` | Неизвестный сервис — ошибка запуска | Пройден |
| MS-T04 | `test_every_registered_manifest_can_be_started` | Все 14 манифестов запускаются | Пройден |

## 3. Проверка миграции
- `alembic upgrade head --sql` — SQL для `0002_groups_permissions_services`
  формируется без ошибок.
- Текущая версия пилотной БД: `2c27d5a2ed88`.
- Миграция `0002` **не применена** к пилоту; требуется подтверждение и
  резервная копия.

## 4. Команды запуска

```powershell
cd C:\Users\adamrv\Documents\school-platform-v2
.venv\Scripts\python.exe -m ruff check backend/app backend/tests
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

## 5. Результаты

| Проверка | Результат |
|---|---|
| Ruff | `All checks passed!` |
| Pytest | `87 passed, 2 warnings` |
| Новые тесты групп/сервисов | 25 |
| Критичные дефекты | Не выявлены |

Предупреждения относятся к `python-jose` (`datetime.utcnow()`), не влияют на
функциональность.

## 6. Сценарии для ручной проверки на Stage
1. Создать школьную группу «Учителя», добавить учителя, выдать
   `journal.grades.write`.
2. Проверить `GET /me/permissions`: право действует.
3. Создать классную группу, запретить `journal.grades.write` через `deny`.
4. Проверить, что ученик класса не может выставлять оценки.
5. Перевести учителя в группу «Администрация школы» и проверить новый набор
   прав.
6. Отключить `library` для школы при включённом на стране — проверить
   `/me/services`.
7. Попробовать отключить `iam` — ожидается `409`.
8. Попробовать управлять группой чужой школы — ожидается `403`.
9. Запустить `SERVICE_CODE=library uvicorn app.service_app:create_service_app
   --factory` и проверить `/health`, `/openapi.json`.
10. Проверить аудит изменений групп и активаций.

## 7. Вывод
Модель групп, иерархическое разрешение прав, реестр сервисов, активации и
отдельный запуск сервисов реализованы и покрыты тестами. Для приёмки нужно
применить миграцию `0002` на Stage, прогнать seed и выполнить сценарии с
реальной PostgreSQL.
