# Модель данных

| Параметр | Значение |
|---|---|
| Код документа | ШК-04-01 |
| Версия | 0.6 |
| Статус | Рабочий |
| Дата | 04.11.2026 |

## 1. Общие принципы
- СУБД: PostgreSQL 16+.
- Первичные ключи: UUID (`gen_random_uuid()`), кроме справочников, где допустим
  BIGSERIAL.
- Временные метки: `created_at`, `updated_at` (timestamptz, UTC).
- Мягкое удаление: `deleted_at` для пользовательских сущностей.
- Версионирование: `version` (optimistic locking) для критичных записей.
- Мультитенантность: `school_id` в учебных данных; проверка на уровне API и RLS.
- Мультиязычность: JSONB `{"ru": "...", "by": "...", "en": "..."}`.
- Аудит: `created_by`, `updated_by`, отдельная таблица `audit.events`.
- Секреты и пароли: только хеши/шифротекст, никогда в открытом виде.

## 2. Схемы PostgreSQL
| Схема | Назначение |
|---|---|
| `iam` | Пользователи, роли, права, сессии, согласия |
| `org` | Регионы, города, учреждения, классы, группы, программы, учебные планы и академические профили |
| `lms` | Предметы, темы, уроки, пособия, медиа |
| `assessment` | Тесты, вопросы, работы, ответы |
| `journal` | Оценки, посещаемость, отчёты |
| `communication` | Чаты, сообщения, уведомления, звонки |
| `safety` | Психология, геолокация, инциденты |
| `documents` | Шаблоны, заявки, справки, подписи |
| `analytics` | Агрегаты, отчёты, снимки |
| `ai` | Настройки, запросы, результаты, эмбеддинги |
| `audit` | Аудит действий и события ИБ |
| `system` | Справочники, настройки, языки, версии |

## 3. IAM
### 3.1. `iam.users`
| Поле | Тип | Описание |
|---|---|---|
| id | uuid PK | Идентификатор |
| login | citext unique | Логин |
| password_hash | text | Argon2id/bcrypt |
| role_id | uuid FK | Основная роль |
| school_id | uuid FK null | Школа |
| class_id | uuid FK null | Класс (для ученика) |
| first_name, last_name, patronymic | text | ФИО |
| email | citext null | E-mail |
| phone | text null | Телефон |
| avatar_url | text null | Аватар |
| language | text | ru/by/en |
| status | text | active/blocked/pending |
| parent_code | text unique null | Код привязки родителя |
| last_login_at | timestamptz null | Последний вход |
| created_at, updated_at, deleted_at | timestamptz | Служебные |

Индексы: `login`, `email`, `school_id`, `class_id`, `parent_code`.

### 3.2. `iam.groups`, `iam.group_memberships`, `iam.permissions`, `iam.group_permissions`
- `groups`: id, code, name, description, category, scope_type, scope_id, depth,
  parent_id, is_system, is_active, meta jsonb, created_at, updated_at.
- `group_memberships`: id, group_id, user_id, assigned_by, assigned_at,
  expires_at, is_primary.
- `permissions`: id, code, name, description, service_code, category, is_system.
- `group_permissions`: id, group_id, permission_id, effect (allow/deny),
  granted_by, granted_at, expires_at.

Права назначаются только группам. Подробная модель — в ШК-04-02.

### 3.2.1. Переходное поле `iam.users.role`
Поле `role` сохраняется для совместимости и постепенного перевода. Пока
пользователь не входит ни в одну группу, действует мост
`LEGACY_ROLE_PERMISSIONS`. После добавления в группу доступ определяется
только группами.

### 3.3. `iam.user_relations`
| Поле | Тип | Описание |
|---|---|---|
| id | uuid PK | |
| parent_id | uuid FK | Родитель/опекун |
| child_id | uuid FK | Ребёнок |
| relation_type | text | mother/father/guardian/other |
| is_primary | boolean | Основной представитель |
| verified_at | timestamptz null | Подтверждение |
| created_at | timestamptz | |

### 3.4. `iam.consents`
- id, user_id, consent_type, document_version, granted_at, revoked_at, ip,
  user_agent, signature_hash.

### 3.5. `iam.sessions`
- id, user_id, refresh_token_hash, device_id, user_agent, ip, expires_at,
  revoked_at, created_at.

## 4. Org
### 4.1. `org.regions`
- id, code, name (jsonb), created_at.

### 4.2. `org.cities`
- id, region_id FK, code, name (jsonb), type (city/district), created_at.

### 4.3. `org.schools`
- id, city_id FK, code, name, short_name, institution_type, education_levels
  (jsonb), profile (jsonb), address, director, phone, email, is_active,
  deleted_at, created_at, updated_at.
- `institution_type`: `school`, `college`, `university`.
- `education_levels`: массив `primary`, `secondary`, `vocational`, `higher`.
- `profile`: лицензии, аккредитации, реквизиты и дополнительные поля.

### 4.4. `org.classes`
- id, school_id FK, grade (1–11), letter, education_level, program_id FK null,
  course_year, profile (jsonb), academic_year, homeroom_teacher_id FK null,
  is_active, deleted_at, created_at, updated_at.
- Unique: (school_id, grade, letter, academic_year, deleted_at).
- `education_level` определяет ступень; `program_id` и `course_year`
  используются в колледжах и вузах.

### 4.5. `org.class_memberships`
- id, class_id FK, user_id FK, role_in_class, joined_at, left_at.
- Unique active: (class_id, user_id) where left_at is null.

### 4.6. `org.teacher_subjects`
- id, teacher_id FK, subject_id FK, school_id FK, class_id FK null, workload_hours.

### 4.7. `org.education_programs`
- id, institution_id FK, code, name, education_level, qualification,
  duration_years, profile (jsonb), is_active, deleted_at, created_at,
  updated_at.
- Unique: (institution_id, code).
- Программа доступна только для `vocational` и `higher`.

### 4.8. `org.student_academic_profiles`
- id, user_id FK unique, institution_id FK, program_id FK null, group_id FK
  null, course_year, record_book_number, funding_type, enrollment_year,
  academic_status, profile (jsonb), created_at, updated_at.
- `funding_type`: `budget`, `paid`, `target`, `other`.
- `academic_status`: `active`, `academic_leave`, `expelled`, `graduated`.

### 4.9. `org.staff_academic_profiles`
- id, user_id FK unique, institution_id FK, department, position,
  academic_degree, academic_title, profile (jsonb), created_at, updated_at.

### 4.10. `org.education_curricula`
- id, institution_id FK, program_id FK, education_level, academic_year, name,
  description, status, approved_at, approved_by_id FK null, profile (jsonb),
  created_at, updated_at.
- Unique: (program_id, academic_year, name).
- `status`: `draft`, `approved`, `archived`.
- `academic_year` хранится в формате `2026/2027`.
- Учебный план доступен только для `vocational` и `higher`.

### 4.11. `org.curriculum_components`
- id, curriculum_id FK, code, name, component_type, semester, credits
  (numeric 5,2), academic_hours, contact_hours, assessment_type, is_optional,
  order_index, description, details (jsonb), created_at, updated_at.
- Unique: (curriculum_id, code).
- `component_type`: `discipline`, `module`, `practice`, `coursework`,
  `internship`, `other`.
- `assessment_type`: `exam`, `credit`, `differentiated_credit`, `coursework`,
  `practice_report`, `other`.
- Ограничения: семестр 1–12, кредиты 0–100, академические часы 0–20000,
  контактные часы не больше академических.
- Компоненты удаляются каскадно вместе с учебным планом.

### 4.12. `org.academic_sessions`
- id, institution_id FK, education_level, academic_year, semester, name,
  session_type, starts_on, ends_on, status, description, profile (jsonb),
  created_at, updated_at.
- Unique: (institution_id, academic_year, semester, name).
- `session_type`: `winter`, `summer`, `additional`, `other`; `status`:
  `planned`, `active`, `completed`, `archived`.

### 4.13. `org.session_statements`
- id, session_id FK, institution_id FK, education_level, group_id FK,
  curriculum_id FK, component_id FK, teacher_id FK null, statement_number,
  issued_on, status, approved_at, approved_by_id FK null, notes, profile
  (jsonb), created_at, updated_at.
- Unique: (session_id, group_id, component_id) и
  (institution_id, statement_number).
- `status`: `draft`, `published`, `approved`, `archived`.

### 4.14. `org.statement_records`
- id, statement_id FK, student_id FK, grade, result, credits_awarded
  (numeric 5,2), comment, profile (jsonb), created_at, updated_at.
- Unique: (statement_id, student_id).
- `result`: `planned`, `passed`, `failed`, `not_appeared`, `exempt`,
  `transferred`; оценка 1–10; кредиты 0–100.

### 4.15. `org.credit_transfers`
- id, institution_id FK, education_level, student_id FK, target_program_id FK
  null, target_component_id FK null, source_institution, source_program,
  source_component_code, source_component_name, source_academic_year,
  source_credits, awarded_credits, source_grade, document_number, reason,
  status, decided_at, decided_by_id FK null, profile (jsonb), created_at,
  updated_at.
- Unique: (institution_id, student_id, source_institution,
  source_component_code, source_academic_year).

### 4.16. `org.competencies`
- id, institution_id FK, education_level, code, name, description,
  competency_type, profile (jsonb), is_active, created_at, updated_at.
- Unique: (institution_id, code).
- `competency_type`: `universal`, `general`, `professional`, `other`.

### 4.17. `org.program_competencies`
- id, program_id FK, competency_id FK, target_level, weight (numeric 5,2),
  profile (jsonb), created_at, updated_at.
- Unique: (program_id, competency_id); целевой уровень 1–5, вес 0–100.

### 4.18. `org.component_competencies`
- id, component_id FK, competency_id FK, weight (numeric 5,2), profile
  (jsonb), created_at, updated_at.
- Unique: (component_id, competency_id); вес 0-100.

### 4.19. `org.practice_places`
- id, institution_id FK, education_level, code, name, industry, address,
  contact_person, contact_phone, contact_email, is_active, profile (jsonb),
  created_at, updated_at.
- Unique: (institution_id, code).
- Код предприятия уникален внутри учреждения; ступень ограничена
  `primary`, `secondary`, `vocational`, `higher`.

### 4.20. `org.practice_contracts`
- id, institution_id FK, education_level, practice_place_id FK, program_id FK
  null, component_id FK null, contract_number, academic_year, starts_on,
  ends_on, signed_on, status, responsible_id FK null, document_number, notes,
  profile (jsonb), created_at, updated_at.
- Unique: (institution_id, contract_number).
- `status`: `draft`, `signed`, `active`, `completed`, `terminated`, `archived`.
- `academic_year` — `2026/2027`; `ends_on >= starts_on`; компонент должен
  относиться к типу `practice` или `internship`.

### 4.21. `org.practice_placements`
- id, contract_id FK, institution_id FK, education_level, student_id FK,
  group_id FK null, component_id FK null, supervisor_id FK null,
  enterprise_supervisor, starts_on, ends_on, total_hours, status, result,
  grade, assessed_at, assessed_by_id FK null, notes, profile (jsonb),
  created_at, updated_at.
- Unique: (contract_id, student_id).
- `status`: `planned`, `active`, `completed`, `failed`, `cancelled`, `archived`.
- `result`: `not_assessed`, `passed`, `failed`, `exempt`; оценка 1-10.
- `total_hours` — 0-2000; период не выходит за период договора.

### 4.22. `org.practice_diary_entries`
- id, placement_id FK, entry_date, hours (numeric 5,2), activity, outcome,
  supervisor_comment, status, submitted_at, approved_at, approved_by_id FK
  null, profile (jsonb), created_at, updated_at.
- `status`: `draft`, `submitted`, `approved`, `rejected`; часы 0-24.
- Дата записи находится внутри периода практики; утверждённые часы не
  превышают плановые часы распределения.

## 5. LMS
### 5.1. `lms.subjects`
- id, code, name (jsonb), icon, description (jsonb), is_active.

### 5.2. `lms.topics`
- id, subject_id FK, class_number, code, title (jsonb), description (jsonb),
  difficulty_level, order_index, status, created_by, created_at, updated_at.

### 5.3. `lms.lessons`
- id, topic_id FK, title (jsonb), lesson_type (text/video/3d/lab), content
  (jsonb), status, order_index, created_by, created_at.

### 5.4. `lms.lesson_blocks`
- id, lesson_id FK, block_type (text/video/audio/quiz/embed), payload (jsonb),
  order_index.

### 5.5. `lms.textbooks`
- id, subject_id FK, class_number, title (jsonb), author, publisher, year,
  description (jsonb), file_id FK, uploaded_by, status.

### 5.6. `lms.textbook_topics`
- id, textbook_id FK, topic_id FK, page_from, page_to.

### 5.7. `lms.files`
- id, owner_id, storage_key, original_name, mime_type, size_bytes, checksum,
  virus_scan_status, created_at.

### 5.8. `lms.portfolio_items`
- id, student_id FK, item_type (certificate/project/olympiad/award), title,
  description, file_id, visibility (private/school/platform/external_link),
  external_url, created_at.

## 6. Assessment
### 6.1. `assessment.quizzes`
- id, title (jsonb), quiz_type (test/dictation/homework/control/exam), subject_id,
  class_number, created_by, school_id, time_limit_seconds, max_attempts,
  status, ai_generated, created_at.

### 6.2. `assessment.questions`
- id, quiz_id FK, question_type (single_choice/multiple_choice/text/number/
  audio/photo/handwriting), prompt (jsonb), payload (jsonb), points,
  order_index, ai_generated.

### 6.3. `assessment.answer_options`
- id, question_id FK, option_text (jsonb), is_correct, order_index.

### 6.4. `assessment.assignments`
- id, quiz_id FK, assigned_by, target_type (class/group/student), target_id,
  starts_at, due_at, instructions (jsonb), status, created_at.

### 6.5. `assessment.submissions`
- id, assignment_id FK, student_id FK, status (in_progress/submitted/graded),
  started_at, submitted_at, score, max_score, ai_checked, teacher_checked,
  teacher_comment, device_id, operation_id, created_at, updated_at.
- Unique: (assignment_id, student_id, attempt_no).

### 6.6. `assessment.answers`
- id, submission_id FK, question_id FK, answer_payload (jsonb), file_id FK null,
  ai_score, ai_feedback (jsonb), teacher_score, teacher_feedback, is_correct,
  answered_at.

### 6.7. `assessment.grading_scales`
- id, school_id, subject_id, scale_type (10_point/percent/pass_fail), config
  jsonb.

## 7. Journal
### 7.1. `journal.entries`
- id, school_id, class_id, subject_id, teacher_id, student_id, lesson_date,
  lesson_topic, grade, attendance (present/absent/sick/late/excused), comment,
  created_at, updated_at.
- Индексы: (class_id, lesson_date), (student_id, subject_id).

### 7.2. `journal.lesson_schedule`
- id, school_id, class_id, subject_id, teacher_id, day_of_week, start_time,
  end_time, room, valid_from, valid_to, created_at.

### 7.3. `journal.substitutions`
- id, schedule_id, absent_teacher_id, substitute_teacher_id, date, reason,
  approved_by, status.

## 8. Communication
### 8.1. `communication.chats`
- id, chat_type (private/group/class/support), title, school_id, created_by,
  is_anonymous, created_at.

### 8.2. `communication.chat_members`
- id, chat_id, user_id, member_role (owner/admin/member), joined_at, left_at.

### 8.3. `communication.messages`
- id, chat_id, sender_id null (аноним), message_type
  (text/file/audio/video/poll), payload jsonb, reply_to_id, created_at,
  edited_at, deleted_at.

### 8.4. `communication.notifications`
- id, user_id, channel (push/email/in_app/messenger), type, title, body,
  payload jsonb, read_at, sent_at, status.

### 8.5. `communication.video_rooms`
- id, room_type, owner_id, starts_at, ends_at, external_provider, external_id,
  status.

## 9. Safety
### 9.1. `safety.psych_appeals`
- id, anonymous_id, student_id null, psychologist_id null, category, status,
  priority, created_at, closed_at.

### 9.2. `safety.psych_messages`
- id, appeal_id, sender_type (student/psychologist/specialist), payload,
  created_at.

### 9.3. `safety.geo_points`
- id, student_id, device_id, latitude, longitude, accuracy_m, event_type
  (location/enter_school/leave_school), recorded_at, consent_id.

### 9.4. `safety.incidents`
- id, school_id, category, severity, description, reported_by, status,
  created_at, resolved_at.

## 10. Documents
### 10.1. `documents.templates`
- id, title, document_type, template_file_id, version, created_by, status.

### 10.2. `documents.requests`
- id, parent_id, student_id, template_id, status, payload jsonb, requested_at,
  processed_by, processed_at, result_file_id.

### 10.3. `documents.signatures`
- id, document_request_id, signer_id, signature_hash, signed_at, ip, user_agent,
  document_version.

## 11. Analytics
### 11.1. `analytics.daily_snapshots`
- id, snapshot_date, scope_type, scope_id, metrics jsonb.

### 11.2. `analytics.reports`
- id, report_type, parameters jsonb, file_id, created_by, created_at.

## 12. AI
### 12.1. `ai.settings`
- id, provider, base_url, model, encrypted_api_key, system_prompt, is_enabled,
  max_tokens, temperature, updated_by.

### 12.2. `ai.requests`
- id, user_id, request_type (generate/check/explain/validate), prompt_hash,
  prompt_preview, model, tokens_in, tokens_out, status, error_code, latency_ms,
  created_at.

### 12.3. `ai.documents`
- id, title, document_type, file_id, embedding vector, metadata jsonb.

## 13. Audit
### 13.1. `audit.events`
- id, actor_id, actor_role, action, entity_type, entity_id, before jsonb,
  after jsonb, ip, user_agent, request_id, created_at.
- Индексы: (actor_id, created_at), (entity_type, entity_id), (action).

### 13.2. `audit.security_events`
- id, event_type, severity, details jsonb, ip, created_at, resolved_at.

## 14. System
### 14.1. `system.settings`
- key, value jsonb, description, updated_by, updated_at.

### 14.2. `system.languages`
- code, name, is_enabled, is_default, order_index.

### 14.3. `system.translations`
- id, locale, namespace, key, value, updated_at.
- Unique: (locale, namespace, key).

### 14.4. `system.feature_flags`
- key, description, enabled, scope, updated_at.

### 14.5. `system.integrations`
- id, code, name, enabled, config jsonb, updated_by.

### 14.6. `system.services`
- code PK, name, description, version, category, api_prefix, icon,
  default_enabled, is_core, status, manifest jsonb, created_at, updated_at.

### 14.7. `system.service_activations`
- id, service_code FK, scope_type, scope_id, depth, enabled, config jsonb,
  updated_by, created_at, updated_at.
- Unique: (service_code, scope_type, scope_id).

### 14.8. `system.service_activations` — правила
- Самая конкретная активация побеждает.
- Ядровые сервисы отключить нельзя.
- Отключение на уровне школы перекрывает включение на уровне страны.

## 15. Ключевые связи
```mermaid
erDiagram
  REGIONS ||--o{ CITIES : contains
  CITIES ||--o{ SCHOOLS : contains
  SCHOOLS ||--o{ CLASSES : has
  SCHOOLS ||--o{ EDUCATION_PROGRAMS : offers
  EDUCATION_PROGRAMS ||--o{ CLASSES : groups
  EDUCATION_PROGRAMS ||--o{ STUDENT_ACADEMIC_PROFILES : program
  CLASSES ||--o{ STUDENT_ACADEMIC_PROFILES : group
  SCHOOLS ||--o{ STAFF_ACADEMIC_PROFILES : employs
  SCHOOLS ||--o{ PRACTICE_PLACES : partners
  PRACTICE_PLACES ||--o{ PRACTICE_CONTRACTS : signs
  EDUCATION_PROGRAMS ||--o{ PRACTICE_CONTRACTS : program
  CURRICULUM_COMPONENTS ||--o{ PRACTICE_CONTRACTS : practice
  PRACTICE_CONTRACTS ||--o{ PRACTICE_PLACEMENTS : places
  USERS ||--o{ PRACTICE_PLACEMENTS : practices
  CLASSES ||--o{ PRACTICE_PLACEMENTS : group
  PRACTICE_PLACEMENTS ||--o{ PRACTICE_DIARY_ENTRIES : diary
  CLASSES ||--o{ CLASS_MEMBERSHIPS : includes
  USERS ||--o{ CLASS_MEMBERSHIPS : member
  USERS ||--o{ STUDENT_ACADEMIC_PROFILES : student
  USERS ||--o{ STAFF_ACADEMIC_PROFILES : staff
  USERS ||--o{ USER_RELATIONS : parent
  USERS ||--o{ USER_RELATIONS : child
  SUBJECTS ||--o{ TOPICS : has
  TOPICS ||--o{ LESSONS : has
  TEXTBOOKS ||--o{ TEXTBOOK_TOPICS : links
  TOPICS ||--o{ TEXTBOOK_TOPICS : links
  QUIZZES ||--o{ QUESTIONS : has
  QUESTIONS ||--o{ ANSWER_OPTIONS : has
  QUIZZES ||--o{ ASSIGNMENTS : assigned
  ASSIGNMENTS ||--o{ SUBMISSIONS : receives
  SUBMISSIONS ||--o{ ANSWERS : contains
  USERS ||--o{ SUBMISSIONS : submits
  CLASSES ||--o{ JOURNAL_ENTRIES : has
  USERS ||--o{ JOURNAL_ENTRIES : student
  CHATS ||--o{ MESSAGES : contains
  USERS ||--o{ CHAT_MEMBERS : member
  USERS ||--o{ NOTIFICATIONS : receives
  USERS ||--o{ PSYCH_APPEALS : anonymous
  DOCUMENT_TEMPLATES ||--o{ DOCUMENT_REQUESTS : generates
  USERS ||--o{ DOCUMENT_SIGNATURES : signs
  USERS ||--o{ GROUP_MEMBERSHIPS : belongs
  GROUPS ||--o{ GROUP_MEMBERSHIPS : includes
  GROUPS ||--o{ GROUP_PERMISSIONS : granted
  PERMISSIONS ||--o{ GROUP_PERMISSIONS : published
  GROUPS ||--o{ GROUPS : inherits
  SERVICES ||--o{ SERVICE_ACTIVATIONS : activated
```

## 16. Офлайн-синхронизация
Для клиентских операций используются поля:
- `operation_id` (uuid) — идемпотентность.
- `device_id` — устройство.
- `client_created_at` — время на клиенте.
- `server_received_at` — время на сервере.

Правила конфликтов:
- Оценки, посещаемость, документы — приоритет сервера.
- Прогресс и локальные заметки — LWW по `updated_at`.
- Дубликаты операций игнорируются по `operation_id`.

## 17. Политика хранения
- Учебные данные — в течение учебного года и необходимого срока отчётности.
- Психологические обращения — минимально необходимый срок, с ограниченным
  доступом.
- Геоданные — короткий срок, если не требуется расследование инцидента.
- Аудит — не менее срока, установленного политикой ИБ.
- Удаление — по регламенту и с подтверждением.

## 18. Миграция из SQLite
1. Экспорт схемы и данных.
2. Нормализация справочников.
3. Сопоставление пользователей и ролей.
4. Перенос файлов в S3.
5. Сверка количества записей и контрольных сумм.
6. Тестовый импорт и функциональная сверка.
7. Промышленный импорт в согласованное окно.
