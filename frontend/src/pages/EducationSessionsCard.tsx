import { useEffect, useMemo, useState } from 'react';
import {
  Award,
  BookOpenCheck,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronUp,
  FileText,
  Plus,
  RefreshCw,
  X,
} from 'lucide-react';

import {
  apiErrorMessage,
  createAcademicSession,
  createCreditTransfer,
  createSessionStatement,
  fetchAcademicSessions,
  fetchCreditTransfers,
  fetchSessionStatements,
  fetchStudentTranscript,
  updateAcademicSession,
  updateCreditTransfer,
  updateSessionStatement,
  upsertStatementRecords,
} from '../api/client';
import type {
  AcademicSession,
  CreditTransfer,
  CreditTransferStatus,
  EducationCurriculum,
  EducationGroup,
  EducationLevel,
  SessionStatement,
  SessionStatus,
  SessionType,
  StaffAcademicProfile,
  StatementResult,
  StudentAcademicProfile,
  Transcript,
} from '../api/types';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Modal,
  Skeleton,
} from '../components/ui';
import { formatDate, pluralize } from '../lib/labels';

const SESSION_STATUS_LABELS: Record<SessionStatus, string> = {
  planned: 'Планируется',
  active: 'Идёт',
  completed: 'Завершена',
  archived: 'Архив',
};

const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  winter: 'Зимняя',
  summer: 'Летняя',
  additional: 'Дополнительная',
  other: 'Иная',
};

const STATEMENT_STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик',
  published: 'Опубликована',
  approved: 'Утверждена',
  archived: 'Архив',
};

const RESULT_LABELS: Record<StatementResult, string> = {
  planned: 'Не выставлен',
  passed: 'Зачтено',
  failed: 'Не зачтено',
  not_appeared: 'Не явился',
  exempt: 'Освобождён',
  transferred: 'Перезачтён',
};

const TRANSFER_STATUS_LABELS: Record<CreditTransferStatus, string> = {
  draft: 'Черновик',
  pending: 'На рассмотрении',
  approved: 'Одобрен',
  rejected: 'Отклонён',
  archived: 'Архив',
};

type SessionForm = {
  name: string;
  academic_year: string;
  semester: string;
  session_type: SessionType;
  starts_on: string;
  ends_on: string;
  status: SessionStatus;
  description: string;
};

type StatementForm = {
  group_id: string;
  component_id: string;
  teacher_id: string;
  statement_number: string;
  issued_on: string;
  notes: string;
};

type RecordDraft = {
  grade: string;
  result: StatementResult;
  credits: string;
  comment: string;
};

type RecordStudent = {
  student_id: string;
  name: string;
  login: string;
};

type TransferForm = {
  student_id: string;
  target_component_id: string;
  source_institution: string;
  source_program: string;
  source_component_code: string;
  source_component_name: string;
  source_academic_year: string;
  source_credits: string;
  awarded_credits: string;
  source_grade: string;
  document_number: string;
  reason: string;
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function currentAcademicYear(): string {
  const now = new Date();
  const start = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
  return `${start}/${start + 1}`;
}

function displayNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function errorText(reason: unknown): string {
  return apiErrorMessage(reason);
}

export function EducationSessionsCard({
  level,
  schoolId,
  academicYear,
  groups,
  curricula,
  profiles,
  staff,
  canManage,
  onDataChanged,
}: {
  level: EducationLevel;
  schoolId: string;
  academicYear?: string;
  groups: EducationGroup[];
  curricula: EducationCurriculum[];
  profiles: StudentAcademicProfile[];
  staff: StaffAcademicProfile[];
  canManage: boolean;
  onDataChanged: () => void;
}) {
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [expandedSessionId, setExpandedSessionId] = useState<string | null>(
    null,
  );
  const [statements, setStatements] = useState<
    Record<string, SessionStatement[]>
  >({});
  const [statementsLoading, setStatementsLoading] = useState<string | null>(
    null,
  );
  const [statementsError, setStatementsError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [sessionModalOpen, setSessionModalOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<AcademicSession | null>(
    null,
  );
  const [sessionSaving, setSessionSaving] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [sessionForm, setSessionForm] = useState<SessionForm>({
    name: 'Зимняя сессия',
    academic_year: currentAcademicYear(),
    semester: '1',
    session_type: 'winter',
    starts_on: '',
    ends_on: '',
    status: 'planned',
    description: '',
  });

  const [statementModalSession, setStatementModalSession] =
    useState<AcademicSession | null>(null);
  const [statementSaving, setStatementSaving] = useState(false);
  const [statementError, setStatementError] = useState<string | null>(null);
  const [statementForm, setStatementForm] = useState<StatementForm>({
    group_id: '',
    component_id: '',
    teacher_id: '',
    statement_number: '',
    issued_on: today(),
    notes: '',
  });

  const [selectedStatement, setSelectedStatement] =
    useState<SessionStatement | null>(null);
  const [recordStudents, setRecordStudents] = useState<RecordStudent[]>([]);
  const [recordDrafts, setRecordDrafts] = useState<Record<string, RecordDraft>>(
    {},
  );
  const [recordsSaving, setRecordsSaving] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [statementStatusSaving, setStatementStatusSaving] = useState(false);

  const [transfers, setTransfers] = useState<CreditTransfer[]>([]);
  const [transfersLoading, setTransfersLoading] = useState(false);
  const [transfersError, setTransfersError] = useState<string | null>(null);
  const [transferModalOpen, setTransferModalOpen] = useState(false);
  const [transferSaving, setTransferSaving] = useState(false);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [transferForm, setTransferForm] = useState<TransferForm>({
    student_id: '',
    target_component_id: '',
    source_institution: '',
    source_program: '',
    source_component_code: '',
    source_component_name: '',
    source_academic_year: currentAcademicYear(),
    source_credits: '',
    awarded_credits: '',
    source_grade: '',
    document_number: '',
    reason: '',
  });

  const [transcriptProfileId, setTranscriptProfileId] = useState('');
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!schoolId) {
      setSessions([]);
      return;
    }
    setSessionsLoading(true);
    setSessionsError(null);
    fetchAcademicSessions(level, schoolId, academicYear)
      .then((items) => {
        if (!cancelled) setSessions(items);
      })
      .catch((reason) => {
        if (!cancelled) setSessionsError(errorText(reason));
      })
      .finally(() => {
        if (!cancelled) setSessionsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [academicYear, level, reloadKey, schoolId]);

  useEffect(() => {
    let cancelled = false;
    if (!schoolId) {
      setTransfers([]);
      return;
    }
    setTransfersLoading(true);
    setTransfersError(null);
    fetchCreditTransfers(level, schoolId)
      .then((items) => {
        if (!cancelled) setTransfers(items);
      })
      .catch((reason) => {
        if (!cancelled) setTransfersError(errorText(reason));
      })
      .finally(() => {
        if (!cancelled) setTransfersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [level, reloadKey, schoolId]);

  const componentOptions = useMemo(
    () =>
      curricula.flatMap((curriculum) =>
        curriculum.components.map((component) => ({
          id: component.id,
          label: `${curriculum.program_name} · ${component.semester} сем. · ${component.code} ${component.name}`,
          curriculumId: curriculum.id,
          programId: curriculum.program_id,
        })),
      ),
    [curricula],
  );

  const groupOptions = useMemo(
    () => groups.filter((group) => group.is_active),
    [groups],
  );

  const transferComponentOptions = useMemo(
    () =>
      componentOptions.map((component) => ({
        ...component,
        label: `${component.label} · ${displayNumber(
          curricula.find((item) => item.id === component.curriculumId)
            ?.components.find((item) => item.id === component.id)?.credits ?? 0,
        )} з.е.`,
      })),
    [componentOptions, curricula],
  );

  function refresh() {
    setReloadKey((value) => value + 1);
  }

  function openCreateSession() {
    setEditingSession(null);
    setSessionError(null);
    setSessionForm({
      name: 'Зимняя сессия',
      academic_year: academicYear || currentAcademicYear(),
      semester: '1',
      session_type: 'winter',
      starts_on: '',
      ends_on: '',
      status: 'planned',
      description: '',
    });
    setSessionModalOpen(true);
  }

  function openEditSession(item: AcademicSession) {
    setEditingSession(item);
    setSessionError(null);
    setSessionForm({
      name: item.name,
      academic_year: item.academic_year,
      semester: String(item.semester),
      session_type: item.session_type,
      starts_on: item.starts_on ?? '',
      ends_on: item.ends_on ?? '',
      status: item.status,
      description: item.description ?? '',
    });
    setSessionModalOpen(true);
  }

  async function saveSession() {
    if (!sessionForm.name.trim() || !schoolId) return;
    setSessionSaving(true);
    setSessionError(null);
    try {
      const payload = {
        name: sessionForm.name.trim(),
        academic_year: sessionForm.academic_year.trim(),
        semester: Number(sessionForm.semester),
        session_type: sessionForm.session_type,
        starts_on: sessionForm.starts_on || null,
        ends_on: sessionForm.ends_on || null,
        status: sessionForm.status,
        description: sessionForm.description.trim() || null,
      };
      if (editingSession) {
        await updateAcademicSession(
          level,
          schoolId,
          editingSession.id,
          payload,
        );
      } else {
        await createAcademicSession(level, schoolId, payload);
      }
      setSessionModalOpen(false);
      refresh();
      onDataChanged();
    } catch (reason) {
      setSessionError(errorText(reason));
    } finally {
      setSessionSaving(false);
    }
  }

  async function loadStatements(sessionId: string) {
    setStatementsLoading(sessionId);
    setStatementsError(null);
    try {
      const items = await fetchSessionStatements(level, schoolId, sessionId);
      setStatements((current) => ({ ...current, [sessionId]: items }));
    } catch (reason) {
      setStatementsError(errorText(reason));
    } finally {
      setStatementsLoading(null);
    }
  }

  async function toggleSession(item: AcademicSession) {
    if (expandedSessionId === item.id) {
      setExpandedSessionId(null);
      return;
    }
    setExpandedSessionId(item.id);
    if (!statements[item.id]) {
      await loadStatements(item.id);
    }
  }

  function openCreateStatement(item: AcademicSession) {
    setStatementModalSession(item);
    setStatementError(null);
    setStatementForm({
      group_id: groupOptions[0]?.id ?? '',
      component_id: componentOptions[0]?.id ?? '',
      teacher_id: staff[0]?.user_id ?? '',
      statement_number: `В-${item.semester}-${item.academic_year.replace('/', '-')}-${String(
        (statements[item.id]?.length ?? 0) + 1,
      ).padStart(2, '0')}`,
      issued_on: today(),
      notes: '',
    });
  }

  async function saveStatement() {
    if (
      !statementModalSession ||
      !statementForm.group_id ||
      !statementForm.component_id ||
      !statementForm.statement_number.trim()
    ) {
      return;
    }
    setStatementSaving(true);
    setStatementError(null);
    try {
      await createSessionStatement(
        level,
        schoolId,
        statementModalSession.id,
        {
          group_id: statementForm.group_id,
          component_id: statementForm.component_id,
          teacher_id: statementForm.teacher_id || null,
          statement_number: statementForm.statement_number.trim(),
          issued_on: statementForm.issued_on || null,
          notes: statementForm.notes.trim() || null,
        },
      );
      setStatementModalSession(null);
      await loadStatements(statementModalSession.id);
      onDataChanged();
    } catch (reason) {
      setStatementError(errorText(reason));
    } finally {
      setStatementSaving(false);
    }
  }

  function openStatement(item: SessionStatement) {
    const existing = new Map(
      item.records.map((record) => [record.student_id, record]),
    );
    const groupProfiles = profiles.filter(
      (profile) => profile.group_id === item.group_id,
    );
    const known = new Set(groupProfiles.map((profile) => profile.user_id));
    const students: RecordStudent[] = groupProfiles.map((profile) => ({
      student_id: profile.user_id,
      name: profile.full_name,
      login: profile.login,
    }));
    for (const record of item.records) {
      if (!known.has(record.student_id)) {
        students.push({
          student_id: record.student_id,
          name: record.student_name,
          login: record.student_login,
        });
      }
    }
    const drafts: Record<string, RecordDraft> = {};
    for (const student of students) {
      const record = existing.get(student.student_id);
      drafts[student.student_id] = {
        grade: record?.grade ? String(record.grade) : '',
        result: record?.result ?? 'planned',
        credits: record ? String(record.credits_awarded) : '',
        comment: record?.comment ?? '',
      };
    }
    setSelectedStatement(item);
    setRecordStudents(students);
    setRecordDrafts(drafts);
    setRecordsError(null);
  }

  function updateRecordDraft(
    studentId: string,
    patch: Partial<RecordDraft>,
  ) {
    setRecordDrafts((current) => ({
      ...current,
      [studentId]: { ...current[studentId], ...patch },
    }));
  }

  async function saveRecords() {
    if (!selectedStatement) return;
    setRecordsSaving(true);
    setRecordsError(null);
    try {
      const records = recordStudents.map((student) => {
        const draft = recordDrafts[student.student_id];
        return {
          student_id: student.student_id,
          grade: draft.grade ? Number(draft.grade) : null,
          result: draft.result,
          credits_awarded:
            draft.credits.trim() === '' ? null : Number(draft.credits),
          comment: draft.comment.trim() || null,
        };
      });
      const saved = await upsertStatementRecords(
        level,
        schoolId,
        selectedStatement.id,
        records,
      );
      setSelectedStatement(saved);
      setStatements((current) => ({
        ...current,
        [saved.session_id]: (current[saved.session_id] ?? []).map((item) =>
          item.id === saved.id ? saved : item,
        ),
      }));
      onDataChanged();
    } catch (reason) {
      setRecordsError(errorText(reason));
    } finally {
      setRecordsSaving(false);
    }
  }

  async function changeStatementStatus(status: SessionStatement['status']) {
    if (!selectedStatement) return;
    setStatementStatusSaving(true);
    setRecordsError(null);
    try {
      const saved = await updateSessionStatement(
        level,
        schoolId,
        selectedStatement.id,
        { status },
      );
      setSelectedStatement(saved);
      setStatements((current) => ({
        ...current,
        [saved.session_id]: (current[saved.session_id] ?? []).map((item) =>
          item.id === saved.id ? saved : item,
        ),
      }));
      onDataChanged();
    } catch (reason) {
      setRecordsError(errorText(reason));
    } finally {
      setStatementStatusSaving(false);
    }
  }

  function openCreateTransfer() {
    setTransferError(null);
    setTransferForm({
      student_id: profiles[0]?.user_id ?? '',
      target_component_id: '',
      source_institution: '',
      source_program: '',
      source_component_code: '',
      source_component_name: '',
      source_academic_year: academicYear || currentAcademicYear(),
      source_credits: '',
      awarded_credits: '',
      source_grade: '',
      document_number: '',
      reason: '',
    });
    setTransferModalOpen(true);
  }

  async function saveTransfer() {
    if (
      !transferForm.student_id ||
      !transferForm.source_institution.trim() ||
      !transferForm.source_program.trim() ||
      !transferForm.source_component_code.trim() ||
      !transferForm.source_component_name.trim() ||
      !transferForm.source_credits
    ) {
      return;
    }
    setTransferSaving(true);
    setTransferError(null);
    try {
      const target = transferForm.target_component_id
        ? componentOptions.find(
            (component) => component.id === transferForm.target_component_id,
          )
        : undefined;
      await createCreditTransfer(level, schoolId, {
        student_id: transferForm.student_id,
        target_component_id: transferForm.target_component_id || null,
        target_program_id: target?.programId ?? null,
        source_institution: transferForm.source_institution.trim(),
        source_program: transferForm.source_program.trim(),
        source_component_code: transferForm.source_component_code.trim(),
        source_component_name: transferForm.source_component_name.trim(),
        source_academic_year: transferForm.source_academic_year.trim(),
        source_credits: Number(transferForm.source_credits),
        awarded_credits: transferForm.awarded_credits
          ? Number(transferForm.awarded_credits)
          : null,
        source_grade: transferForm.source_grade
          ? Number(transferForm.source_grade)
          : null,
        document_number: transferForm.document_number.trim() || null,
        reason: transferForm.reason.trim() || null,
        status: 'pending',
      });
      setTransferModalOpen(false);
      refresh();
      onDataChanged();
    } catch (reason) {
      setTransferError(errorText(reason));
    } finally {
      setTransferSaving(false);
    }
  }

  async function decideTransfer(
    item: CreditTransfer,
    status: CreditTransferStatus,
  ) {
    setTransfersError(null);
    try {
      await updateCreditTransfer(level, schoolId, item.id, { status });
      refresh();
      onDataChanged();
    } catch (reason) {
      setTransfersError(errorText(reason));
    }
  }

  async function loadTranscript(profileId: string) {
    if (!profileId) return;
    setTranscriptLoading(true);
    setTranscriptError(null);
    try {
      setTranscript(
        await fetchStudentTranscript(level, schoolId, profileId),
      );
    } catch (reason) {
      setTranscript(null);
      setTranscriptError(errorText(reason));
    } finally {
      setTranscriptLoading(false);
    }
  }

  return (
    <>
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Сессии, ведомости и кредиты
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Экзаменационные сессии, зачётные ведомости, перезачёт кредитов и
              зачётные книжки.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
              {pluralize(sessions.length, 'сессия', 'сессии', 'сессий')}
            </Badge>
            {canManage ? (
              <Button size="sm" onClick={openCreateSession}>
                <Plus className="h-4 w-4" />
                Сессия
              </Button>
            ) : null}
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={sessionsLoading}
            >
              <RefreshCw
                className={sessionsLoading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'}
              />
              Обновить
            </Button>
          </div>
        </div>

        {sessionsError ? (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {sessionsError}
          </div>
        ) : sessionsLoading ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-14" />
            <Skeleton className="h-14" />
          </div>
        ) : sessions.length === 0 ? (
          <EmptyState
            title="Сессий пока нет"
            description="Создайте зимнюю или летнюю сессию, затем добавьте ведомости по дисциплинам и группам."
            icon={<CalendarDays className="h-6 w-6" />}
            action={
              canManage ? (
                <Button size="sm" onClick={openCreateSession}>
                  <Plus className="h-4 w-4" />
                  Создать сессию
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className="mt-4 space-y-3">
            {sessions.map((item) => {
              const expanded = expandedSessionId === item.id;
              const sessionStatements = statements[item.id] ?? [];
              return (
                <div
                  key={item.id}
                  className="rounded-xl border border-slate-100"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3 px-3 py-3">
                    <button
                      type="button"
                      onClick={() => void toggleSession(item)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-slate-800">
                          {item.name}
                        </p>
                        <Badge className="bg-brand-50 text-brand-700 ring-brand-200">
                          {SESSION_TYPE_LABELS[item.session_type]}
                        </Badge>
                        <Badge
                          className={
                            item.status === 'active'
                              ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                              : item.status === 'completed'
                                ? 'bg-sky-50 text-sky-700 ring-sky-200'
                                : 'bg-slate-100 text-slate-600 ring-slate-200'
                          }
                        >
                          {SESSION_STATUS_LABELS[item.status]}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {item.academic_year} · {item.semester} семестр
                        {item.starts_on
                          ? ` · ${formatDate(item.starts_on)}`
                          : ''}
                        {item.ends_on ? ` — ${formatDate(item.ends_on)}` : ''}
                      </p>
                    </button>
                    <div className="flex items-center gap-1">
                      {canManage ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditSession(item)}
                          aria-label="Изменить сессию"
                        >
                          <FileText className="h-4 w-4" />
                        </Button>
                      ) : null}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => void toggleSession(item)}
                        aria-label={
                          expanded ? 'Свернуть сессию' : 'Развернуть сессию'
                        }
                      >
                        {expanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {expanded ? (
                    <div className="border-t border-slate-100 px-3 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Ведомости сессии
                        </p>
                        {canManage ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openCreateStatement(item)}
                            disabled={!groupOptions.length || !componentOptions.length}
                          >
                            <Plus className="h-4 w-4" />
                            Ведомость
                          </Button>
                        ) : null}
                      </div>

                      {statementsError ? (
                        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                          {statementsError}
                        </div>
                      ) : statementsLoading === item.id ? (
                        <div className="mt-3 space-y-2">
                          <Skeleton className="h-12" />
                          <Skeleton className="h-12" />
                        </div>
                      ) : sessionStatements.length === 0 ? (
                        <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
                          В сессии пока нет ведомостей. Добавьте ведомость для
                          группы и дисциплины.
                        </p>
                      ) : (
                        <div className="mt-3 space-y-2">
                          {sessionStatements.map((statement) => (
                            <button
                              key={statement.id}
                              type="button"
                              onClick={() => openStatement(statement)}
                              className="w-full rounded-xl border border-slate-100 px-3 py-2 text-left transition hover:border-brand-200 hover:bg-brand-50/40"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-slate-800">
                                  {statement.component_name}
                                </p>
                                <Badge
                                  className={
                                    statement.status === 'approved'
                                      ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                                      : statement.status === 'published'
                                        ? 'bg-sky-50 text-sky-700 ring-sky-200'
                                        : 'bg-slate-100 text-slate-600 ring-slate-200'
                                  }
                                >
                                  {STATEMENT_STATUS_LABELS[statement.status]}
                                </Badge>
                              </div>
                              <p className="mt-1 text-xs text-slate-500">
                                № {statement.statement_number} ·{' '}
                                {statement.group_name} ·{' '}
                                {statement.component_code} ·{' '}
                                {pluralize(
                                  statement.records.length,
                                  'студент',
                                  'студента',
                                  'студентов',
                                )}
                                {statement.teacher_name
                                  ? ` · ${statement.teacher_name}`
                                  : ''}
                              </p>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Перезачёт кредитов
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Признание дисциплин и кредитов, полученных в другом учреждении или
              по другой программе.
            </p>
          </div>
          {canManage ? (
            <Button size="sm" onClick={openCreateTransfer}>
              <Plus className="h-4 w-4" />
              Новый перезачёт
            </Button>
          ) : null}
        </div>

        {transfersError ? (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {transfersError}
          </div>
        ) : transfersLoading ? (
          <div className="mt-4 space-y-2">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : transfers.length === 0 ? (
          <EmptyState
            title="Перезачётов пока нет"
            description="Добавьте сведения о дисциплине, изученной в другом учреждении, и примите решение о перезачёте."
            icon={<Award className="h-6 w-6" />}
          />
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2 font-semibold">Студент</th>
                  <th className="px-2 py-2 font-semibold">Источник</th>
                  <th className="px-2 py-2 font-semibold">Дисциплина</th>
                  <th className="px-2 py-2 text-right font-semibold">Кредиты</th>
                  <th className="px-2 py-2 font-semibold">Статус</th>
                  {canManage ? (
                    <th className="px-2 py-2 text-right font-semibold"> </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {transfers.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-slate-50 last:border-0"
                  >
                    <td className="px-2 py-2.5">
                      <p className="font-semibold text-slate-800">
                        {item.student_name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {item.student_login}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      <p>{item.source_institution}</p>
                      <p className="text-xs text-slate-500">
                        {item.source_program} · {item.source_academic_year}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      <p>{item.source_component_name}</p>
                      <p className="text-xs text-slate-500">
                        {item.source_component_code}
                        {item.target_component_code
                          ? ` → ${item.target_component_code}`
                          : ''}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-right text-slate-600">
                      {displayNumber(item.awarded_credits)}
                      {item.source_credits !== item.awarded_credits
                        ? ` / ${displayNumber(item.source_credits)}`
                        : ''}
                    </td>
                    <td className="px-2 py-2.5">
                      <Badge
                        className={
                          item.status === 'approved'
                            ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                            : item.status === 'rejected'
                              ? 'bg-rose-50 text-rose-700 ring-rose-200'
                              : 'bg-amber-50 text-amber-700 ring-amber-200'
                        }
                      >
                        {TRANSFER_STATUS_LABELS[item.status]}
                      </Badge>
                    </td>
                    {canManage ? (
                      <td className="px-2 py-2.5 text-right">
                        {item.status === 'pending' || item.status === 'draft' ? (
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                void decideTransfer(item, 'approved')
                              }
                              aria-label="Одобрить перезачёт"
                            >
                              <Check className="h-4 w-4 text-emerald-600" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                void decideTransfer(item, 'rejected')
                              }
                              aria-label="Отклонить перезачёт"
                            >
                              <X className="h-4 w-4 text-rose-500" />
                            </Button>
                          </div>
                        ) : null}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Зачётная книжка
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Итоговые кредиты по утверждённым ведомостям и одобренным
              перезачётам.
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Обучающийся
              </span>
              <select
                value={transcriptProfileId}
                onChange={(event) => {
                  setTranscriptProfileId(event.target.value);
                  setTranscript(null);
                }}
                className="h-9 min-w-56 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Выберите обучающегося</option>
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.full_name}
                    {profile.record_book_number
                      ? ` · ${profile.record_book_number}`
                      : ''}
                  </option>
                ))}
              </select>
            </label>
            <Button
              size="sm"
              onClick={() => void loadTranscript(transcriptProfileId)}
              loading={transcriptLoading}
              disabled={!transcriptProfileId}
            >
              <BookOpenCheck className="h-4 w-4" />
              Показать
            </Button>
          </div>
        </div>

        {transcriptError ? (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {transcriptError}
          </div>
        ) : null}

        {transcript ? (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Обучающийся
                </p>
                <p className="mt-0.5 text-sm font-semibold text-slate-800">
                  {transcript.full_name}
                </p>
                <p className="text-xs text-slate-500">
                  {transcript.record_book_number ?? transcript.login}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Программа
                </p>
                <p className="mt-0.5 text-sm font-semibold text-slate-800">
                  {transcript.program_name ?? '—'}
                </p>
                <p className="text-xs text-slate-500">
                  {transcript.group_name ?? '—'}
                </p>
              </div>
              <div className="rounded-xl bg-slate-50 px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Кредиты
                </p>
                <p className="mt-0.5 text-sm font-semibold text-slate-800">
                  {displayNumber(transcript.total_credits)} /{' '}
                  {displayNumber(transcript.curriculum_total_credits)} з.е.
                </p>
                <p className="text-xs text-slate-500">
                  {transcript.progress_percent}% учебного плана
                </p>
              </div>
            </div>

            {transcript.items.length === 0 ? (
              <p className="rounded-xl bg-slate-50 px-3 py-3 text-sm text-slate-500">
                В зачётной книжке пока нет утверждённых результатов.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                      <th className="px-2 py-2 font-semibold">Дисциплина</th>
                      <th className="px-2 py-2 text-right font-semibold">Сем.</th>
                      <th className="px-2 py-2 text-right font-semibold">
                        Кредиты
                      </th>
                      <th className="px-2 py-2 text-right font-semibold">
                        Оценка
                      </th>
                      <th className="px-2 py-2 font-semibold">Результат</th>
                      <th className="px-2 py-2 font-semibold">Основание</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transcript.items.map((item, index) => (
                      <tr
                        key={`${item.source}-${item.statement_id ?? item.transfer_id}-${index}`}
                        className="border-b border-slate-50 last:border-0"
                      >
                        <td className="px-2 py-2.5">
                          <p className="font-semibold text-slate-800">
                            {item.component_name}
                          </p>
                          <p className="text-xs text-slate-500">
                            {item.component_code}
                          </p>
                        </td>
                        <td className="px-2 py-2.5 text-right text-slate-600">
                          {item.semester ?? '—'}
                        </td>
                        <td className="px-2 py-2.5 text-right text-slate-600">
                          {displayNumber(item.credits)}
                        </td>
                        <td className="px-2 py-2.5 text-right text-slate-600">
                          {item.grade ?? '—'}
                        </td>
                        <td className="px-2 py-2.5 text-slate-600">
                          {item.result === 'recognized'
                            ? 'Перезачтено'
                            : RESULT_LABELS[item.result]}
                        </td>
                        <td className="px-2 py-2.5 text-slate-600">
                          {item.source === 'statement'
                            ? `Ведомость № ${item.statement_number ?? '—'}`
                            : `Перезачёт № ${item.document_number ?? '—'}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : null}
      </Card>

      <Modal
        open={sessionModalOpen}
        onClose={() => setSessionModalOpen(false)}
        title={editingSession ? 'Изменить сессию' : 'Новая сессия'}
        description="Сессия объединяет ведомости по дисциплинам и группам на выбранный учебный год."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setSessionModalOpen(false)}
              disabled={sessionSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveSession()}
              loading={sessionSaving}
              disabled={!sessionForm.name.trim() || !schoolId}
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {sessionError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {sessionError}
            </div>
          ) : null}
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Название
            </span>
            <input
              value={sessionForm.name}
              onChange={(event) =>
                setSessionForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              placeholder="Зимняя сессия"
              className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учебный год
              </span>
              <input
                value={sessionForm.academic_year}
                onChange={(event) =>
                  setSessionForm((current) => ({
                    ...current,
                    academic_year: event.target.value,
                  }))
                }
                placeholder="2025/2026"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Семестр
              </span>
              <input
                type="number"
                min={1}
                max={12}
                value={sessionForm.semester}
                onChange={(event) =>
                  setSessionForm((current) => ({
                    ...current,
                    semester: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Тип
              </span>
              <select
                value={sessionForm.session_type}
                onChange={(event) =>
                  setSessionForm((current) => ({
                    ...current,
                    session_type: event.target.value as SessionType,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {Object.entries(SESSION_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Статус
              </span>
              <select
                value={sessionForm.status}
                onChange={(event) =>
                  setSessionForm((current) => ({
                    ...current,
                    status: event.target.value as SessionStatus,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {Object.entries(SESSION_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Начало
              </span>
              <input
                type="date"
                value={sessionForm.starts_on}
                onChange={(event) =>
                  setSessionForm((current) => ({
                    ...current,
                    starts_on: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Окончание
              </span>
              <input
                type="date"
                value={sessionForm.ends_on}
                onChange={(event) =>
                  setSessionForm((current) => ({
                    ...current,
                    ends_on: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Описание
            </span>
            <textarea
              value={sessionForm.description}
              onChange={(event) =>
                setSessionForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
        </div>
      </Modal>

      <Modal
        open={statementModalSession !== null}
        onClose={() => setStatementModalSession(null)}
        title="Новая ведомость"
        description="Ведомость создаётся для одной группы и одного компонента учебного плана."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setStatementModalSession(null)}
              disabled={statementSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveStatement()}
              loading={statementSaving}
              disabled={
                !statementForm.group_id ||
                !statementForm.component_id ||
                !statementForm.statement_number.trim()
              }
            >
              Создать
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {statementError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {statementError}
            </div>
          ) : null}
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Группа
            </span>
            <select
              value={statementForm.group_id}
              onChange={(event) =>
                setStatementForm((current) => ({
                  ...current,
                  group_id: event.target.value,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Выберите группу</option>
              {groupOptions.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name} · {group.course_year ?? '—'} курс
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Компонент учебного плана
            </span>
            <select
              value={statementForm.component_id}
              onChange={(event) =>
                setStatementForm((current) => ({
                  ...current,
                  component_id: event.target.value,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Выберите компонент</option>
              {componentOptions.map((component) => (
                <option key={component.id} value={component.id}>
                  {component.label}
                </option>
              ))}
            </select>
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Номер ведомости
              </span>
              <input
                value={statementForm.statement_number}
                onChange={(event) =>
                  setStatementForm((current) => ({
                    ...current,
                    statement_number: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Дата
              </span>
              <input
                type="date"
                value={statementForm.issued_on}
                onChange={(event) =>
                  setStatementForm((current) => ({
                    ...current,
                    issued_on: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Преподаватель
            </span>
            <select
              value={statementForm.teacher_id}
              onChange={(event) =>
                setStatementForm((current) => ({
                  ...current,
                  teacher_id: event.target.value,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Не указан</option>
              {staff.map((member) => (
                <option key={member.user_id} value={member.user_id}>
                  {member.full_name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Примечание
            </span>
            <textarea
              value={statementForm.notes}
              onChange={(event) =>
                setStatementForm((current) => ({
                  ...current,
                  notes: event.target.value,
                }))
              }
              rows={2}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
        </div>
      </Modal>

      <Modal
        open={selectedStatement !== null}
        onClose={() => setSelectedStatement(null)}
        title={
          selectedStatement
            ? `Ведомость № ${selectedStatement.statement_number}`
            : 'Ведомость'
        }
        description={
          selectedStatement
            ? `${selectedStatement.component_name} · ${selectedStatement.group_name} · ${selectedStatement.curriculum_name}`
            : undefined
        }
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setSelectedStatement(null)}
              disabled={recordsSaving || statementStatusSaving}
            >
              Закрыть
            </Button>
            {canManage &&
            selectedStatement &&
            !['approved', 'archived'].includes(selectedStatement.status) ? (
              <Button
                variant="secondary"
                onClick={() => void changeStatementStatus('approved')}
                loading={statementStatusSaving}
              >
                <Check className="h-4 w-4" />
                Утвердить
              </Button>
            ) : null}
            {canManage &&
            selectedStatement &&
            !['approved', 'archived'].includes(selectedStatement.status) ? (
              <Button onClick={() => void saveRecords()} loading={recordsSaving}>
                Сохранить результаты
              </Button>
            ) : null}
          </>
        }
      >
        <div className="space-y-4">
          {recordsError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {recordsError}
            </div>
          ) : null}
          {selectedStatement ? (
            <div className="flex flex-wrap gap-2 text-xs text-slate-500">
              <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                {STATEMENT_STATUS_LABELS[selectedStatement.status]}
              </Badge>
              <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                {selectedStatement.component_code}
              </Badge>
              <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                {displayNumber(selectedStatement.component_credits)} з.е.
              </Badge>
              <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                {selectedStatement.semester} семестр
              </Badge>
              <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                {formatDate(selectedStatement.issued_on)}
              </Badge>
            </div>
          ) : null}

          {recordStudents.length === 0 ? (
            <p className="rounded-xl bg-slate-50 px-3 py-3 text-sm text-slate-500">
              В группе нет обучающихся с академическими профилями.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                    <th className="px-2 py-2 font-semibold">Студент</th>
                    <th className="px-2 py-2 font-semibold">Оценка</th>
                    <th className="px-2 py-2 font-semibold">Результат</th>
                    <th className="px-2 py-2 font-semibold">Кредиты</th>
                    <th className="px-2 py-2 font-semibold">Комментарий</th>
                  </tr>
                </thead>
                <tbody>
                  {recordStudents.map((student) => {
                    const draft = recordDrafts[student.student_id];
                    const editable =
                      canManage &&
                      selectedStatement !== null &&
                      !['approved', 'archived'].includes(
                        selectedStatement.status,
                      );
                    return (
                      <tr
                        key={student.student_id}
                        className="border-b border-slate-50 last:border-0"
                      >
                        <td className="px-2 py-2">
                          <p className="font-semibold text-slate-800">
                            {student.name}
                          </p>
                          <p className="text-xs text-slate-500">
                            {student.login}
                          </p>
                        </td>
                        <td className="px-2 py-2">
                          <input
                            type="number"
                            min={1}
                            max={10}
                            value={draft?.grade ?? ''}
                            disabled={!editable}
                            onChange={(event) =>
                              updateRecordDraft(student.student_id, {
                                grade: event.target.value,
                              })
                            }
                            className="h-8 w-20 rounded-lg border border-slate-200 px-2 text-sm outline-none disabled:bg-slate-50 focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                          />
                        </td>
                        <td className="px-2 py-2">
                          <select
                            value={draft?.result ?? 'planned'}
                            disabled={!editable}
                            onChange={(event) =>
                              updateRecordDraft(student.student_id, {
                                result: event.target.value as StatementResult,
                              })
                            }
                            className="h-8 w-40 rounded-lg border border-slate-200 bg-white px-2 text-sm outline-none disabled:bg-slate-50 focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                          >
                            {Object.entries(RESULT_LABELS).map(
                              ([value, label]) => (
                                <option key={value} value={value}>
                                  {label}
                                </option>
                              ),
                            )}
                          </select>
                        </td>
                        <td className="px-2 py-2">
                          <input
                            type="number"
                            min={0}
                            max={100}
                            step="0.01"
                            value={draft?.credits ?? ''}
                            disabled={!editable}
                            onChange={(event) =>
                              updateRecordDraft(student.student_id, {
                                credits: event.target.value,
                              })
                            }
                            className="h-8 w-24 rounded-lg border border-slate-200 px-2 text-sm outline-none disabled:bg-slate-50 focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                          />
                        </td>
                        <td className="px-2 py-2">
                          <input
                            value={draft?.comment ?? ''}
                            disabled={!editable}
                            onChange={(event) =>
                              updateRecordDraft(student.student_id, {
                                comment: event.target.value,
                              })
                            }
                            placeholder="—"
                            className="h-8 w-full min-w-40 rounded-lg border border-slate-200 px-2 text-sm outline-none disabled:bg-slate-50 focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Modal>

      <Modal
        open={transferModalOpen}
        onClose={() => setTransferModalOpen(false)}
        title="Новый перезачёт кредитов"
        description="Укажите дисциплину и кредиты, полученные в другом учреждении или по другой программе."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setTransferModalOpen(false)}
              disabled={transferSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveTransfer()}
              loading={transferSaving}
              disabled={
                !transferForm.student_id ||
                !transferForm.source_institution.trim() ||
                !transferForm.source_program.trim() ||
                !transferForm.source_component_code.trim() ||
                !transferForm.source_component_name.trim() ||
                !transferForm.source_credits
              }
            >
              Отправить на рассмотрение
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {transferError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {transferError}
            </div>
          ) : null}
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Обучающийся
            </span>
            <select
              value={transferForm.student_id}
              onChange={(event) =>
                setTransferForm((current) => ({
                  ...current,
                  student_id: event.target.value,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Выберите обучающегося</option>
              {profiles.map((profile) => (
                <option key={profile.id} value={profile.user_id}>
                  {profile.full_name}
                  {profile.record_book_number
                    ? ` · ${profile.record_book_number}`
                    : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Дисциплина в текущем плане (необязательно)
            </span>
            <select
              value={transferForm.target_component_id}
              onChange={(event) =>
                setTransferForm((current) => ({
                  ...current,
                  target_component_id: event.target.value,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Не привязывать</option>
              {transferComponentOptions.map((component) => (
                <option key={component.id} value={component.id}>
                  {component.label}
                </option>
              ))}
            </select>
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учреждение-источник
              </span>
              <input
                value={transferForm.source_institution}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_institution: event.target.value,
                  }))
                }
                placeholder="Колледж №1"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Программа-источник
              </span>
              <input
                value={transferForm.source_program}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_program: event.target.value,
                  }))
                }
                placeholder="Программирование"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Код дисциплины
              </span>
              <input
                value={transferForm.source_component_code}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_component_code: event.target.value,
                  }))
                }
                placeholder="MATH-101"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Название дисциплины
              </span>
              <input
                value={transferForm.source_component_name}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_component_name: event.target.value,
                  }))
                }
                placeholder="Математика"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учебный год источника
              </span>
              <input
                value={transferForm.source_academic_year}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_academic_year: event.target.value,
                  }))
                }
                placeholder="2025/2026"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Номер документа
              </span>
              <input
                value={transferForm.document_number}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    document_number: event.target.value,
                  }))
                }
                placeholder="Справка № 12"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Кредиты источника
              </span>
              <input
                type="number"
                min={0}
                max={100}
                step="0.01"
                value={transferForm.source_credits}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_credits: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Кредиты к зачёту
              </span>
              <input
                type="number"
                min={0}
                max={100}
                step="0.01"
                value={transferForm.awarded_credits}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    awarded_credits: event.target.value,
                  }))
                }
                placeholder="как источник"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Оценка
              </span>
              <input
                type="number"
                min={1}
                max={10}
                value={transferForm.source_grade}
                onChange={(event) =>
                  setTransferForm((current) => ({
                    ...current,
                    source_grade: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Причина и основание
            </span>
            <textarea
              value={transferForm.reason}
              onChange={(event) =>
                setTransferForm((current) => ({
                  ...current,
                  reason: event.target.value,
                }))
              }
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
        </div>
      </Modal>
    </>
  );
}
