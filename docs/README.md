# Проектная документация ЕОРП «ВЕКТОР»

**Версия пакета:** 0.9.0 (рабочая документация этапа 2; ступени образования, компетенции, сессии и кредиты, практика и договоры, уведомления communication, заявки документов, безопасность и психологическая поддержка, обучение и аналитика, пилот на новом профиле Alwaysdata)
**Дата:** 05.11.2026
**Язык:** русский
**Статус:** рабочая документация; юридически значимые разделы требуют
согласования с юристом, ОАЦ и Министерством образования Республики Беларусь.

## Назначение пакета
Пакет описывает создание Единой образовательной республиканской платформы
«ВЕКТОР»: концепцию, техническое задание, архитектуру, модель данных,
требования безопасности, испытания, развёртывание, план работ и нормативную
базу. Документы предназначены для заказчика, разработчика, QA, ИБ, DevOps и
органов, участвующих в согласовании и приёмке.

## Навигация и экономия токенов
- `INDEX.md` — индекс всех документов: код, версия, дата, размер, путь.
- `CODEMAP.md` — карта кода: модули, классы, функции, тесты.
- `api/ENDPOINTS.md` — компактный индекс 172 путей и 232 операций из OpenAPI.
- `word/` — только готовые DOCX; не читать агенту и не использовать как
  источник. Первичны Markdown-файлы.
- Правила чтения и бюджет контекста — `AGENTS.md`, раздел 9.
- Генераторы индексов: `scripts/gen_docs_index.py`, `scripts/gen_codemap.py`,
  `scripts/gen_api_index.py`; единая проверка — `scripts/check.ps1`.

## Состав
| Код | Документ | Файл |
|---|---|---|
| ШК-00-01 | Реестр документации | `00-register/01-register-dokumentacii.md` |
| ШК-01-01 | Концепция платформы | `01-concept/01-koncepciya.md` |
| ШК-02-01 | Техническое задание | `02-tz/01-tehnicheskoe-zadanie.md` |
| ШК-02-02 | Функциональные требования по ролям | `02-tz/02-funkcionalnye-trebovaniya-po-rolyam.md` |
| ШК-02-03 | Требования к интеграциям | `02-tz/03-trebovaniya-k-integraciyam.md` |
| ШК-02-04 | Матрица соответствия требованиям | `02-tz/04-matrica-sootvetstviya.md` |
| ШК-02-05 | Карта миграции старого функционала | `02-tz/05-karta-migracii.md` |
| ШК-03-01 | Архитектура системы | `03-architecture/01-arhitektura.md` |
| ШК-03-02 | Блок-схема платформы | `03-architecture/02-blok-shema.md` |
| ШК-03-03 | API пилотного контура | `03-architecture/03-api.md` |
| ШК-03-04 | Микросервисная архитектура | `03-architecture/04-mikroservisy.md` |
| ШК-03-05 | Группы пользователей и права | `03-architecture/05-gruppy-i-prava.md` |
| ШК-03-06 | Веб-клиент и личный кабинет | `03-architecture/06-web-client.md` |
| ШК-03-07 | Обучение работе в платформе | `03-architecture/07-obuchenie-rabote-v-platforme.md` |
| ШК-03-08 | Аналитика школы | `03-architecture/08-analitika-shkoly.md` |
| ШК-03-09 | Ступени образования | `03-architecture/09-stupeni-obrazovaniya.md` |
| ШК-04-01 | Модель данных | `04-data/01-model-dannyh.md` |
| ШК-04-02 | Модель групп, прав и сервисов | `04-data/02-model-grupp-prav-i-servisov.md` |
| ШК-05-01 | Концепция информационной безопасности | `05-security/01-koncepciya-ib.md` |
| ШК-06-01 | Стратегия тестирования | `06-testing/01-strategiya-testirovaniya.md` |
| ШК-06-02 | Программа и методика испытаний | `06-testing/02-programma-i-metodika-ispytaniy.md` |
| ШК-07-01 | Развёртывание и эксплуатация | `07-operations/01-razvertyvanie-i-ekspluataciya.md` |
| ШК-08-01 | План разработки | `08-roadmap/01-plan-razrabotki.md` |
| ШК-08-02 | Детальный план работ | `08-roadmap/02-detalnyy-plan-rabot.md` |
| ШК-09-01 | Реестр нормативных документов | `09-normative/01-reestr-normativnyh-dokumentov.md` |
| ШК-10-01 | Шаблон отчёта о разработке | `10-reporting/01-shablon-otcheta-o-razrabotke.md` |
| ШК-10-02 | Шаблон отчёта о тестировании | `10-reporting/02-shablon-otcheta-o-testirovanii.md` |
| ШК-10-03 | Журнал рисков | `10-reporting/03-zhurnal-riskov.md` |
| ШК-10-04 | Журнал изменений | `10-reporting/04-zhurnal-izmeneniy.md` |
| ШК-10-05 | Отчёт о завершении этапа 0 | `10-reporting/05-otchet-o-zavershenii-etapa-0.md` |
| ШК-10-06 | Отчёт о завершении этапа 1 | `10-reporting/06-otchet-o-zavershenii-etapa-1.md` |
| ШК-10-07 | Отчёт о тестировании API LMS | `10-reporting/07-otchet-o-testirovanii-lms-api.md` |
| ШК-10-08 | Отчёт о тестировании API assessment | `10-reporting/08-otchet-o-testirovanii-assessment-api.md` |
| ШК-10-09 | Отчёт о тестировании API journal | `10-reporting/09-otchet-o-testirovanii-journal-api.md` |
| ШК-10-10 | Отчёт о тестировании групп, прав и сервисов | `10-reporting/10-otchet-o-testirovanii-groups-services.md` |
| ШК-10-11 | Отчёт о тестировании веб-клиента | `10-reporting/11-otchet-o-testirovanii-web-klienta.md` |
| ШК-10-12 | Отчёт о тестировании обучения и аналитики | `10-reporting/12-otchet-o-testirovanii-obucheniya-i-analitiki.md` |
| ШК-10-13 | Отчёт о тестировании ступеней образования | `10-reporting/13-otchet-o-testirovanii-stupeney-obrazovaniya.md` |
| ШК-10-14 | Отчёт о тестировании сессий, ведомостей и кредитов | `10-reporting/14-otchet-o-testirovanii-sessiy-i-kreditov.md` |
| ШК-10-15 | Отчёт о тестировании компетенций и матрицы компетенций | `10-reporting/15-otchet-o-testirovanii-kompetenciy.md` |
| ШК-10-16 | Отчёт о тестировании практики и договоров с предприятиями | `10-reporting/16-otchet-o-testirovanii-praktiki-i-dogovorov.md` |
| ШК-10-17 | Отчёт о тестировании уведомлений communication | `10-reporting/17-otchet-o-testirovanii-uvedomleniy.md` |
| ШК-10-18 | Отчёт о тестировании запросов документов | `10-reporting/18-otchet-o-testirovanii-zaprosov-dokumentov.md` |
| ШК-10-19 | Отчёт о тестировании сервиса безопасности и психологической поддержки | `10-reporting/19-otchet-o-testirovanii-safety.md` |
| ШК-10-20 | Отчёт об оптимизации OpenCode: экономия токенов и ускорение | `10-reporting/20-otchet-ob-optimizacii-opencode.md` |
| ШК-11-01 | Правила OpenCode и промпты | `11-opencode/01-pravila-i-prompty.md` |

Актуальный объединённый пакет DOCX:
`word/ЕОРП_ВЕКТОР_Полный_пакет_документации_v0.9.0.docx`.
Файлы без суффикса версии, `_v0.2` … `_v0.8.3` оставлены как предыдущие
версии; после закрытия их можно заменить актуальным.

## Форматы
- Markdown — рабочая версия, удобная для Git и OpenCode.
- DOCX — официальная версия для согласования и подписи.
- Исходные Markdown-файлы являются первичными; DOCX генерируются из них.

## Порядок изменения
1. Изменение вносится в Markdown.
2. Обновляется журнал изменений.
3. Документ проходит проверку владельцем.
4. Генерируется новая версия DOCX.
5. Версия фиксируется в реестре документации.
