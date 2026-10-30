# Active Context

## Текущий этап
**Этап 2.6. Веб-клиент и публикация на пилоте.**
Дата: 2026-10-30.

## Что сделано
1. Backend этапа 2.5: 14 сервисов с манифестами, активации по 5 уровням,
   групповая модель прав (GBAC), API групп/сервисов/личного доступа.
2. Пилотная PostgreSQL: миграция `0002_groups_permissions_services`,
   73 права, 14 сервисов, 14 активаций, 30 групп, 215 выдач.
3. Создан React-клиент (`frontend/`): React 18, TypeScript strict, Vite,
   TailwindCSS, React Router, Axios.
4. Реализованы экраны:
   - вход и восстановление JWT-сессии;
   - дашборд с реальными показателями школы, выбором школы для
     супер-администратора, статусом `/health`, сервисами и группами;
   - группы и права: фильтры, создание группы, карточка группы, выдача
     `allow`/`deny`, участники, дочерние группы;
   - каталог сервисов: 14 карточек, уровни «республика / школа», поиск,
     категории, зависимости, переключатели активации;
   - профиль: группы, права по сервисам, запреты;
   - универсальные карточки сервисов и 404.
5. Динамическое меню строится из `/me/services`; административные разделы —
   из `/me/permissions`; маршруты защищены `PermissionGate`.
6. Исправлены дефекты, найденные при визуальной проверке:
   - 500 в карточке группы из-за ленивой загрузки связей дочерних групп;
   - CORS `/health` (переход на Vite-прокси / относительный URL);
   - конфликт Tailwind-классов (подключён `tailwind-merge`);
   - перекрывающий таблицу плавающий бейдж версии.
7. FastAPI умеет раздавать собранный `frontend/dist`: `/` и клиентские
   маршруты отдают SPA, `/assets/*` — статику; API, `/health`, `/docs`,
   `/openapi.json`, `/robots.txt` не затрагиваются. Если `dist` отсутствует,
   `/` возвращает прежний JSON.
8. Проверки: backend `88 passed`, `ruff` чистый; frontend `npm run typecheck`
   и `npm run build` успешны.
9. Документация обновлена до 0.7: ШК-03-06 (веб-клиент), ШК-10-11 (отчёт о
   тестировании), реестр, журнал изменений, операции, генератор DOCX.

## Что происходит сейчас
- Пилот опубликован на `https://school-platform-v2.alwaysdata.net`:
  backend, React-клиент, JWT-ключи и `.env` перенесены на новый профиль.
- Новый хост подключён к существующей БД `virusadk_school_platform`.
- API проверен: 73 allow, 0 deny, 1 группа, 11 сервисов из 14, 30 групп,
  школа `pilot-school`.
- Визуально проверены вход, дашборд, группы, каталог сервисов и профиль;
  ошибок в консоли нет.
- В API добавлены проверки активации сервиса и групповых прав для journal,
  assessment, library, lms; 96 тестов зелёные, Ruff чистый.
- Старый сайт `virusadk.alwaysdata.net` не изменялся.

## Фактические параметры пилота
- Профиль: `school-platform-v2`.
- Домен: `https://school-platform-v2.alwaysdata.net`.
- SSH: `school-platform-v2@ssh-school-platform-v2.alwaysdata.net`.
- Backend: `/home/school-platform-v2/school-platform-v2/backend`.
- Frontend dist: `/home/school-platform-v2/school-platform-v2/frontend/dist`.
- Venv: `/home/school-platform-v2/.virtualenvs/school-platform`.
- Тип сайта: **Python WSGI (uWSGI 2.0.31)**.
- Точка входа: `backend/__init__.py` — эквивалент
  `deploy/alwaysdata/wsgi_entry.py`, адаптер `a2wsgi`.
- Working directory в панели: `school-platform-v2/backend`
  (относительно `/home/school-platform-v2`).
- Альтернатива: User program + `uvicorn app.main:app`.
- PostgreSQL: `postgresql-virusadk.alwaysdata.net:5432/virusadk_school_platform`.
- Кэш сайта отключён; WAF basic; Force HTTPS включён.
- `robots.txt` закрывает пилот от индексации; security headers включены.

## Запреты
- Не трогать работающий проект `C:\Users\adamrv\Documents\edu-math`.
- Не менять его базу и не перезапускать его процессы.
- Не менять сайт `virusadk.alwaysdata.net`.
- Не переносить реальные ПДн в новую систему без согласованной политики.
- Не коммитить `.env`, `backend/.env`, `secrets/`, `.tools/`, пароли,
  токены и приватные ключи.

## Следующая задача
1. Развернуть backend с проверками доступа и перезапустить uWSGI в панели.
2. Перезапустить seed, чтобы школьная группа родителей получила
   `assessment.results.read`.
3. Перевести пользователей пилота в группы; проверить, что мост
   `LEGACY_ROLE_PERMISSIONS` не используется.
4. Подключить проверки к analytics, communication, documents, safety.
5. Полноценные экраны журнала, библиотеки, LMS и оценивания.
6. Автоматизированные E2E-тесты (Playwright), i18n, Redis-кеш прав и RLS.
7. Решить, оставить ли WSGI-адаптер или перевести сайт на Uvicorn.
8. Проверить async pool/lifespan под uWSGI нагрузкой.

Результат фиксировать в `progress.md`, `docs/02-tz/05-karta-migracii.md` и
журнале изменений.
