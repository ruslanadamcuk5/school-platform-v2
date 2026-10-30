"""Domain models.

Importing this package registers every model on ``Base.metadata`` so Alembic
and the application see the complete schema.
"""
from app.models.ai import AIExplanation, AIRequest, AISetting
from app.models.analytics import Attempt, DailyAnswer, MethodProgress, TopicProgress
from app.models.assessment import (
    Answer,
    AnswerOption,
    Assignment,
    GradingScale,
    PlaySession,
    Question,
    Quiz,
    Submission,
)
from app.models.audit import AuditEvent
from app.models.communication import Notification
from app.models.iam import (
    GroupMembership,
    GroupPermission,
    Permission,
    RefreshToken,
    User,
    UserGroup,
    UserRelation,
)
from app.models.journal import JournalEntry, LessonSchedule
from app.models.lms import (
    Course,
    CourseClass,
    CourseTopic,
    Lesson,
    LessonBlock,
    LibraryItem,
    LibraryItemClass,
    LibraryRecommendation,
    LibraryRecommendationStatus,
    Method,
    StoredFile,
    Subject,
    Textbook,
    TextbookTopic,
    Topic,
    UserBadge,
)
from app.models.org import City, ClassMembership, Region, School, SchoolClass, TeacherSubject
from app.models.system import (
    FeatureFlag,
    ImportRun,
    Language,
    Service,
    ServiceActivation,
    Setting,
)

__all__ = [
    "AIExplanation",
    "AIRequest",
    "AISetting",
    "Answer",
    "AnswerOption",
    "Assignment",
    "Attempt",
    "AuditEvent",
    "City",
    "ClassMembership",
    "Course",
    "CourseClass",
    "CourseTopic",
    "DailyAnswer",
    "FeatureFlag",
    "GradingScale",
    "GroupMembership",
    "GroupPermission",
    "ImportRun",
    "JournalEntry",
    "Language",
    "Lesson",
    "LessonBlock",
    "LessonSchedule",
    "LibraryItem",
    "LibraryItemClass",
    "LibraryRecommendation",
    "LibraryRecommendationStatus",
    "Method",
    "MethodProgress",
    "Notification",
    "Permission",
    "PlaySession",
    "Question",
    "Quiz",
    "RefreshToken",
    "Region",
    "School",
    "SchoolClass",
    "Service",
    "ServiceActivation",
    "Setting",
    "StoredFile",
    "Subject",
    "Submission",
    "TeacherSubject",
    "Textbook",
    "TextbookTopic",
    "Topic",
    "TopicProgress",
    "User",
    "UserBadge",
    "UserGroup",
    "UserRelation",
]
