"""Platform service registry.

Each functional domain is described here once.  The registry is the single
source of truth for:

* the service catalog stored in ``system.services``;
* the permission catalog stored in ``iam.permissions``;
* the router prefix used by the gateway and by a standalone service app;
* default activation rules.

A service can be mounted in the modular monolith (development and the pilot)
or packaged as its own FastAPI application with
:func:`app.service_app.create_service_app`.  Both modes share the same code,
models, permissions and contract, so a domain can be extracted without
rewriting business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.scopes import CORE_SERVICES


@dataclass(frozen=True)
class PermissionSpec:
    """A capability published by a service."""

    code: str
    name: str
    category: str = "use"


@dataclass(frozen=True)
class ServiceManifest:
    """Static description of one platform service."""

    code: str
    name: str
    description: str
    category: str
    api_prefix: str
    icon: str
    version: str = "1.0.0"
    default_enabled: bool = True
    is_core: bool = False
    status: str = "active"
    permissions: tuple[PermissionSpec, ...] = field(default_factory=tuple)
    depends_on: tuple[str, ...] = field(default_factory=tuple)

    @property
    def permission_codes(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.permissions)

    @property
    def manifest_payload(self) -> dict:
        """JSON payload persisted in ``system.services.manifest``."""
        return {
            "code": self.code,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "api_prefix": self.api_prefix,
            "depends_on": list(self.depends_on),
            "permissions": [
                {
                    "code": item.code,
                    "name": item.name,
                    "category": item.category,
                }
                for item in self.permissions
            ],
        }


SERVICES: tuple[ServiceManifest, ...] = (
    ServiceManifest(
        code="system",
        name="Ядро платформы",
        description=(
            "Реестр сервисов, глобальные настройки, языки, миграции и "
            "управление включением функционала."
        ),
        category="core",
        api_prefix="/api/v1/services",
        icon="⚙️",
        is_core=True,
        permissions=(
            PermissionSpec("system.services.read", "Просмотр каталога сервисов", "read"),
            PermissionSpec("system.services.write", "Управление сервисами", "admin"),
            PermissionSpec("system.settings.read", "Просмотр настроек", "read"),
            PermissionSpec("system.settings.write", "Изменение настроек", "admin"),
        ),
    ),
    ServiceManifest(
        code="iam",
        name="Пользователи и доступ",
        description=(
            "Пользователи, группы, иерархические права, сессии и согласия. "
            "Права назначаются группам, а не отдельным пользователям."
        ),
        category="core",
        api_prefix="/api/v1/auth",
        icon="👥",
        is_core=True,
        permissions=(
            PermissionSpec("iam.profile.read", "Просмотр профиля", "read"),
            PermissionSpec("iam.profile.write", "Изменение профиля", "write"),
            PermissionSpec("iam.users.read", "Просмотр пользователей", "read"),
            PermissionSpec("iam.users.write", "Управление пользователями", "write"),
            PermissionSpec("iam.groups.read", "Просмотр групп", "read"),
            PermissionSpec("iam.groups.write", "Управление группами и правами", "admin"),
            PermissionSpec("iam.permissions.read", "Просмотр каталога прав", "read"),
            PermissionSpec("iam.audit.read", "Просмотр аудита доступа", "admin"),
        ),
        depends_on=("system",),
    ),
    ServiceManifest(
        code="org",
        name="Организации и классы",
        description=(
            "Регионы, города, школы, классы, учебные годы и состав классов. "
            "Иерархия используется группами и сервисными активациями."
        ),
        category="core",
        api_prefix="/api/v1/org",
        icon="🏫",
        is_core=True,
        permissions=(
            PermissionSpec("org.schools.read", "Просмотр школ", "read"),
            PermissionSpec("org.schools.write", "Управление школами", "admin"),
            PermissionSpec("org.classes.read", "Просмотр классов", "read"),
            PermissionSpec("org.classes.write", "Управление классами", "write"),
            PermissionSpec("org.members.read", "Просмотр состава классов", "read"),
            PermissionSpec("org.members.write", "Управление составом классов", "write"),
        ),
        depends_on=("system",),
    ),
    ServiceManifest(
        code="audit",
        name="Аудит и безопасность",
        description=(
            "Журнал действий, события информационной безопасности, "
            "трассировка доступа к персональным данным."
        ),
        category="security",
        api_prefix="/api/v1/admin",
        icon="🛡️",
        is_core=True,
        permissions=(
            PermissionSpec("audit.events.read", "Просмотр журнала аудита", "read"),
            PermissionSpec("audit.events.export", "Выгрузка журнала аудита", "admin"),
            PermissionSpec("audit.security.read", "Просмотр событий ИБ", "admin"),
        ),
        depends_on=("system", "iam"),
    ),
    ServiceManifest(
        code="lms",
        name="Учебный контент",
        description=(
            "Предметы, темы, уроки, учебники, курсы, методики и медиа. "
            "Публикует учебные материалы для всех клиентов."
        ),
        category="education",
        api_prefix="/api/v1/lms",
        icon="📚",
        permissions=(
            PermissionSpec("lms.content.read", "Просмотр учебного контента", "read"),
            PermissionSpec("lms.content.write", "Создание и изменение контента", "write"),
            PermissionSpec("lms.content.publish", "Публикация контента", "admin"),
            PermissionSpec("lms.textbooks.manage", "Управление учебниками", "write"),
            PermissionSpec("lms.courses.manage", "Управление курсами", "write"),
            PermissionSpec("lms.methods.manage", "Управление методиками", "write"),
        ),
        depends_on=("system", "org"),
    ),
    ServiceManifest(
        code="assessment",
        name="Тесты и работы",
        description=(
            "Тесты, вопросы, домашние и контрольные работы, сдача, "
            "автопроверка, результаты и аналитика попыток."
        ),
        category="education",
        api_prefix="/api/v1/assessment",
        icon="📝",
        permissions=(
            PermissionSpec("assessment.quizzes.read", "Просмотр тестов", "read"),
            PermissionSpec("assessment.quizzes.write", "Создание тестов", "write"),
            PermissionSpec("assessment.assignments.create", "Назначение работ", "write"),
            PermissionSpec("assessment.submissions.submit", "Сдача работ", "use"),
            PermissionSpec("assessment.submissions.grade", "Проверка и оценивание", "write"),
            PermissionSpec("assessment.results.read", "Просмотр результатов", "read"),
        ),
        depends_on=("system", "org", "lms"),
    ),
    ServiceManifest(
        code="journal",
        name="Электронный журнал",
        description=(
            "Расписание, оценки, посещаемость, массовое выставление, "
            "сводки и дневник. Сердце ежедневной работы школы."
        ),
        category="education",
        api_prefix="/api/v1/journal",
        icon="📔",
        permissions=(
            PermissionSpec("journal.schedule.read", "Просмотр расписания", "read"),
            PermissionSpec("journal.schedule.write", "Управление расписанием", "write"),
            PermissionSpec("journal.grades.read", "Просмотр оценок", "read"),
            PermissionSpec("journal.grades.write", "Выставление оценок", "write"),
            PermissionSpec("journal.attendance.read", "Просмотр посещаемости", "read"),
            PermissionSpec("journal.attendance.write", "Отметка посещаемости", "write"),
            PermissionSpec("journal.summary.read", "Просмотр сводок", "read"),
        ),
        depends_on=("system", "org"),
    ),
    ServiceManifest(
        code="library",
        name="Библиотека и рекомендации",
        description=(
            "Каталог пособий, доступ по классам, рекомендации учителя, "
            "отметки о прочтении и статистика."
        ),
        category="education",
        api_prefix="/api/v1/library",
        icon="📖",
        permissions=(
            PermissionSpec("library.catalog.read", "Просмотр библиотеки", "read"),
            PermissionSpec("library.books.manage", "Управление книгами", "write"),
            PermissionSpec("library.recommendations.create", "Рекомендация книг", "write"),
            PermissionSpec("library.recommendations.revoke", "Отзыв рекомендаций", "write"),
            PermissionSpec("library.progress.read", "Просмотр прогресса чтения", "read"),
        ),
        depends_on=("system", "org", "lms"),
    ),
    ServiceManifest(
        code="analytics",
        name="Аналитика и отчётность",
        description=(
            "BI-показатели, отчёты по формам Министерства образования, "
            "срезы по классам, школам, городам, областям и стране."
        ),
        category="analytics",
        api_prefix="/api/v1/analytics",
        icon="📊",
        default_enabled=True,
        permissions=(
            PermissionSpec("analytics.reports.read", "Просмотр отчётов", "read"),
            PermissionSpec("analytics.reports.export", "Выгрузка отчётов", "write"),
            PermissionSpec("analytics.bi.read", "Просмотр BI-панелей", "read"),
            PermissionSpec("analytics.bi.manage", "Настройка BI-панелей", "admin"),
        ),
        depends_on=("system", "org", "journal"),
    ),
    ServiceManifest(
        code="ai",
        name="ИИ-оркестратор",
        description=(
            "Объяснения, генерация заданий, проверка фото/аудио/прописей, "
            "RAG по учебникам и валидация контента по учебным программам."
        ),
        category="ai",
        api_prefix="/api/v1/ai",
        icon="🤖",
        default_enabled=False,
        status="beta",
        permissions=(
            PermissionSpec("ai.explain.use", "Использование ИИ-объяснений", "use"),
            PermissionSpec("ai.generate.use", "Генерация заданий", "use"),
            PermissionSpec("ai.check.use", "ИИ-проверка работ", "use"),
            PermissionSpec("ai.validate.use", "Валидация контента", "use"),
            PermissionSpec("ai.settings.manage", "Настройка ИИ-провайдеров", "admin"),
        ),
        depends_on=("system", "lms", "assessment"),
    ),
    ServiceManifest(
        code="communication",
        name="Коммуникации",
        description=(
            "Внутренний мессенджер, уведомления, объявления, видеосвязь "
            "с возможностью отключения внешних провайдеров."
        ),
        category="communication",
        api_prefix="/api/v1/communication",
        icon="💬",
        default_enabled=True,
        permissions=(
            PermissionSpec("communication.chat.use", "Использование чатов", "use"),
            PermissionSpec("communication.announcements.read", "Просмотр объявлений", "read"),
            PermissionSpec("communication.announcements.write", "Публикация объявлений", "write"),
            PermissionSpec("communication.video.use", "Видеосвязь", "use"),
            PermissionSpec("communication.moderation.manage", "Модерация", "admin"),
        ),
        depends_on=("system", "iam"),
    ),
    ServiceManifest(
        code="safety",
        name="Безопасность и психология",
        description=(
            "Психологическая поддержка, анонимные обращения, инциденты, "
            "геолокация и маршруты с согласиями законных представителей."
        ),
        category="security",
        api_prefix="/api/v1/safety",
        icon="🧠",
        default_enabled=False,
        permissions=(
            PermissionSpec("safety.support.use", "Обращение к психологу", "use"),
            PermissionSpec("safety.incidents.read", "Просмотр инцидентов", "read"),
            PermissionSpec("safety.incidents.manage", "Управление инцидентами", "write"),
            PermissionSpec("safety.geolocation.read", "Просмотр геолокации", "read"),
            PermissionSpec("safety.consents.manage", "Управление согласиями", "admin"),
        ),
        depends_on=("system", "iam", "communication"),
    ),
    ServiceManifest(
        code="documents",
        name="Документы и секретариат",
        description=(
            "Шаблоны справок и заявлений, согласия, электронная подпись, "
            "документооборот школы и вышестоящих органов."
        ),
        category="management",
        api_prefix="/api/v1/documents",
        icon="📄",
        default_enabled=False,
        permissions=(
            PermissionSpec("documents.templates.read", "Просмотр шаблонов", "read"),
            PermissionSpec("documents.templates.write", "Управление шаблонами", "write"),
            PermissionSpec("documents.requests.create", "Создание заявок", "use"),
            PermissionSpec("documents.requests.process", "Обработка заявок", "write"),
            PermissionSpec("documents.sign.use", "Электронная подпись", "use"),
        ),
        depends_on=("system", "iam", "org"),
    ),
    ServiceManifest(
        code="admin",
        name="Администрирование",
        description=(
            "Статистика, управление пользователями школы, региональные и "
            "республиканские панели, иерархия администраторов."
        ),
        category="management",
        api_prefix="/api/v1/admin",
        icon="🛠️",
        default_enabled=True,
        permissions=(
            PermissionSpec("admin.school.read", "Просмотр статистики школы", "read"),
            PermissionSpec("admin.school.manage", "Управление школой", "admin"),
            PermissionSpec("admin.region.manage", "Управление городом/областью", "admin"),
            PermissionSpec("admin.country.manage", "Республиканское управление", "admin"),
        ),
        depends_on=("system", "iam", "org", "audit"),
    ),
)

SERVICE_BY_CODE: dict[str, ServiceManifest] = {
    manifest.code: manifest for manifest in SERVICES
}

PERMISSION_BY_CODE: dict[str, PermissionSpec] = {
    permission.code: permission
    for manifest in SERVICES
    for permission in manifest.permissions
}


def get_service(code: str) -> ServiceManifest | None:
    return SERVICE_BY_CODE.get(code)


def core_service_codes() -> frozenset[str]:
    return frozenset(
        manifest.code
        for manifest in SERVICES
        if manifest.is_core or manifest.code in CORE_SERVICES
    )
