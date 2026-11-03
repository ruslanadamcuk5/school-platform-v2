"""Versioned catalogue of interactive onboarding modules.

The catalogue is deliberately code-first:

* content is reviewed and released together with a service manifest;
* every module declares the service it belongs to and the permissions that
  make it relevant;
* the learner curriculum is assembled per request from enabled services,
  role and effective permissions.

Progress lives in ``onboarding.module_progress``.  When an administrator
enables a new service for a learner, a module for that service appears as an
add-on ("дообучение") until the learner starts it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CATALOG_VERSION = "1.0.0"

STAGES: tuple[dict[str, str], ...] = (
    {
        "code": "start",
        "title": "Старт",
        "description": "Первые шаги, навигация и безопасная работа с аккаунтом.",
    },
    {
        "code": "core",
        "title": "Ядро платформы",
        "description": "Пользователи, структура школы, группы и аудит.",
    },
    {
        "code": "daily",
        "title": "Ежедневная работа",
        "description": "Учебный контент, журнал, работы и библиотека.",
    },
    {
        "code": "management",
        "title": "Управление и отчётность",
        "description": "Аналитика, документы и административные панели.",
    },
    {
        "code": "advanced",
        "title": "Дополнительные возможности",
        "description": "Коммуникации, безопасность и ИИ-помощник.",
    },
)


@dataclass(frozen=True)
class OnboardingStep:
    code: str
    title: str
    body: str
    target: str | None = None
    route: str | None = None
    tip: str | None = None
    action: str = "next"
    duration_seconds: int = 30


@dataclass(frozen=True)
class OnboardingModule:
    code: str
    service_code: str
    stage: str
    title: str
    description: str
    icon: str
    estimated_minutes: int
    steps: tuple[OnboardingStep, ...]
    roles: tuple[str, ...] | None = None
    required_permissions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def step_codes(self) -> tuple[str, ...]:
        return tuple(step.code for step in self.steps)


def _service_steps(
    *,
    nav_code: str,
    route: str,
    focus_title: str,
    focus_body: str,
    practice_title: str,
    practice_body: str,
    safety_body: str,
) -> tuple[OnboardingStep, ...]:
    """Four-step pattern used by every service-specific module."""
    return (
        OnboardingStep(
            code="locate",
            title="Где находится раздел",
            body=focus_body,
            target=f"[data-onboarding-nav='{nav_code}']",
            route="/",
            tip="Нажмите на подсвеченный пункт меню — он откроется в этом же окне.",
            action="click",
            duration_seconds=25,
        ),
        OnboardingStep(
            code="open",
            title=focus_title,
            body=(
                "Раздел открыт. Обратите внимание на заголовок, фильтры и "
                "основные действия — они понадобятся в ежедневной работе."
            ),
            target="[data-onboarding='page-content']",
            route=route,
            tip="Интерфейс намеренно не перегружен: начните с одного действия.",
            duration_seconds=35,
        ),
        OnboardingStep(
            code="practice",
            title=practice_title,
            body=practice_body,
            target="[data-onboarding='page-content']",
            route=route,
            tip="Прогресс сохраняется после каждого шага. Можно вернуться завтра.",
            duration_seconds=40,
        ),
        OnboardingStep(
            code="rules",
            title="Права и безопасность",
            body=safety_body,
            target="[data-onboarding='page-content']",
            route=route,
            tip="Если действие недоступно — значит, оно не входит в ваши права.",
            duration_seconds=30,
        ),
    )


MODULES: tuple[OnboardingModule, ...] = (
    OnboardingModule(
        code="platform-basics",
        service_code="system",
        stage="start",
        title="Первый вход и рабочее пространство",
        description=(
            "Как устроен «Школьник»: дашборд, боковое меню, профиль и "
            "принцип «только нужные сервисы»."
        ),
        icon="🚀",
        estimated_minutes=5,
        roles=None,
        steps=(
            OnboardingStep(
                code="dashboard",
                title="Ваш рабочий стол",
                body=(
                    "Дашборд собирает главное: школу, количество классов и "
                    "пользователей, включённые сервисы и состояние платформы."
                ),
                target="[data-onboarding-nav='dashboard']",
                route="/",
                tip="Начните день с дашборда: здесь видно, всё ли работает.",
                action="click",
                duration_seconds=30,
            ),
            OnboardingStep(
                code="services",
                title="Только ваши сервисы",
                body=(
                    "Боковое меню строится динамически. Вы видите только те "
                    "сервисы, которые включены для вашей школы или класса."
                ),
                target="[data-onboarding='page-content']",
                route="/",
                tip="Если сервис отключён администратором, он исчезает из меню.",
                duration_seconds=35,
            ),
            OnboardingStep(
                code="profile",
                title="Профиль и доступ",
                body=(
                    "В профиле видны группы, права и включённые сервисы. "
                    "Отсюда можно проверить, почему доступно или недоступно действие."
                ),
                target="[data-onboarding-nav='profile']",
                route="/profile",
                tip="Права выдаются группам, а не отдельным пользователям.",
                action="click",
                duration_seconds=35,
            ),
            OnboardingStep(
                code="security",
                title="Безопасность аккаунта",
                body=(
                    "Не передавайте пароль коллегам. Для постоянной работы "
                    "используйте личный аккаунт, а при подозрении на утечку — "
                    "сообщите администратору."
                ),
                target="[data-onboarding='page-content']",
                route="/profile",
                tip="Сессия защищена короткоживущим JWT и refresh-токеном.",
                duration_seconds=25,
            ),
        ),
    ),
    OnboardingModule(
        code="onboarding-navigation",
        service_code="onboarding",
        stage="start",
        title="Как проходить обучение",
        description=(
            "Обучение разбито на этапы и шаги. Его можно проходить за "
            "несколько дней, а прогресс сохраняется автоматически."
        ),
        icon="🎓",
        estimated_minutes=4,
        roles=None,
        required_permissions=("onboarding.courses.read",),
        steps=(
            OnboardingStep(
                code="find",
                title="Центр обучения",
                body=(
                    "Раздел «Обучение работе» всегда доступен в меню. Здесь "
                    "собраны этапы, модули и ваш общий прогресс."
                ),
                target="[data-onboarding-nav='onboarding']",
                route="/",
                tip="Обучение включено по умолчанию для всех пользователей.",
                action="click",
                duration_seconds=25,
            ),
            OnboardingStep(
                code="stages",
                title="Этапы и модули",
                body=(
                    "Этапы идут от первого входа к ежедневной работе и "
                    "управлению. Внутри каждого модуля — короткие шаги с "
                    "анимированной подсказкой."
                ),
                target="[data-onboarding='page-content']",
                route="/onboarding",
                tip="Начните с этапа «Старт», затем переходите к своему сервису.",
                duration_seconds=35,
            ),
            OnboardingStep(
                code="resume",
                title="Можно вернуться завтра",
                body=(
                    "Каждый завершённый шаг сохраняется. Если закрыть окно, "
                    "при следующем входе обучение продолжится с того же места."
                ),
                target="[data-onboarding='page-content']",
                route="/onboarding",
                tip="Прогресс виден администраторам, руководителям и учителям.",
                duration_seconds=30,
            ),
        ),
    ),
    OnboardingModule(
        code="iam-access",
        service_code="iam",
        stage="core",
        title="Пользователи, группы и права",
        description=(
            "Иерархические группы, наследование прав и принцип запрета: "
            "как выдать доступ ровно на нужный уровень."
        ),
        icon="👥",
        estimated_minutes=6,
        roles=("superadmin", "admin", "methodologist"),
        required_permissions=("iam.groups.read", "iam.groups.write"),
        steps=_service_steps(
            nav_code="groups",
            route="/groups",
            focus_title="Откройте группы и права",
            focus_body=(
                "В разделе «Группы и права» собраны группы страны, школы и "
                "класса. Права выдаются группе, а пользователь получает их "
                "через членство."
            ),
            practice_title="Проверьте карточку группы",
            practice_body=(
                "Откройте группу: в карточке видны участники, права, "
                "дочерние группы и источник наследования."
            ),
            safety_body=(
                "На одном уровне запрет важнее разрешения. Не выдавайте "
                "права напрямую отдельному пользователю — используйте группу."
            ),
        ),
    ),
    OnboardingModule(
        code="org-structure",
        service_code="org",
        stage="core",
        title="Школа, классы и структура",
        description=(
            "Как устроены школа, классы и учебные годы; почему класс — "
            "это отдельный контур для прав и обучения."
        ),
        icon="🏫",
        estimated_minutes=5,
        roles=("superadmin", "admin", "methodologist", "secretary"),
        required_permissions=("org.schools.read", "org.classes.read", "org.members.read"),
        steps=_service_steps(
            nav_code="groups",
            route="/groups",
            focus_title="Структура в группах",
            focus_body=(
                "Школа и классы используются как области действия групп. "
                "Классная группа наследует права школьной группы."
            ),
            practice_title="Найдите свою школу и класс",
            practice_body=(
                "Отфильтруйте группы по уровню «Школа» или «Класс» и "
                "посмотрите, какие права наследуются."
            ),
            safety_body=(
                "Не переносите пользователя в чужую школу: это нарушает "
                "мультитенантную изоляцию и доступ к персональным данным."
            ),
        ),
    ),
    OnboardingModule(
        code="audit-security",
        service_code="audit",
        stage="core",
        title="Аудит и безопасность",
        description=(
            "Кто и когда совершил действие, как читать журнал аудита и "
            "почему безопасность — часть ежедневной работы."
        ),
        icon="🛡️",
        estimated_minutes=5,
        roles=("superadmin", "admin"),
        required_permissions=("audit.events.read", "audit.security.read"),
        steps=_service_steps(
            nav_code="services",
            route="/services",
            focus_title="Управление и контроль",
            focus_body=(
                "Административные действия фиксируются в журнале аудита. "
                "Доступ к журналу выдаётся отдельным группам."
            ),
            practice_title="Проверьте свои права",
            practice_body=(
                "В профиле видно, какие права и группы действуют. Если "
                "журнал недоступен — у вашей группы нет соответствующего права."
            ),
            safety_body=(
                "В логах не должно быть паролей, токенов и лишних "
                "персональных данных. Подозрительные события — сразу администратору."
            ),
        ),
    ),
    OnboardingModule(
        code="lms-content",
        service_code="lms",
        stage="daily",
        title="Учебный контент",
        description=(
            "Предметы, темы, уроки и материалы. Как найти нужный контент "
            "и не потеряться в структуре курса."
        ),
        icon="📚",
        estimated_minutes=6,
        roles=None,
        required_permissions=("lms.content.read", "lms.content.write"),
        steps=_service_steps(
            nav_code="lms",
            route="/lms",
            focus_title="Откройте учебный контент",
            focus_body=(
                "В разделе LMS собраны предметы, темы, уроки, учебники и "
                "медиаматериалы. Начните с поиска по названию темы."
            ),
            practice_title="Найдите тему урока",
            practice_body=(
                "Выберите предмет и тему. Обратите внимание на материалы "
                "урока и связанные задания — они пригодятся при подготовке."
            ),
            safety_body=(
                "Изменять и публиковать контент могут только группы с "
                "правами write/publish. Чужие материалы не редактируйте."
            ),
        ),
    ),
    OnboardingModule(
        code="assessment-work",
        service_code="assessment",
        stage="daily",
        title="Тесты, работы и результаты",
        description=(
            "Как назначить работу, сдать её и посмотреть результат. "
            "Отдельные сценарии для учителя и ученика."
        ),
        icon="📝",
        estimated_minutes=6,
        roles=None,
        required_permissions=(
            "assessment.quizzes.read",
            "assessment.submissions.submit",
            "assessment.results.read",
        ),
        steps=_service_steps(
            nav_code="assessment",
            route="/assessment",
            focus_title="Откройте тесты и работы",
            focus_body=(
                "Раздел «Тесты и работы» показывает доступные задания и "
                "результаты. Учитель видит назначения, ученик — свои работы."
            ),
            practice_title="Проверьте ближайшую работу",
            practice_body=(
                "Откройте работу и прочитайте инструкцию до начала. "
                "Ученику важно проверить дедлайн, учителю — состав заданий."
            ),
            safety_body=(
                "Результаты видны только тем, кому разрешено право "
                "assessment.results.read. Не обсуждайте чужие оценки публично."
            ),
        ),
    ),
    OnboardingModule(
        code="journal-daily",
        service_code="journal",
        stage="daily",
        title="Электронный журнал",
        description=(
            "Расписание, оценки, посещаемость и сводки — сердце ежедневной "
            "работы школы."
        ),
        icon="📔",
        estimated_minutes=7,
        roles=None,
        required_permissions=(
            "journal.schedule.read",
            "journal.grades.read",
            "journal.attendance.read",
            "journal.summary.read",
        ),
        steps=_service_steps(
            nav_code="journal",
            route="/journal",
            focus_title="Откройте электронный журнал",
            focus_body=(
                "В журнале собраны расписание, оценки и посещаемость. "
                "Начните с расписания на сегодня."
            ),
            practice_title="Проверьте урок и отметки",
            practice_body=(
                "Учитель выбирает класс и предмет, ученик и родитель видят "
                "только свои данные. Проверьте, что отображается нужный период."
            ),
            safety_body=(
                "Оценки и посещаемость — персональные данные. Не передавайте "
                "их третьим лицам и не делайте скриншоты без необходимости."
            ),
        ),
    ),
    OnboardingModule(
        code="library-reading",
        service_code="library",
        stage="daily",
        title="Библиотека и рекомендации",
        description=(
            "Каталог пособий, доступ по классам, рекомендации учителя и "
            "отметки о прочтении."
        ),
        icon="📖",
        estimated_minutes=5,
        roles=None,
        required_permissions=("library.catalog.read", "library.progress.read"),
        steps=_service_steps(
            nav_code="library",
            route="/library",
            focus_title="Откройте библиотеку",
            focus_body=(
                "В библиотеке можно найти пособие по предмету, классу или "
                "рекомендации учителя. Используйте фильтры, чтобы не листать всё."
            ),
            practice_title="Найдите книгу для своего класса",
            practice_body=(
                "Откройте карточку книги: в ней видны доступные классы, "
                "аннотация и рекомендации. Отметьте прочтение после изучения."
            ),
            safety_body=(
                "Учитель видит прогресс чтения своих учеников. Рекомендации "
                "и отзыв рекомендаций — отдельные права."
            ),
        ),
    ),
    OnboardingModule(
        code="analytics-reports",
        service_code="analytics",
        stage="management",
        title="Аналитика и отчётность",
        description=(
            "Срезы по классам, школам и региону, экспорт отчётов и "
            "чтение BI-показателей без искажений."
        ),
        icon="📊",
        estimated_minutes=6,
        roles=("superadmin", "admin", "methodologist"),
        required_permissions=("analytics.reports.read", "analytics.bi.read"),
        steps=_service_steps(
            nav_code="analytics",
            route="/analytics",
            focus_title="Откройте аналитику",
            focus_body=(
                "В аналитике собраны отчёты и показатели. Сначала выберите "
                "период и школу, затем — нужный срез."
            ),
            practice_title="Сравните два среза",
            practice_body=(
                "Сравните классы или параллели. Обращайте внимание на "
                "размер выборки: маленькие группы дают менее устойчивые выводы."
            ),
            safety_body=(
                "Выгрузка отчётов — отдельное право. Перед публикацией "
                "проверьте, что в файле нет лишних персональных данных."
            ),
        ),
    ),
    OnboardingModule(
        code="documents-flow",
        service_code="documents",
        stage="management",
        title="Документы и заявления",
        description=(
            "Шаблоны справок, заявления, согласия и обработка запросов "
            "в школьном документообороте."
        ),
        icon="📄",
        estimated_minutes=5,
        roles=None,
        required_permissions=(
            "documents.templates.read",
            "documents.requests.create",
            "documents.requests.process",
        ),
        steps=_service_steps(
            nav_code="documents",
            route="/documents",
            focus_title="Откройте документы",
            focus_body=(
                "В разделе документов доступны шаблоны и заявки. "
                "Начните с шаблона, а не с пустого документа."
            ),
            practice_title="Выберите шаблон",
            practice_body=(
                "Проверьте поля шаблона и срок действия. Заявка создаётся "
                "от вашего имени и попадает в обработку по правам группы."
            ),
            safety_body=(
                "Согласия и документы детей — защищённые данные. "
                "Скачивайте только то, что нужно для текущей задачи."
            ),
        ),
    ),
    OnboardingModule(
        code="admin-school",
        service_code="admin",
        stage="management",
        title="Администрирование школы",
        description=(
            "Пользователи, статистика, регионы и республиканские панели. "
            "Как управлять контуром, не нарушая изоляцию школ."
        ),
        icon="🛠️",
        estimated_minutes=7,
        roles=("superadmin", "admin", "methodologist"),
        required_permissions=(
            "admin.school.read",
            "admin.school.manage",
            "admin.region.manage",
            "admin.country.manage",
        ),
        steps=_service_steps(
            nav_code="admin",
            route="/admin",
            focus_title="Откройте администрирование",
            focus_body=(
                "Административная панель показывает статистику школы и "
                "пользователей. Для супер-администратора доступен выбор школы."
            ),
            practice_title="Проверьте свою область",
            practice_body=(
                "Убедитесь, что вы работаете в правильной школе. "
                "Данные другой школы не должны быть видны."
            ),
            safety_body=(
                "Права администратора не отменяют аудит. Каждое изменение "
                "пользователей и сервисов фиксируется в журнале."
            ),
        ),
    ),
    OnboardingModule(
        code="communication-space",
        service_code="communication",
        stage="advanced",
        title="Коммуникации",
        description=(
            "Объявления, чаты и видеосвязь. Правила общения и границы "
            "личного пространства."
        ),
        icon="💬",
        estimated_minutes=5,
        roles=None,
        required_permissions=(
            "communication.chat.use",
            "communication.announcements.read",
            "communication.announcements.write",
            "communication.video.use",
        ),
        steps=_service_steps(
            nav_code="communication",
            route="/communication",
            focus_title="Откройте коммуникации",
            focus_body=(
                "В разделе коммуникаций собраны объявления и чаты. "
                "Проверьте, какие каналы доступны вашей группе."
            ),
            practice_title="Найдите объявление",
            practice_body=(
                "Прочитайте закреплённое объявление. Публикация доступна "
                "только группам с правом announcements.write."
            ),
            safety_body=(
                "Не пересылайте личные сообщения и фотографии детей. "
                "Для видеосвязи используйте только согласованные каналы."
            ),
        ),
    ),
    OnboardingModule(
        code="safety-support",
        service_code="safety",
        stage="advanced",
        title="Безопасность и поддержка",
        description=(
            "Психологическая поддержка, обращения, инциденты и согласия. "
            "Деликатные сценарии с защитой персональных данных."
        ),
        icon="🧠",
        estimated_minutes=6,
        roles=None,
        required_permissions=(
            "safety.support.use",
            "safety.incidents.read",
            "safety.incidents.manage",
            "safety.consents.manage",
        ),
        steps=_service_steps(
            nav_code="safety",
            route="/safety",
            focus_title="Откройте безопасность",
            focus_body=(
                "Раздел помогает обратиться за поддержкой и сообщить об "
                "инциденте. Доступ к разным сценариям зависит от роли."
            ),
            practice_title="Выберите безопасный сценарий",
            practice_body=(
                "Психолог видит обращения, ученик — форму поддержки, "
                "администратор — инциденты. Не смешивайте эти роли."
            ),
            safety_body=(
                "Обращения и согласия — особо чувствительные данные. "
                "Обсуждайте их только с уполномоченными специалистами."
            ),
        ),
    ),
    OnboardingModule(
        code="ai-assistant",
        service_code="ai",
        stage="advanced",
        title="ИИ-помощник",
        description=(
            "Объяснения, генерация заданий и проверка работ. Как использовать "
            "ИИ ответственно и не подменять педагогическое решение."
        ),
        icon="🤖",
        estimated_minutes=6,
        roles=None,
        required_permissions=(
            "ai.explain.use",
            "ai.generate.use",
            "ai.check.use",
            "ai.validate.use",
        ),
        steps=_service_steps(
            nav_code="ai",
            route="/ai",
            focus_title="Откройте ИИ-помощник",
            focus_body=(
                "ИИ-помощник объясняет материал, помогает с заданиями и "
                "проверкой. Он не заменяет учителя и не выставляет оценки сам."
            ),
            practice_title="Сформулируйте учебную задачу",
            practice_body=(
                "Опишите класс, тему и цель. Проверьте результат по учебной "
                "программе и только потом используйте в работе."
            ),
            safety_body=(
                "Не отправляйте в ИИ персональные данные детей. "
                "Проверяйте сгенерированный контент перед публикацией."
            ),
        ),
    ),
)

MODULE_BY_CODE: dict[str, OnboardingModule] = {
    module.code: module for module in MODULES
}

STAGE_BY_CODE: dict[str, dict[str, str]] = {
    stage["code"]: stage for stage in STAGES
}


def get_module(code: str) -> OnboardingModule | None:
    return MODULE_BY_CODE.get(code)


def modules_for_service(service_code: str) -> tuple[OnboardingModule, ...]:
    return tuple(
        module for module in MODULES if module.service_code == service_code
    )
