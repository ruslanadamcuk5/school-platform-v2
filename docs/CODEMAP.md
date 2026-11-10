# Карта кода

> Сгенерировано `scripts/gen_codemap.py`. Не редактировать вручную.
> Дата генерации: 10.11.2026.
> Backend: 79 файлов; tests: 23; frontend: 34.

## Как пользоваться
1. Найдите домен в таблице.
2. Откройте 1–2 файла по указанному пути, не весь каталог.
3. Для маршрутов API используйте `docs/api/ENDPOINTS.md`.

## Backend
| Файл | Строк | Классы | Функции |
|---|---:|---|---|
| `backend/app/__init__.py` | 1 | — | — |
| `backend/app/api/__init__.py` | 1 | — | — |
| `backend/app/api/deps.py` | 182 | — | get_current_user:27, require_roles:60, ensure_school_access:91, tenant_school_id:114, require_permission:127, require_service:152, ensure_scope_access:168 |
| `backend/app/api/v1/__init__.py` | 1 | — | — |
| `backend/app/api/v1/admin.py` | 215 | — | stats:27, list_users:86, create_user:140, audit_events:198 |
| `backend/app/api/v1/admin_settings.py` | 260 | — | _dangerous_changes:47, _values_for:60, _probe:67, _as_out:76, get_cache_settings:107, update_cache_settings:122, cache_settings_history:197, test_cache_connection:241 |
| `backend/app/api/v1/analytics.py` | 410 | — | _percent:50, _average:56, _csv_cell:62, build_class_csv:69, _build_overview:96, overview:363, export_csv:380 |
| `backend/app/api/v1/assessment.py` | 1165 | — | _ensure_role:75, _now:83, _as_utc:87, _quiz_scope_ok:95, _ensure_quiz_scope:99, _ensure_assignment_owner:107, _load_quiz:117, _load_assignment:126, _quiz_out:141, _quiz_detail:147 (+24) |
| `backend/app/api/v1/auth.py` | 417 | — | _client_ip:54, _user_agent:61, _load_mfa_user:65, login:95, refresh:192, mfa_enroll_start:228, mfa_enroll_verify:262, mfa_verify:327, mfa_status:387, logout:400 (+1) |
| `backend/app/api/v1/communication.py` | 128 | — | _now:31, list_notifications:36, mark_notification_read:56, create_notification:81 |
| `backend/app/api/v1/documents.py` | 290 | — | _now:47, _ensure_school:51, _ensure_student_access:59, list_my_document_requests:98, list_school_document_requests:120, create_document_request:146, process_document_request:210, cancel_document_request:260 |
| `backend/app/api/v1/education.py` | 4449 | — | _level_or_404:116, _level_out:123, _school_for_level:127, _available_years:148, _group_query:166, _students_by_group:188, _group_out:207, _program_map:232, _overview:249, _program_for_institution:371 (+35) |
| `backend/app/api/v1/groups.py` | 589 | — | _now:57, _group_out:61, _group_detail:84, _options:119, _load_group:131, _assert_scope_visible:142, _resolve_scope:155, list_permissions:172, list_groups:202, get_group:269 (+7) |
| `backend/app/api/v1/journal.py` | 1076 | — | _ensure_role:77, _now:85, _today:89, _schedule_stmt:93, _entry_stmt:102, _schedule_out:111, _entry_out:136, _class_scope:158, _subject_or_404:169, _student_class_ids:176 (+18) |
| `backend/app/api/v1/library.py` | 1352 | — | _now:70, _ensure_role:74, _book_options:82, _book_stmt:95, _rec_options:99, _rec_stmt:111, _topics_out:115, _book_out:138, _book_detail_out:163, _rec_out:177 (+28) |
| `backend/app/api/v1/lms.py` | 362 | — | list_subjects:58, get_subject:72, list_topics:84, get_topic_by_code:135, get_topic:153, _topic_detail:164, list_textbooks:207, get_textbook:258, list_courses:289, get_course:318 |
| `backend/app/api/v1/me.py` | 130 | — | _options:30, my_permissions:45, my_services:113 |
| `backend/app/api/v1/onboarding.py` | 701 | — | _now:57, _step_out:61, _module_out:75, _progress_out:116, my_onboarding:138, my_module:197, start_my_module:216, complete_my_step:237, _managed_school_ids:254, _teacher_student_ids:298 (+7) |
| `backend/app/api/v1/org.py` | 261 | — | list_regions:37, list_cities:47, list_schools:64, _validate_levels:74, create_school:100, update_school:162, get_school:210, list_classes:227, get_class:252 |
| `backend/app/api/v1/router.py` | 46 | — | — |
| `backend/app/api/v1/safety.py` | 1074 | — | _now:82, _age_on:86, _is_minor:92, _load_safety_settings:104, _settings_scope:123, _get_school:133, _resolve_school_id:141, _assert_student_in_school:165, _assert_parent_link:184, _user_requester_role:202 (+19) |
| `backend/app/api/v1/services.py` | 298 | — | _now:41, _resolve_scope:45, _fallback_services:60, _all_services:79, list_services:86, effective_services:99, get_service:156, get_activation:174, set_activation:202, delete_activation:276 |
| `backend/app/api/v1/system.py` | 59 | — | build_health:19, health:39, meta:47 |
| `backend/app/core/__init__.py` | 1 | — | — |
| `backend/app/core/cache.py` | 274 | CacheClient:37, NullCache:51, RedisCache:70 | _prefix:96, _version_key:100, _available:104, _mark_failure:108, _mark_success:118, get_cache:124, _close_cache_client:143, ensure_cache_runtime:155, apply_cache_runtime_settings:168, close_cache:175 (+7) |
| `backend/app/core/config.py` | 130 | Settings:20 | get_settings:126 |
| `backend/app/core/education.py` | 226 | EducationLevelInfo:102 | normalize_level:206, level_for_grade:214, default_levels_for_institution:219, level_info:225 |
| `backend/app/core/scopes.py` | 51 | — | — |
| `backend/app/core/security.py` | 214 | TokenError:20 | hash_password:24, _verify_legacy_pbkdf2:30, verify_password:51, needs_rehash:62, _read_key:74, _private_key:82, _public_key:89, create_access_token:95, decode_access_token:125, create_mfa_token:141 (+6) |
| `backend/app/db/__init__.py` | 1 | — | — |
| `backend/app/db/base.py` | 44 | Base:20, UUIDPrimaryKeyMixin:24, TimestampMixin:33 | — |
| `backend/app/db/import_legacy.py` | 1420 | Importer:200 | legacy_uuid:101, sha256_file:106, parse_dt:114, parse_date:136, parse_time:141, parse_json:153, clean_text:164, slug_code:171, old_rows:175, source_counts:182 (+2) |
| `backend/app/db/pilot_data.py` | 3563 | Person:630 | _person:640, _login_slug:689, _demo_password:696, _repair_demo_logins:711, _get_or_create_school:734, _get_or_create_user:802, _get_or_create_class:841, _get_or_create_program:907, _ensure_groups:946, _attach:1007 (+25) |
| `backend/app/db/seed.py` | 569 | — | _upsert_geography:140, _upsert_permissions:175, _upsert_services:201, _upsert_country_activations:232, _get_or_create_group:265, _grant_permissions:305, _add_membership:344, seed:368 |
| `backend/app/db/session.py` | 38 | — | get_session:31 |
| `backend/app/main.py` | 165 | — | lifespan:32, request_headers_middleware:95, robots:114, root:119, root_health:134 |
| `backend/app/models/__init__.py` | 159 | — | — |
| `backend/app/models/ai.py` | 112 | AISetting:29, AIRequest:62, AIExplanation:90 | — |
| `backend/app/models/analytics.py` | 183 | Attempt:30, TopicProgress:74, MethodProgress:122, DailyAnswer:164 | — |
| `backend/app/models/assessment.py` | 374 | Quiz:31, Question:79, AnswerOption:115, Assignment:136, Submission:196, Answer:264, GradingScale:309, PlaySession:335 | — |
| `backend/app/models/audit.py` | 41 | AuditEvent:15 | — |
| `backend/app/models/communication.py` | 55 | Notification:18 | — |
| `backend/app/models/documents.py` | 68 | DocumentRequest:26 | — |
| `backend/app/models/education.py` | 1146 | EducationProgram:77, StudentAcademicProfile:132, StaffAcademicProfile:195, EducationCurriculum:231, CurriculumComponent:301, AcademicSession:379, SessionStatement:440, StatementRecord:539, CreditTransfer:591, Competency:692 (+6) | — |
| `backend/app/models/iam.py` | 457 | User:48, UserRelation:175, RefreshToken:221, MfaRecoveryCode:258, UserGroup:281, GroupMembership:348, Permission:388, GroupPermission:419 | — |
| `backend/app/models/journal.py` | 145 | LessonSchedule:31, JournalEntry:93 | — |
| `backend/app/models/lms.py` | 566 | Subject:40, Topic:68, Method:131, Lesson:165, LessonBlock:196, StoredFile:215, Textbook:241, TextbookTopic:280, Course:308, CourseTopic:351 (+6) | _jsonb_object:31 |
| `backend/app/models/onboarding.py` | 100 | OnboardingProfile:24, OnboardingModuleProgress:56 | — |
| `backend/app/models/org.py` | 292 | Region:34, City:49, School:72, SchoolClass:130, ClassMembership:209, TeacherSubject:248 | — |
| `backend/app/models/safety.py` | 254 | SupportAppeal:61, Incident:125, GeolocationPoint:168, Consent:208 | — |
| `backend/app/models/system.py` | 206 | Setting:28, Language:49, FeatureFlag:66, ImportRun:86, Service:110, ServiceActivation:161 | — |
| `backend/app/schemas/__init__.py` | 1 | — | — |
| `backend/app/schemas/analytics.py` | 67 | AnalyticsTotalsOut:10, AnalyticsGradesOut:17, AnalyticsAttendanceOut:26, AnalyticsSubjectOut:36, AnalyticsClassOut:45, AnalyticsOverviewOut:57 | — |
| `backend/app/schemas/assessment.py` | 220 | AnswerOptionIn:11, QuestionIn:16, QuizCreate:29, QuizUpdate:43, AnswerOptionOut:50, AnswerOptionAdminOut:58, QuestionOut:62, QuestionPublicOut:74, QuizOut:85, QuizDetailOut:104 (+11) | — |
| `backend/app/schemas/auth.py` | 136 | LoginRequest:11, RefreshRequest:16, LogoutRequest:20, TokenPair:24, UserOut:33, MfaChallenge:57, MfaTokenRequest:64, MfaEnrollStart:68, MfaVerifyRequest:74, MfaEnrollmentComplete:78 (+6) | — |
| `backend/app/schemas/common.py` | 19 | Message:7, HealthOut:12 | — |
| `backend/app/schemas/communication.py` | 49 | NotificationCreate:11, NotificationOut:36 | — |
| `backend/app/schemas/documents.py` | 73 | DocumentRequestCreate:11, DocumentRequestProcess:35, DocumentRequestOut:57 | — |
| `backend/app/schemas/education.py` | 866 | EducationLevelOut:43, EducationGroupOut:58, EducationTotalsOut:73, EducationProgramOut:80, EducationProgramCreate:96, EducationProgramUpdate:105, CurriculumComponentOut:114, CurriculumComponentCreate:135, CurriculumComponentUpdate:158, EducationCurriculumOut:173 (+49) | — |
| `backend/app/schemas/groups.py` | 144 | PermissionOut:25, PermissionListOut:37, GroupMemberOut:42, GroupPermissionOut:52, GroupOut:60, GroupDetailOut:79, GroupListOut:85, GroupCreate:90, GroupUpdate:102, GroupMembersAdd:111 (+4) | — |
| `backend/app/schemas/journal.py` | 175 | ScheduleItemIn:12, ScheduleItemUpdate:36, ScheduleItemOut:51, ScheduleListOut:76, JournalClassOut:81, JournalStudentOut:91, JournalEntryIn:99, JournalEntryUpdate:110, JournalEntryOut:117, JournalBulkItem:139 (+5) | — |
| `backend/app/schemas/library.py` | 186 | LibraryTopicOut:12, LibraryBookOut:22, LibraryRecommendationOut:42, LibraryBookDetailOut:63, LibraryBookCreate:69, LibraryBookUpdate:79, LibraryRecommendationCreate:88, LibraryStatsOut:101, LibraryClassOut:109, LibraryChildOut:119 (+9) | — |
| `backend/app/schemas/lms.py` | 158 | SubjectOut:10, MethodOut:24, LessonOut:37, TopicOut:47, TextbookLinkOut:69, TopicDetailOut:79, TopicList:85, TextbookOut:92, TextbookTopicOut:109, TextbookDetailOut:117 (+5) | — |
| `backend/app/schemas/onboarding.py` | 117 | OnboardingStepOut:10, OnboardingModuleOut:22, OnboardingStageOut:45, OnboardingOverviewOut:55, OnboardingProgressOut:71, OnboardingReportSummaryOut:83, OnboardingReportUserOut:96, OnboardingReportUsersOut:112 | — |
| `backend/app/schemas/org.py` | 102 | SchoolCreate:14, SchoolUpdate:33, SchoolOut:48, RegionOut:66, CityOut:75, ClassOut:86 | — |
| `backend/app/schemas/platform_settings.py` | 73 | CacheSettingsOut:14, CacheSettingsUpdate:34, CacheSettingsHistoryItem:53, CacheSettingsHistory:62, CacheTestOut:68 | — |
| `backend/app/schemas/safety.py` | 248 | SupportAppealCreate:11, SupportAppealRespond:42, SupportAppealOut:55, IncidentCreate:78, IncidentResolve:104, IncidentOut:117, GeolocationPointCreate:135, GeolocationPointOut:160, ConsentCreate:174, ConsentRevoke:190 (+4) | — |
| `backend/app/schemas/services.py` | 77 | ServicePermissionOut:17, ServiceOut:23, ServiceListOut:39, ServiceActivationOut:44, ServiceActivationSet:57, EffectiveServiceOut:62, MyServicesOut:75 | — |
| `backend/app/service_app.py` | 192 | — | _middleware:69, create_service_app:96 |
| `backend/app/services/__init__.py` | 1 | — | — |
| `backend/app/services/access.py` | 790 | PermissionGrant:54, EffectivePermissions:65, ServiceState:227 | now_utc:48, legacy_allows:201, resolve_permissions:210, _cache_subject:237, _permissions_to_cache:243, _permissions_from_cache:262, _service_states_to_cache:284, _service_states_from_cache:298, pick_service_state:316, scope_within:341 (+17) |
| `backend/app/services/audit.py` | 35 | — | add_audit_event:12 |
| `backend/app/services/auth.py` | 203 | AuthError:22 | _client_info:26, authenticate:35, record_login_success:85, issue_refresh_token:111, rotate_refresh_token:132, revoke_refresh_token:178 |
| `backend/app/services/grading.py` | 287 | — | _clean:28, normalize_text:33, normalize_number:42, normalize_time:75, normalize:100, _given_values:110, _payload_answer:117, _answer_type:122, _read_task:136, _correct_choices:143 (+9) |
| `backend/app/services/mfa.py` | 346 | MfaError:33, MfaNotConfiguredError:37, MfaLockedError:41 | _now:45, _fernet:49, encrypt_secret:64, decrypt_secret:68, generate_totp_secret:77, build_otpauth_uri:81, _hotp:95, totp_code:106, verify_totp:116, normalize_recovery_code:140 (+10) |
| `backend/app/services/onboarding.py` | 301 | CurriculumContext:59, PersonalizedModule:151 | now_utc:28, _allowed:32, module_is_eligible:40, curriculum_context:64, personalized_modules:73, _stage_order:95, ensure_profile:106, progress_by_module:137, personalized_state:157, next_step:180 (+5) |
| `backend/app/services/onboarding_catalog.py` | 861 | OnboardingStep:51, OnboardingModule:63 | _service_steps:80, get_module:854, modules_for_service:858 |
| `backend/app/services/platform_settings.py` | 269 | CacheRuntimeSettings:61 | _normalise_prefix:33, _number_in_range:41, _env_defaults:103, _coerce:119, current_cache_settings:181, get_cache_runtime:188, save_cache_settings:238, reset_cache_runtime_for_tests:265 |
| `backend/app/services/registry.py` | 553 | PermissionSpec:25, ServiceManifest:34 | get_service:544, core_service_codes:548 |

## Frontend
| Файл | Строк | Экспорты |
|---|---:|---|
| `frontend/src/access/AccessContext.tsx` | 149 | AccessProvider, useAccess |
| `frontend/src/api/client.ts` | 1812 | API_BASE, API_ORIGIN, api, getAccessToken, getRefreshToken, getStoredUser, storeSession, storeUser, clearSession, apiErrorMessage (+114) |
| `frontend/src/api/types.ts` | 1263 | Role, ScopeType, User, TokenPair, MfaChallenge, LoginResult, MfaEnrollStart, MfaEnrollmentComplete, MfaStatus, Service (+112) |
| `frontend/src/App.tsx` | 240 | App, UnauthorizedPage |
| `frontend/src/auth/AuthContext.tsx` | 155 | AuthProvider, useAuth |
| `frontend/src/auth/ProtectedRoute.tsx` | 26 | ProtectedRoute |
| `frontend/src/components/ui.tsx` | 370 | Button, IconButton, Card, Badge, Spinner, EmptyState, ErrorAlert, Toggle, PageHeader, StatCard (+2) |
| `frontend/src/layout/AppLayout.tsx` | 404 | AppLayout |
| `frontend/src/lib/cn.ts` | 5 | cn |
| `frontend/src/lib/labels.ts` | 178 | roleLabels, roleLabel, categoryLabels, categoryColors, scopeLabels, scopeShortLabels, scopeColors, serviceCategoryLabels, serviceCategoryColors, initials (+6) |
| `frontend/src/main.tsx` | 11 | — |
| `frontend/src/onboarding/CoachContext.tsx` | 149 | CoachProvider, useCoach |
| `frontend/src/onboarding/CoachOverlay.tsx` | 268 | CoachOverlay |
| `frontend/src/pages/AnalyticsPage.tsx` | 569 | AnalyticsPage |
| `frontend/src/pages/DashboardPage.tsx` | 638 | DashboardPage |
| `frontend/src/pages/EducationCompetenciesCard.tsx` | 913 | EducationCompetenciesCard |
| `frontend/src/pages/EducationLevelPage.tsx` | 2856 | EducationLevelPage |
| `frontend/src/pages/EducationPracticeCard.tsx` | 2061 | EducationPracticeCard |
| `frontend/src/pages/EducationSessionsCard.tsx` | 1973 | EducationSessionsCard |
| `frontend/src/pages/GroupsPage.tsx` | 1311 | GroupsPage |
| `frontend/src/pages/LoginPage.test.tsx` | 133 | — |
| `frontend/src/pages/LoginPage.tsx` | 484 | LoginPage |
| `frontend/src/pages/NotFoundPage.tsx` | 27 | NotFoundPage |
| `frontend/src/pages/OnboardingModulePage.tsx` | 368 | OnboardingModulePage |
| `frontend/src/pages/OnboardingPage.tsx` | 434 | OnboardingPage |
| `frontend/src/pages/OnboardingReportsPage.tsx` | 546 | OnboardingReportsPage |
| `frontend/src/pages/PlatformSettingsPage.test.tsx` | 187 | — |
| `frontend/src/pages/PlatformSettingsPage.tsx` | 636 | PlatformSettingsPage |
| `frontend/src/pages/ProfilePage.tsx` | 435 | ProfilePage |
| `frontend/src/pages/SafetyPage.test.tsx` | 174 | — |
| `frontend/src/pages/SafetyPage.tsx` | 2122 | SafetyPage |
| `frontend/src/pages/ServicePlaceholderPage.tsx` | 439 | ServicePlaceholderPage |
| `frontend/src/pages/ServicesPage.tsx` | 552 | ServicesPage |
| `frontend/src/test/setup.ts` | 6 | — |

## Tests
| Файл | Строк | Тестов |
|---|---:|---:|
| `backend/tests/conftest.py` | 19 | 0 |
| `backend/tests/test_access_resolution.py` | 166 | 13 |
| `backend/tests/test_analytics.py` | 64 | 4 |
| `backend/tests/test_assessment_api.py` | 366 | 9 |
| `backend/tests/test_cache.py` | 204 | 9 |
| `backend/tests/test_communication.py` | 73 | 7 |
| `backend/tests/test_documents.py` | 71 | 7 |
| `backend/tests/test_education_levels.py` | 348 | 16 |
| `backend/tests/test_grading.py` | 137 | 8 |
| `backend/tests/test_groups_api.py` | 146 | 7 |
| `backend/tests/test_journal_api.py` | 486 | 12 |
| `backend/tests/test_library_api.py` | 699 | 17 |
| `backend/tests/test_lms_api.py` | 226 | 6 |
| `backend/tests/test_mfa.py` | 388 | 12 |
| `backend/tests/test_module_access.py` | 129 | 3 |
| `backend/tests/test_onboarding.py` | 104 | 8 |
| `backend/tests/test_openapi.py` | 43 | 2 |
| `backend/tests/test_pilot_data.py` | 20 | 2 |
| `backend/tests/test_platform_settings.py` | 393 | 11 |
| `backend/tests/test_safety.py` | 228 | 23 |
| `backend/tests/test_security.py` | 59 | 5 |
| `backend/tests/test_service_app.py` | 52 | 6 |
| `backend/tests/test_services_api.py` | 158 | 8 |

## Где искать
- API-роутеры: `backend/app/api/v1/`.
- Сервисы и права: `backend/app/services/`.
- Модели: `backend/app/models/`; схемы: `backend/app/schemas/`.
- Миграции: `backend/alembic/versions/`.
- Веб-клиент: `frontend/src/pages/`, `frontend/src/api/`, `frontend/src/components/`.
- Документация: `docs/INDEX.md`.
