import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  FileCheck2,
  HeartHandshake,
  MapPin,
  MessageCircle,
  Plus,
  RefreshCw,
  Send,
  Settings2,
  ShieldCheck,
  ShieldOff,
  XCircle,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  closeSafetyAppeal,
  createSafetyAppeal,
  createSafetyConsent,
  createSafetyIncident,
  fetchMySafetyAppeals,
  fetchSafetyAppeals,
  fetchSafetyConsents,
  fetchSafetyGeolocation,
  fetchSafetyIncidents,
  fetchSafetySettings,
  fetchSchools,
  fetchUsers,
  purgeSafetyData,
  resolveSafetyIncident,
  respondSafetyAppeal,
  revokeSafetyConsent,
  updateSafetySettings,
} from '../api/client';
import type {
  SafetyAppeal,
  SafetyAppealCategory,
  SafetyAppealStatus,
  SafetyConsent,
  SafetyConsentScope,
  SafetyConsentSource,
  SafetyGeolocationEventType,
  SafetyGeolocationPoint,
  SafetyIncident,
  SafetyIncidentCategory,
  SafetyIncidentSeverity,
  SafetyIncidentStatus,
  SafetyPriority,
  SafetyPurgeResult,
  SafetySettings,
  School,
  User,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  Modal,
  PageHeader,
  Skeleton,
  Toggle,
} from '../components/ui';
import { cn } from '../lib/cn';
import { formatDate, formatDateTime } from '../lib/labels';

type TabKey =
  | 'my-appeals'
  | 'school-appeals'
  | 'incidents'
  | 'consents'
  | 'geolocation'
  | 'settings';

const inputClass =
  'h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100';
const textareaClass =
  'min-h-28 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100';
const labelClass = 'mb-1.5 block text-xs font-semibold text-slate-700';
const hintClass = 'mt-1 block text-[11px] text-slate-400';

const appealCategoryLabels: Record<SafetyAppealCategory, string> = {
  psychological: 'Психологическая поддержка',
  conflict: 'Конфликт',
  bullying: 'Травля / буллинг',
  family: 'Семейная ситуация',
  other: 'Другое',
};

const appealStatusLabels: Record<SafetyAppealStatus, string> = {
  open: 'Новое',
  in_progress: 'В работе',
  responded: 'Есть ответ',
  closed: 'Закрыто',
};

const appealStatusColors: Record<SafetyAppealStatus, string> = {
  open: 'bg-amber-50 text-amber-700 ring-amber-200',
  in_progress: 'bg-sky-50 text-sky-700 ring-sky-200',
  responded: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  closed: 'bg-slate-100 text-slate-600 ring-slate-200',
};

const priorityLabels: Record<SafetyPriority, string> = {
  low: 'Низкий',
  medium: 'Средний',
  high: 'Высокий',
  urgent: 'Срочный',
};

const priorityColors: Record<SafetyPriority, string> = {
  low: 'bg-slate-100 text-slate-600 ring-slate-200',
  medium: 'bg-sky-50 text-sky-700 ring-sky-200',
  high: 'bg-amber-50 text-amber-700 ring-amber-200',
  urgent: 'bg-rose-50 text-rose-700 ring-rose-200',
};

const incidentCategoryLabels: Record<SafetyIncidentCategory, string> = {
  bullying: 'Травля / буллинг',
  violence: 'Насилие',
  self_harm: 'Самоповреждение',
  health: 'Здоровье',
  facility: 'Помещение / территория',
  other: 'Другое',
};

const incidentSeverityLabels: Record<SafetyIncidentSeverity, string> = {
  low: 'Низкая',
  medium: 'Средняя',
  high: 'Высокая',
  critical: 'Критическая',
};

const incidentSeverityColors: Record<SafetyIncidentSeverity, string> = {
  low: 'bg-slate-100 text-slate-600 ring-slate-200',
  medium: 'bg-sky-50 text-sky-700 ring-sky-200',
  high: 'bg-amber-50 text-amber-700 ring-amber-200',
  critical: 'bg-rose-50 text-rose-700 ring-rose-200',
};

const incidentStatusLabels: Record<SafetyIncidentStatus, string> = {
  open: 'Открыт',
  investigating: 'Расследование',
  resolved: 'Решён',
  closed: 'Закрыт',
};

const incidentStatusColors: Record<SafetyIncidentStatus, string> = {
  open: 'bg-amber-50 text-amber-700 ring-amber-200',
  investigating: 'bg-sky-50 text-sky-700 ring-sky-200',
  resolved: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  closed: 'bg-slate-100 text-slate-600 ring-slate-200',
};

const consentScopeLabels: Record<SafetyConsentScope, string> = {
  geolocation: 'Геолокация',
  psychological_support: 'Психологическая поддержка',
  incident_reporting: 'Сообщение об инцидентах',
  health_data: 'Данные о здоровье',
};

const consentSourceLabels: Record<SafetyConsentSource, string> = {
  written: 'Письменно',
  electronic: 'Электронно',
  verbal_recorded: 'Устно, с записью',
};

const geolocationEventLabels: Record<SafetyGeolocationEventType, string> = {
  location: 'Точка',
  enter_school: 'Вход в школу',
  leave_school: 'Выход из школы',
};

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className={labelClass}>{label}</span>
      {children}
      {hint ? <span className={hintClass}>{hint}</span> : null}
    </label>
  );
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function FormError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
}

function SchoolScopeNotice() {
  return (
    <Card>
      <EmptyState
        title="Выберите школу"
        description="Для просмотра данных безопасности республиканскому администратору нужно выбрать школу в верхней панели."
        icon={<ShieldCheck className="h-6 w-6" />}
      />
    </Card>
  );
}

function MyAppealsPanel({ schoolId }: { schoolId?: string }) {
  const [appeals, setAppeals] = useState<SafetyAppeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({
    category: 'psychological' as SafetyAppealCategory,
    priority: 'medium' as SafetyPriority,
    subject: '',
    message: '',
    anonymous: false,
    consentGiven: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAppeals(await fetchMySafetyAppeals());
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 6000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  function resetForm() {
    setForm({
      category: 'psychological',
      priority: 'medium',
      subject: '',
      message: '',
      anonymous: false,
      consentGiven: true,
    });
    setFormError(null);
  }

  async function submit() {
    if (!form.subject.trim() || !form.message.trim()) {
      setFormError('Заполните тему и сообщение.');
      return;
    }
    if (!form.consentGiven) {
      setFormError('Для обработки обращения нужно согласие.');
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      const created = await createSafetyAppeal({
        school_id: schoolId ?? null,
        category: form.category,
        priority: form.priority,
        subject: form.subject.trim(),
        message: form.message.trim(),
        is_anonymous: form.anonymous,
        consent_required: true,
        consent_given: form.consentGiven,
      });
      setFormOpen(false);
      resetForm();
      setNotice(
        created.is_anonymous
          ? `Анонимное обращение принято. Номер: ${created.id}. Сохраните его — обращение не отображается в списке «Мои обращения».`
          : 'Обращение отправлено психологу.',
      );
      await load();
    } catch (caught) {
      setFormError(apiErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      {notice ? <Notice>{notice}</Notice> : null}
      <Card className="p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-900">
              Обращение к психологу
            </p>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Можно обратиться от своего имени или анонимно. Анонимное обращение
              не сохраняет связь с учётной записью, поэтому его номер нужно
              сохранить самостоятельно.
            </p>
          </div>
          <Button onClick={() => setFormOpen(true)}>
            <Plus className="h-4 w-4" />
            Новое обращение
          </Button>
        </div>
      </Card>

      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <ListSkeleton />
      ) : appeals.length === 0 ? (
        <Card>
          <EmptyState
            title="Обращений пока нет"
            description="Здесь появятся ваши обращения и ответы психолога."
            icon={<HeartHandshake className="h-6 w-6" />}
            action={
              <Button variant="outline" onClick={() => setFormOpen(true)}>
                <Plus className="h-4 w-4" />
                Создать обращение
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {appeals.map((appeal) => (
            <Card key={appeal.id} className="p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={appealStatusColors[appeal.status]}>
                  {appealStatusLabels[appeal.status]}
                </Badge>
                <Badge className={priorityColors[appeal.priority]}>
                  {priorityLabels[appeal.priority]}
                </Badge>
                <Badge>{appealCategoryLabels[appeal.category]}</Badge>
                {appeal.is_anonymous ? (
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    анонимно
                  </Badge>
                ) : null}
                <span className="ml-auto text-xs text-slate-400">
                  {formatDateTime(appeal.created_at)}
                </span>
              </div>
              <h3 className="mt-3 text-base font-semibold text-slate-900">
                {appeal.subject}
              </h3>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {appeal.message}
              </p>
              {appeal.response ? (
                <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
                    Ответ психолога
                  </p>
                  <p className="mt-1 whitespace-pre-wrap leading-6">
                    {appeal.response}
                  </p>
                  <p className="mt-2 text-xs text-emerald-600">
                    {formatDateTime(appeal.responded_at)}
                  </p>
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-400">
                  Ответа пока нет. Обращение {appealStatusLabels[appeal.status].toLowerCase()}.
                </p>
              )}
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="Новое обращение"
        description="Сообщение увидит только психолог и уполномоченные сотрудники школы."
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Отмена
            </Button>
            <Button onClick={() => void submit()} loading={saving}>
              <Send className="h-4 w-4" />
              Отправить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {formError ? <FormError message={formError} /> : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Категория">
              <select
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    category: event.target.value as SafetyAppealCategory,
                  }))
                }
                className={inputClass}
              >
                {Object.entries(appealCategoryLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Приоритет">
              <select
                value={form.priority}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    priority: event.target.value as SafetyPriority,
                  }))
                }
                className={inputClass}
              >
                {Object.entries(priorityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Тема *">
            <input
              value={form.subject}
              maxLength={255}
              onChange={(event) =>
                setForm((current) => ({ ...current, subject: event.target.value }))
              }
              placeholder="Кратко опишите ситуацию"
              className={inputClass}
            />
          </Field>
          <Field label="Сообщение *" hint="До 4000 символов. Не указывайте лишние персональные данные.">
            <textarea
              value={form.message}
              maxLength={4000}
              onChange={(event) =>
                setForm((current) => ({ ...current, message: event.target.value }))
              }
              placeholder="Что произошло, когда и какая помощь нужна?"
              className={textareaClass}
            />
          </Field>
          <label className="flex cursor-pointer items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.anonymous}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  anonymous: event.target.checked,
                }))
              }
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600"
            />
            <span>
              <span className="font-semibold text-slate-800">Анонимно</span>
              <span className="mt-0.5 block text-xs text-slate-500">
                Имя и учётная запись не сохраняются. Номер обращения нужно
                сохранить после отправки.
              </span>
            </span>
          </label>
          <label className="flex cursor-pointer items-start gap-2 rounded-xl border border-slate-200 p-3 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.consentGiven}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  consentGiven: event.target.checked,
                }))
              }
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600"
            />
            <span>
              <span className="font-semibold text-slate-800">
                Согласен на обработку обращения
              </span>
              <span className="mt-0.5 block text-xs text-slate-500">
                Данные используются только для психологической поддержки и
                хранятся ограниченный срок.
              </span>
            </span>
          </label>
        </div>
      </Modal>
    </div>
  );
}

function SchoolAppealsPanel({ schoolId }: { schoolId?: string }) {
  const [appeals, setAppeals] = useState<SafetyAppeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SafetyAppeal | null>(null);
  const [response, setResponse] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setAppeals(await fetchSafetyAppeals(schoolId));
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [schoolId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  function openRespond(appeal: SafetyAppeal) {
    setSelected(appeal);
    setResponse(appeal.response ?? '');
    setFormError(null);
  }

  async function submitResponse() {
    if (!selected) return;
    if (!response.trim()) {
      setFormError('Введите текст ответа.');
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await respondSafetyAppeal(selected.id, {
        response: response.trim(),
        status: 'responded',
      });
      setSelected(null);
      setResponse('');
      setNotice('Ответ отправлен.');
      await load();
    } catch (caught) {
      setFormError(apiErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  async function closeAppeal(appeal: SafetyAppeal) {
    if (!window.confirm('Закрыть обращение? Действие можно отменить только администратором данных.')) {
      return;
    }
    try {
      await closeSafetyAppeal(appeal.id);
      setNotice('Обращение закрыто.');
      await load();
    } catch (caught) {
      setError(apiErrorMessage(caught));
    }
  }

  return (
    <div className="space-y-4">
      {notice ? <Notice>{notice}</Notice> : null}
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Обращения школы. Анонимные обращения не содержат автора.
        </p>
        <Button variant="outline" size="sm" onClick={() => void load()}>
          <RefreshCw className="h-4 w-4" />
          Обновить
        </Button>
      </div>
      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <ListSkeleton />
      ) : appeals.length === 0 ? (
        <Card>
          <EmptyState
            title="Обращений нет"
            description="Новые обращения появятся здесь."
            icon={<MessageCircle className="h-6 w-6" />}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {appeals.map((appeal) => (
            <Card key={appeal.id} className="p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={appealStatusColors[appeal.status]}>
                  {appealStatusLabels[appeal.status]}
                </Badge>
                <Badge className={priorityColors[appeal.priority]}>
                  {priorityLabels[appeal.priority]}
                </Badge>
                <Badge>{appealCategoryLabels[appeal.category]}</Badge>
                {appeal.is_anonymous ? (
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    анонимно
                  </Badge>
                ) : null}
                <span className="ml-auto text-xs text-slate-400">
                  {formatDateTime(appeal.created_at)}
                </span>
              </div>
              <h3 className="mt-3 text-base font-semibold text-slate-900">
                {appeal.subject}
              </h3>
              <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {appeal.message}
              </p>
              {appeal.response ? (
                <p className="mt-3 whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                  <span className="font-semibold">Ответ: </span>
                  {appeal.response}
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                {appeal.status === 'open' || appeal.status === 'in_progress' ? (
                  <Button size="sm" onClick={() => openRespond(appeal)}>
                    <Send className="h-4 w-4" />
                    Ответить
                  </Button>
                ) : null}
                {appeal.status !== 'closed' ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void closeAppeal(appeal)}
                  >
                    <XCircle className="h-4 w-4" />
                    Закрыть
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="Ответ на обращение"
        description={selected?.subject}
        footer={
          <>
            <Button variant="outline" onClick={() => setSelected(null)}>
              Отмена
            </Button>
            <Button onClick={() => void submitResponse()} loading={saving}>
              <Send className="h-4 w-4" />
              Отправить ответ
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {formError ? <FormError message={formError} /> : null}
          {selected ? (
            <div className="rounded-xl bg-slate-50 p-3 text-sm leading-6 text-slate-600">
              <p className="line-clamp-6 whitespace-pre-wrap">{selected.message}</p>
            </div>
          ) : null}
          <Field label="Ответ *" hint="Ответ увидит автор обращения.">
            <textarea
              value={response}
              maxLength={4000}
              onChange={(event) => setResponse(event.target.value)}
              placeholder="Что сделано, какая помощь предложена, куда обратиться дальше"
              className={textareaClass}
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

function IncidentsPanel({
  schoolId,
  canManage,
}: {
  schoolId?: string;
  canManage: boolean;
}) {
  const [incidents, setIncidents] = useState<SafetyIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [form, setForm] = useState({
    category: 'other' as SafetyIncidentCategory,
    severity: 'medium' as SafetyIncidentSeverity,
    title: '',
    description: '',
  });
  const [selected, setSelected] = useState<SafetyIncident | null>(null);
  const [resolveStatus, setResolveStatus] = useState<'resolved' | 'closed'>('resolved');
  const [actionsTaken, setActionsTaken] = useState('');
  const [resolving, setResolving] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setIncidents(
        await fetchSafetyIncidents(schoolId, {
          status: statusFilter || undefined,
          severity: severityFilter || undefined,
        }),
      );
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [schoolId, statusFilter, severityFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  async function submitCreate() {
    if (!form.title.trim()) {
      setCreateError('Укажите заголовок инцидента.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      await createSafetyIncident({
        school_id: schoolId ?? null,
        category: form.category,
        severity: form.severity,
        title: form.title.trim(),
        description: form.description.trim() || null,
      });
      setCreateOpen(false);
      setForm({
        category: 'other',
        severity: 'medium',
        title: '',
        description: '',
      });
      setNotice('Инцидент зарегистрирован.');
      await load();
    } catch (caught) {
      setCreateError(apiErrorMessage(caught));
    } finally {
      setCreating(false);
    }
  }

  function openResolve(incident: SafetyIncident) {
    setSelected(incident);
    setResolveStatus('resolved');
    setActionsTaken(incident.actions_taken ?? '');
    setResolveError(null);
  }

  async function submitResolve() {
    if (!selected) return;
    setResolving(true);
    setResolveError(null);
    try {
      await resolveSafetyIncident(selected.id, {
        actions_taken: actionsTaken.trim() || null,
        status: resolveStatus,
      });
      setSelected(null);
      setNotice('Инцидент обновлён.');
      await load();
    } catch (caught) {
      setResolveError(apiErrorMessage(caught));
    } finally {
      setResolving(false);
    }
  }

  return (
    <div className="space-y-4">
      {notice ? <Notice>{notice}</Notice> : null}
      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row">
            <Field label="Статус">
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className={inputClass}
              >
                <option value="">Все</option>
                {Object.entries(incidentStatusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Тяжесть">
              <select
                value={severityFilter}
                onChange={(event) => setSeverityFilter(event.target.value)}
                className={inputClass}
              >
                <option value="">Все</option>
                {Object.entries(incidentSeverityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void load()}>
              <RefreshCw className="h-4 w-4" />
              Обновить
            </Button>
            {canManage ? (
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4" />
                Инцидент
              </Button>
            ) : null}
          </div>
        </div>
      </Card>

      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <ListSkeleton />
      ) : incidents.length === 0 ? (
        <Card>
          <EmptyState
            title="Инцидентов нет"
            description="Зарегистрированные случаи появятся здесь."
            icon={<AlertTriangle className="h-6 w-6" />}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {incidents.map((incident) => (
            <Card key={incident.id} className="p-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className={incidentStatusColors[incident.status]}>
                  {incidentStatusLabels[incident.status]}
                </Badge>
                <Badge className={incidentSeverityColors[incident.severity]}>
                  {incidentSeverityLabels[incident.severity]}
                </Badge>
                <Badge>{incidentCategoryLabels[incident.category]}</Badge>
                <span className="ml-auto text-xs text-slate-400">
                  {formatDateTime(incident.created_at)}
                </span>
              </div>
              <h3 className="mt-3 text-base font-semibold text-slate-900">
                {incident.title}
              </h3>
              {incident.description ? (
                <p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                  {incident.description}
                </p>
              ) : null}
              {incident.actions_taken ? (
                <p className="mt-3 whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                  <span className="font-semibold">Принятые меры: </span>
                  {incident.actions_taken}
                </p>
              ) : null}
              {canManage &&
              (incident.status === 'open' || incident.status === 'investigating') ? (
                <Button
                  className="mt-4"
                  size="sm"
                  onClick={() => openResolve(incident)}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Завершить
                </Button>
              ) : null}
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новый инцидент"
        description="Зафиксируйте событие для дальнейшего разбора и мер."
        footer={
          <>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Отмена
            </Button>
            <Button onClick={() => void submitCreate()} loading={creating}>
              <Plus className="h-4 w-4" />
              Зарегистрировать
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {createError ? <FormError message={createError} /> : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Категория">
              <select
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    category: event.target.value as SafetyIncidentCategory,
                  }))
                }
                className={inputClass}
              >
                {Object.entries(incidentCategoryLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Тяжесть">
              <select
                value={form.severity}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    severity: event.target.value as SafetyIncidentSeverity,
                  }))
                }
                className={inputClass}
              >
                {Object.entries(incidentSeverityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Заголовок *">
            <input
              value={form.title}
              maxLength={255}
              onChange={(event) =>
                setForm((current) => ({ ...current, title: event.target.value }))
              }
              placeholder="Краткое описание инцидента"
              className={inputClass}
            />
          </Field>
          <Field label="Описание">
            <textarea
              value={form.description}
              maxLength={4000}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              placeholder="Обстоятельства, участники, что уже сделано"
              className={textareaClass}
            />
          </Field>
        </div>
      </Modal>

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="Завершение инцидента"
        description={selected?.title}
        footer={
          <>
            <Button variant="outline" onClick={() => setSelected(null)}>
              Отмена
            </Button>
            <Button onClick={() => void submitResolve()} loading={resolving}>
              <CheckCircle2 className="h-4 w-4" />
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {resolveError ? <FormError message={resolveError} /> : null}
          <Field label="Статус">
            <select
              value={resolveStatus}
              onChange={(event) =>
                setResolveStatus(event.target.value as 'resolved' | 'closed')
              }
              className={inputClass}
            >
              <option value="resolved">Решён</option>
              <option value="closed">Закрыт</option>
            </select>
          </Field>
          <Field label="Принятые меры" hint="Что сделано для устранения и профилактики.">
            <textarea
              value={actionsTaken}
              maxLength={4000}
              onChange={(event) => setActionsTaken(event.target.value)}
              placeholder="Проведена беседа, уведомлены родители, составлен план…"
              className={textareaClass}
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

function ConsentsPanel({
  schoolId,
  canReadUsers,
}: {
  schoolId?: string;
  canReadUsers: boolean;
}) {
  const [consents, setConsents] = useState<SafetyConsent[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scopeFilter, setScopeFilter] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [form, setForm] = useState({
    studentId: '',
    representativeId: '',
    scope: 'psychological_support' as SafetyConsentScope,
    source: 'electronic' as SafetyConsentSource,
    expiresAt: '',
  });
  const [revokeTarget, setRevokeTarget] = useState<SafetyConsent | null>(null);
  const [revokeReason, setRevokeReason] = useState('');
  const [revoking, setRevoking] = useState(false);
  const [revokeError, setRevokeError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setConsents(
        await fetchSafetyConsents(schoolId, {
          scope: scopeFilter || undefined,
        }),
      );
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [schoolId, scopeFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!canReadUsers || !schoolId) {
      setUsers([]);
      return;
    }
    let cancelled = false;
    fetchUsers(schoolId)
      .then((data) => {
        if (!cancelled) {
          setUsers(data.items);
          setUsersError(null);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setUsers([]);
          setUsersError(apiErrorMessage(caught));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [canReadUsers, schoolId]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const students = useMemo(
    () => users.filter((user) => user.role === 'student'),
    [users],
  );
  const representatives = useMemo(
    () => users.filter((user) => user.role === 'parent'),
    [users],
  );

  function nameFor(userId: string): string {
    const user = users.find((item) => item.id === userId);
    return user ? user.full_name : userId;
  }

  async function submitCreate() {
    if (!form.studentId.trim() || !form.representativeId.trim()) {
      setCreateError('Укажите ученика и законного представителя.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      await createSafetyConsent({
        student_id: form.studentId.trim(),
        legal_representative_id: form.representativeId.trim(),
        scope: form.scope,
        granted: true,
        source: form.source,
        expires_at: form.expiresAt
          ? new Date(`${form.expiresAt}T23:59:59`).toISOString()
          : null,
      });
      setCreateOpen(false);
      setForm({
        studentId: '',
        representativeId: '',
        scope: 'psychological_support',
        source: 'electronic',
        expiresAt: '',
      });
      setNotice('Согласие зарегистрировано.');
      await load();
    } catch (caught) {
      setCreateError(apiErrorMessage(caught));
    } finally {
      setCreating(false);
    }
  }

  async function submitRevoke() {
    if (!revokeTarget) return;
    setRevoking(true);
    setRevokeError(null);
    try {
      await revokeSafetyConsent(revokeTarget.id, revokeReason.trim() || undefined);
      setRevokeTarget(null);
      setRevokeReason('');
      setNotice('Согласие отозвано.');
      await load();
    } catch (caught) {
      setRevokeError(apiErrorMessage(caught));
    } finally {
      setRevoking(false);
    }
  }

  return (
    <div className="space-y-4">
      {notice ? <Notice>{notice}</Notice> : null}
      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <Field label="Вид согласия">
            <select
              value={scopeFilter}
              onChange={(event) => setScopeFilter(event.target.value)}
              className={inputClass}
            >
              <option value="">Все</option>
              {Object.entries(consentScopeLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void load()}>
              <RefreshCw className="h-4 w-4" />
              Обновить
            </Button>
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" />
              Согласие
            </Button>
          </div>
        </div>
      </Card>

      {usersError ? (
        <p className="text-xs text-amber-600">
          Список пользователей недоступен: {usersError}. Идентификаторы можно
          указать вручную.
        </p>
      ) : null}
      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <ListSkeleton />
      ) : consents.length === 0 ? (
        <Card>
          <EmptyState
            title="Согласий нет"
            description="Согласия законных представителей появятся здесь."
            icon={<FileCheck2 className="h-6 w-6" />}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {consents.map((consent) => {
            const expired =
              consent.expires_at !== null &&
              new Date(consent.expires_at).getTime() < Date.now();
            const active = consent.granted && !consent.revoked_at && !expired;
            return (
              <Card key={consent.id} className="p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    className={
                      active
                        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                        : 'bg-slate-100 text-slate-600 ring-slate-200'
                    }
                  >
                    {consent.revoked_at
                      ? 'Отозвано'
                      : expired
                        ? 'Истекло'
                        : !consent.granted
                          ? 'Не выдано'
                          : 'Действует'}
                  </Badge>
                  <Badge>{consentScopeLabels[consent.scope]}</Badge>
                  <Badge>{consentSourceLabels[consent.source]}</Badge>
                  <span className="ml-auto text-xs text-slate-400">
                    {formatDateTime(consent.created_at)}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-700">
                  Ученик: <span className="font-semibold">{nameFor(consent.student_id)}</span>
                </p>
                <p className="mt-1 text-sm text-slate-700">
                  Представитель:{' '}
                  <span className="font-semibold">
                    {nameFor(consent.legal_representative_id)}
                  </span>
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  Выдано: {formatDate(consent.granted_at)} · Действует до:{' '}
                  {formatDate(consent.expires_at)}
                </p>
                {consent.revoked_at ? (
                  <p className="mt-1 text-xs text-rose-500">
                    Отозвано: {formatDateTime(consent.revoked_at)}
                  </p>
                ) : null}
                {active ? (
                  <Button
                    className="mt-4"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setRevokeTarget(consent);
                      setRevokeReason('');
                      setRevokeError(null);
                    }}
                  >
                    <XCircle className="h-4 w-4" />
                    Отозвать
                  </Button>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новое согласие"
        description="Для ребёнка младше порога согласие даёт законный представитель."
        footer={
          <>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Отмена
            </Button>
            <Button onClick={() => void submitCreate()} loading={creating}>
              <Plus className="h-4 w-4" />
              Зарегистрировать
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {createError ? <FormError message={createError} /> : null}
          {students.length > 0 ? (
            <Field label="Ученик *">
              <select
                value={form.studentId}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    studentId: event.target.value,
                  }))
                }
                className={inputClass}
              >
                <option value="">Выберите ученика</option>
                {students.map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.full_name}
                  </option>
                ))}
              </select>
            </Field>
          ) : (
            <Field label="ID ученика *" hint="UUID ученика из контура школы.">
              <input
                value={form.studentId}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    studentId: event.target.value,
                  }))
                }
                placeholder="00000000-0000-0000-0000-000000000000"
                className={`${inputClass} font-mono text-xs`}
              />
            </Field>
          )}
          {representatives.length > 0 ? (
            <Field label="Законный представитель *">
              <select
                value={form.representativeId}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    representativeId: event.target.value,
                  }))
                }
                className={inputClass}
              >
                <option value="">Выберите представителя</option>
                {representatives.map((representative) => (
                  <option key={representative.id} value={representative.id}>
                    {representative.full_name}
                  </option>
                ))}
              </select>
            </Field>
          ) : (
            <Field label="ID законного представителя *" hint="UUID родителя или опекуна.">
              <input
                value={form.representativeId}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    representativeId: event.target.value,
                  }))
                }
                placeholder="00000000-0000-0000-0000-000000000000"
                className={`${inputClass} font-mono text-xs`}
              />
            </Field>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Вид согласия">
              <select
                value={form.scope}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    scope: event.target.value as SafetyConsentScope,
                  }))
                }
                className={inputClass}
              >
                {Object.entries(consentScopeLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Источник">
              <select
                value={form.source}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    source: event.target.value as SafetyConsentSource,
                  }))
                }
                className={inputClass}
              >
                {Object.entries(consentSourceLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Действует до">
            <input
              type="date"
              value={form.expiresAt}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  expiresAt: event.target.value,
                }))
              }
              className={inputClass}
            />
          </Field>
        </div>
      </Modal>

      <Modal
        open={Boolean(revokeTarget)}
        onClose={() => setRevokeTarget(null)}
        title="Отзыв согласия"
        description={
          revokeTarget
            ? `${consentScopeLabels[revokeTarget.scope]} · ${nameFor(revokeTarget.student_id)}`
            : undefined
        }
        footer={
          <>
            <Button variant="outline" onClick={() => setRevokeTarget(null)}>
              Отмена
            </Button>
            <Button variant="danger" onClick={() => void submitRevoke()} loading={revoking}>
              <XCircle className="h-4 w-4" />
              Отозвать
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {revokeError ? <FormError message={revokeError} /> : null}
          <p className="text-sm text-slate-600">
            После отзыва обработка в рамках этого согласия прекращается. Уже
            созданные записи сохраняются в пределах срока хранения.
          </p>
          <Field label="Причина">
            <textarea
              value={revokeReason}
              maxLength={1000}
              onChange={(event) => setRevokeReason(event.target.value)}
              placeholder="Необязательно"
              className={textareaClass}
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}

function GeolocationPanel({ schoolId }: { schoolId?: string }) {
  const [points, setPoints] = useState<SafetyGeolocationPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPoints(await fetchSafetyGeolocation(schoolId));
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [schoolId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500">
            Точки поступают с мобильного устройства при наличии активного
            согласия. Веб-интерфейс показывает последние записи.
          </p>
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4" />
            Обновить
          </Button>
        </div>
      </Card>

      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      {loading ? (
        <ListSkeleton />
      ) : points.length === 0 ? (
        <Card>
          <EmptyState
            title="Точек пока нет"
            description="Геолокация появится после подключения мобильного клиента и согласия представителя."
            icon={<MapPin className="h-6 w-6" />}
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {points.map((point) => (
            <Card key={point.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-sky-50 text-sky-700 ring-sky-200">
                  {geolocationEventLabels[point.event_type]}
                </Badge>
                <span className="text-xs text-slate-400">
                  {formatDateTime(point.recorded_at)}
                </span>
                <span className="ml-auto font-mono text-xs text-slate-400">
                  {point.student_id.slice(0, 8)}…
                </span>
              </div>
              <p className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                <MapPin className="h-4 w-4 text-slate-400" />
                {point.latitude.toFixed(5)}, {point.longitude.toFixed(5)}
                {point.accuracy_m !== null ? (
                  <span className="text-xs text-slate-400">
                    ±{Math.round(point.accuracy_m)} м
                  </span>
                ) : null}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function SettingsPanel({ schoolId }: { schoolId?: string }) {
  const [settings, setSettings] = useState<SafetySettings | null>(null);
  const [form, setForm] = useState<SafetySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeError, setPurgeError] = useState<string | null>(null);
  const [purgeResult, setPurgeResult] = useState<SafetyPurgeResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSafetySettings(schoolId);
      setSettings(data);
      setForm(data);
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [schoolId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  async function save() {
    if (!form) return;
    if (form.retention_days < 1 || form.incident_retention_days < 1) {
      setError('Сроки хранения должны быть не меньше одного дня.');
      return;
    }
    if (form.incident_retention_days < form.retention_days) {
      setError('Срок хранения инцидентов не может быть меньше общего срока.');
      return;
    }
    if (form.consent_age_threshold < 16) {
      setError('Порог согласия не может быть ниже 16 лет.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateSafetySettings(
        {
          retention_days: form.retention_days,
          incident_retention_days: form.incident_retention_days,
          consent_age_threshold: form.consent_age_threshold,
          allow_anonymous_appeals: form.allow_anonymous_appeals,
          geolocation_enabled: form.geolocation_enabled,
        },
        schoolId,
      );
      setSettings(updated);
      setForm(updated);
      setNotice('Настройки сохранены.');
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  async function purge() {
    setPurging(true);
    setPurgeError(null);
    try {
      const result = await purgeSafetyData(schoolId);
      setPurgeResult(result);
      setPurgeOpen(false);
      setNotice('Просроченные данные удалены.');
      await load();
    } catch (caught) {
      setPurgeError(apiErrorMessage(caught));
    } finally {
      setPurging(false);
    }
  }

  if (loading) return <ListSkeleton />;
  if (!form) {
    return <ErrorAlert message={error ?? 'Настройки недоступны'} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-4">
      {notice ? <Notice>{notice}</Notice> : null}
      {error ? <ErrorAlert message={error} onRetry={() => void load()} /> : null}
      <Card className="p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">
              Ограничения безопасности
            </p>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              {schoolId
                ? 'Настройки действуют для выбранной школы.'
                : 'Глобальные настройки по умолчанию. Школа может переопределить их.'}{' '}
              Значения ниже требований законодательства недоступны.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <Field label="Хранение обращений, дней">
            <input
              type="number"
              min={1}
              max={3650}
              value={form.retention_days}
              onChange={(event) =>
                setForm((current) =>
                  current
                    ? { ...current, retention_days: Number(event.target.value) }
                    : current,
                )
              }
              className={inputClass}
            />
          </Field>
          <Field label="Хранение инцидентов, дней">
            <input
              type="number"
              min={1}
              max={3650}
              value={form.incident_retention_days}
              onChange={(event) =>
                setForm((current) =>
                  current
                    ? {
                        ...current,
                        incident_retention_days: Number(event.target.value),
                      }
                    : current,
                )
              }
              className={inputClass}
            />
          </Field>
          <Field label="Порог согласия, лет" hint="Не ниже 16 лет.">
            <input
              type="number"
              min={16}
              max={18}
              value={form.consent_age_threshold}
              onChange={(event) =>
                setForm((current) =>
                  current
                    ? {
                        ...current,
                        consent_age_threshold: Number(event.target.value),
                      }
                    : current,
                )
              }
              className={inputClass}
            />
          </Field>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 p-4">
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Анонимные обращения
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Разрешить обращения без привязки к учётной записи.
              </p>
            </div>
            <Toggle
              checked={form.allow_anonymous_appeals}
              onChange={(next) =>
                setForm((current) =>
                  current
                    ? { ...current, allow_anonymous_appeals: next }
                    : current,
                )
              }
              label="Анонимные обращения"
            />
          </div>
          <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 p-4">
            <div>
              <p className="text-sm font-semibold text-slate-800">Геолокация</p>
              <p className="mt-1 text-xs text-slate-500">
                Принимать точки только при активном согласии.
              </p>
            </div>
            <Toggle
              checked={form.geolocation_enabled}
              onChange={(next) =>
                setForm((current) =>
                  current ? { ...current, geolocation_enabled: next } : current,
                )
              }
              label="Геолокация"
            />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => void save()} loading={saving}>
            <Settings2 className="h-4 w-4" />
            Сохранить настройки
          </Button>
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCw className="h-4 w-4" />
            Сбросить изменения
          </Button>
        </div>
        {settings ? (
          <p className="mt-3 text-xs text-slate-400">
            Текущая конфигурация: обращения {settings.retention_days} дн.,
            инциденты {settings.incident_retention_days} дн., согласие с{' '}
            {settings.consent_age_threshold} лет.
          </p>
        ) : null}
      </Card>

      <Card className="border-rose-200 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-rose-800">
              Очистка просроченных данных
            </p>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Удаляет обращения, инциденты, согласия и точки геолокации старше
              установленных сроков. Действие фиксируется в аудите.
            </p>
          </div>
          <Button
            variant="danger"
            onClick={() => {
              setPurgeError(null);
              setPurgeOpen(true);
            }}
          >
            <XCircle className="h-4 w-4" />
            Очистить
          </Button>
        </div>
        {purgeResult ? (
          <p className="mt-3 text-xs text-slate-500">
            Последняя очистка: обращения {purgeResult.deleted_appeals}, инциденты{' '}
            {purgeResult.deleted_incidents}, согласия {purgeResult.deleted_consents},
            геолокация {purgeResult.deleted_geolocation}.
          </p>
        ) : null}
      </Card>

      <Modal
        open={purgeOpen}
        onClose={() => setPurgeOpen(false)}
        title="Очистить просроченные данные?"
        description="Удаление необратимо. В аудите сохранится только факт и количество удалённых записей."
        footer={
          <>
            <Button variant="outline" onClick={() => setPurgeOpen(false)}>
              Отмена
            </Button>
            <Button variant="danger" onClick={() => void purge()} loading={purging}>
              <XCircle className="h-4 w-4" />
              Удалить
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {purgeError ? <FormError message={purgeError} /> : null}
          <p className="text-sm leading-6 text-slate-600">
            Будут удалены записи старше {form.retention_days} дней для обращений и{' '}
            {form.incident_retention_days} дней для инцидентов. Продолжить?
          </p>
        </div>
      </Modal>
    </div>
  );
}

export function SafetyPage() {
  const { user } = useAuth();
  const { can, services, loading: accessLoading, error: accessError } = useAccess();
  const [activeTab, setActiveTab] = useState<TabKey>('my-appeals');
  const [schools, setSchools] = useState<School[]>([]);
  const [scopeSchoolId, setScopeSchoolId] = useState(user?.school_id ?? '');

  const isSuperadmin = user?.role === 'superadmin';
  const safetyService = services.find((service) => service.code === 'safety');
  const enabled = safetyService?.enabled ?? false;

  useEffect(() => {
    if (!isSuperadmin) return;
    let cancelled = false;
    fetchSchools()
      .then((data) => {
        if (!cancelled) {
          setSchools(data);
          setScopeSchoolId((current) => current || data[0]?.id || '');
        }
      })
      .catch(() => {
        if (!cancelled) setSchools([]);
      });
    return () => {
      cancelled = true;
    };
  }, [isSuperadmin]);

  const canSupport = can('safety.support.use');
  const canManageAppeals = can('safety.incidents.manage');
  const canReadIncidents = can('safety.incidents.read') || canManageAppeals;
  const canManageConsents = can('safety.consents.manage');
  const canReadGeolocation = can('safety.geolocation.read');
  const canManageSettings = can('safety.settings.manage');
  const canReadUsers = can('iam.users.read');

  const tabs = useMemo(
    () =>
      [
        canSupport
          ? {
              key: 'my-appeals' as const,
              label: 'Мои обращения',
              icon: <HeartHandshake className="h-4 w-4" />,
            }
          : null,
        canManageAppeals
          ? {
              key: 'school-appeals' as const,
              label: 'Обращения школы',
              icon: <MessageCircle className="h-4 w-4" />,
            }
          : null,
        canReadIncidents
          ? {
              key: 'incidents' as const,
              label: 'Инциденты',
              icon: <AlertTriangle className="h-4 w-4" />,
            }
          : null,
        canManageConsents
          ? {
              key: 'consents' as const,
              label: 'Согласия',
              icon: <FileCheck2 className="h-4 w-4" />,
            }
          : null,
        canReadGeolocation
          ? {
              key: 'geolocation' as const,
              label: 'Геолокация',
              icon: <MapPin className="h-4 w-4" />,
            }
          : null,
        canManageSettings
          ? {
              key: 'settings' as const,
              label: 'Настройки',
              icon: <Settings2 className="h-4 w-4" />,
            }
          : null,
      ].filter((tab): tab is NonNullable<typeof tab> => tab !== null),
    [
      canManageAppeals,
      canManageConsents,
      canManageSettings,
      canReadGeolocation,
      canReadIncidents,
      canSupport,
    ],
  );

  useEffect(() => {
    if (tabs.length > 0 && !tabs.some((tab) => tab.key === activeTab)) {
      setActiveTab(tabs[0].key);
    }
  }, [activeTab, tabs]);

  const schoolId = isSuperadmin
    ? scopeSchoolId || undefined
    : user?.school_id ?? undefined;
  const needsSchool = activeTab !== 'settings';

  if (accessLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500">
        <RefreshCw className="h-5 w-5 animate-spin" />
        Проверяем доступ к сервису…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Безопасность и психология"
        title="Поддержка и безопасность"
        subtitle="Обращения к психологу, инциденты, согласия и геолокация. Сервис работает только при включённой активации школы."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {isSuperadmin ? (
              <select
                value={scopeSchoolId}
                onChange={(event) => setScopeSchoolId(event.target.value)}
                className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                aria-label="Школа"
              >
                <option value="">Глобальные настройки</option>
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            ) : null}
            <Badge
              className={
                enabled
                  ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                  : 'bg-slate-100 text-slate-500 ring-slate-200'
              }
            >
              <span
                className={cn(
                  'h-1.5 w-1.5 rounded-full',
                  enabled ? 'bg-emerald-500' : 'bg-slate-400',
                )}
              />
              {enabled ? 'сервис включён' : 'сервис отключён'}
            </Badge>
          </div>
        }
      />

      {accessError ? <ErrorAlert message={accessError} /> : null}

      {!safetyService || !enabled ? (
        <Card>
          <EmptyState
            title="Сервис безопасности отключён"
            description="Активация выполняется администратором школы в разделе «Сервисы». API и данные при этом остаются недоступны до включения."
            icon={<ShieldOff className="h-6 w-6" />}
            action={
              can('system.services.read') ? (
                <Link to="/services">
                  <Button variant="outline">
                    <Settings2 className="h-4 w-4" />
                    Открыть сервисы
                  </Button>
                </Link>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  'inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition',
                  activeTab === tab.key
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800',
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {needsSchool && !schoolId ? (
            <SchoolScopeNotice />
          ) : activeTab === 'my-appeals' ? (
            <MyAppealsPanel schoolId={schoolId} />
          ) : activeTab === 'school-appeals' ? (
            <SchoolAppealsPanel schoolId={schoolId} />
          ) : activeTab === 'incidents' ? (
            <IncidentsPanel schoolId={schoolId} canManage={canManageAppeals} />
          ) : activeTab === 'consents' ? (
            <ConsentsPanel schoolId={schoolId} canReadUsers={canReadUsers} />
          ) : activeTab === 'geolocation' ? (
            <GeolocationPanel schoolId={schoolId} />
          ) : (
            <SettingsPanel schoolId={schoolId} />
          )}
        </>
      )}
    </div>
  );
}
