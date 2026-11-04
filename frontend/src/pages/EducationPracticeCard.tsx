import { useEffect, useMemo, useState } from 'react';
import {
  Award,
  Building2,
  CalendarDays,
  Check,
  ClipboardList,
  FileText,
  Pencil,
  Plus,
  RefreshCw,
  X,
} from 'lucide-react';

import {
  apiErrorMessage,
  assessPracticePlacement,
  createPracticeContract,
  createPracticeDiaryEntry,
  createPracticePlace,
  createPracticePlacement,
  fetchPracticeContracts,
  fetchPracticeDiary,
  fetchPracticePlaces,
  fetchPracticePlacements,
  updatePracticeContract,
  updatePracticeDiaryEntry,
  updatePracticePlace,
  updatePracticePlacement,
} from '../api/client';
import type {
  CurriculumComponent,
  EducationCurriculum,
  EducationGroup,
  EducationLevel,
  PracticeContract,
  PracticeContractStatus,
  PracticeDiaryEntry,
  PracticeDiaryStatus,
  PracticePlace,
  PracticePlacement,
  PracticePlacementStatus,
  PracticeResult,
  StaffAcademicProfile,
  StudentAcademicProfile,
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

const CONTRACT_STATUS_LABELS: Record<PracticeContractStatus, string> = {
  draft: 'Черновик',
  signed: 'Подписан',
  active: 'Действует',
  completed: 'Завершён',
  terminated: 'Расторгнут',
  archived: 'Архив',
};

const PLACEMENT_STATUS_LABELS: Record<PracticePlacementStatus, string> = {
  planned: 'Запланирована',
  active: 'Идёт',
  completed: 'Завершена',
  failed: 'Не сдана',
  cancelled: 'Отменена',
  archived: 'Архив',
};

const RESULT_LABELS: Record<PracticeResult, string> = {
  not_assessed: 'Не оценена',
  passed: 'Зачтена',
  failed: 'Не зачтена',
  exempt: 'Освобождён',
};

const DIARY_STATUS_LABELS: Record<PracticeDiaryStatus, string> = {
  draft: 'Черновик',
  submitted: 'На проверке',
  approved: 'Утверждена',
  rejected: 'Отклонена',
};

type PracticeComponent = CurriculumComponent & {
  curriculum_id: string;
  curriculum_name: string;
  program_id: string;
  program_name: string;
};

type PlaceForm = {
  code: string;
  name: string;
  industry: string;
  address: string;
  contact_person: string;
  contact_phone: string;
  contact_email: string;
  is_active: boolean;
};

type ContractForm = {
  practice_place_id: string;
  component_id: string;
  contract_number: string;
  academic_year: string;
  starts_on: string;
  ends_on: string;
  signed_on: string;
  status: PracticeContractStatus;
  document_number: string;
  notes: string;
};

type PlacementForm = {
  contract_id: string;
  student_id: string;
  group_id: string;
  component_id: string;
  supervisor_id: string;
  enterprise_supervisor: string;
  starts_on: string;
  ends_on: string;
  total_hours: string;
  status: PracticePlacementStatus;
  notes: string;
};

type DiaryForm = {
  entry_date: string;
  hours: string;
  activity: string;
  outcome: string;
  supervisor_comment: string;
  status: PracticeDiaryStatus;
};

const EMPTY_PLACE: PlaceForm = {
  code: '',
  name: '',
  industry: '',
  address: '',
  contact_person: '',
  contact_phone: '',
  contact_email: '',
  is_active: true,
};

function errorText(reason: unknown): string {
  return apiErrorMessage(reason);
}

function currentAcademicYear(): string {
  const now = new Date();
  const start = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
  return `${start}/${start + 1}`;
}

function academicStart(year: string | undefined): number {
  const value = year || currentAcademicYear();
  const start = Number(value.split('/')[0]);
  return Number.isFinite(start) ? start : new Date().getFullYear();
}

function contractDefaults(year: string | undefined) {
  const start = academicStart(year);
  return {
    starts_on: `${start + 1}-02-01`,
    ends_on: `${start + 1}-05-01`,
  };
}

function emptyContract(year: string | undefined): ContractForm {
  const dates = contractDefaults(year);
  return {
    practice_place_id: '',
    component_id: '',
    contract_number: '',
    academic_year: year || currentAcademicYear(),
    starts_on: dates.starts_on,
    ends_on: dates.ends_on,
    signed_on: '',
    status: 'draft',
    document_number: '',
    notes: '',
  };
}

function emptyPlacement(year: string | undefined): PlacementForm {
  const dates = contractDefaults(year);
  return {
    contract_id: '',
    student_id: '',
    group_id: '',
    component_id: '',
    supervisor_id: '',
    enterprise_supervisor: '',
    starts_on: dates.starts_on,
    ends_on: dates.ends_on,
    total_hours: '0',
    status: 'planned',
    notes: '',
  };
}

function emptyDiary(date: string): DiaryForm {
  return {
    entry_date: date,
    hours: '6',
    activity: '',
    outcome: '',
    supervisor_comment: '',
    status: 'draft',
  };
}

function numberText(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function EducationPracticeCard({
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
  const [places, setPlaces] = useState<PracticePlace[]>([]);
  const [contracts, setContracts] = useState<PracticeContract[]>([]);
  const [placements, setPlacements] = useState<PracticePlacement[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [selectedPlacementId, setSelectedPlacementId] = useState('');
  const [diary, setDiary] = useState<PracticeDiaryEntry[]>([]);
  const [diaryLoading, setDiaryLoading] = useState(false);
  const [diaryError, setDiaryError] = useState('');

  const [placeModalOpen, setPlaceModalOpen] = useState(false);
  const [editingPlace, setEditingPlace] = useState<PracticePlace | null>(null);
  const [placeForm, setPlaceForm] = useState<PlaceForm>(EMPTY_PLACE);
  const [placeSaving, setPlaceSaving] = useState(false);
  const [placeFormError, setPlaceFormError] = useState('');

  const [contractModalOpen, setContractModalOpen] = useState(false);
  const [editingContract, setEditingContract] =
    useState<PracticeContract | null>(null);
  const [contractForm, setContractForm] = useState<ContractForm>(
    emptyContract(academicYear),
  );
  const [contractSaving, setContractSaving] = useState(false);
  const [contractFormError, setContractFormError] = useState('');

  const [placementModalOpen, setPlacementModalOpen] = useState(false);
  const [editingPlacement, setEditingPlacement] =
    useState<PracticePlacement | null>(null);
  const [placementForm, setPlacementForm] = useState<PlacementForm>(
    emptyPlacement(academicYear),
  );
  const [placementSaving, setPlacementSaving] = useState(false);
  const [placementFormError, setPlacementFormError] = useState('');

  const [diaryModalOpen, setDiaryModalOpen] = useState(false);
  const [editingDiary, setEditingDiary] = useState<PracticeDiaryEntry | null>(
    null,
  );
  const [diaryForm, setDiaryForm] = useState<DiaryForm>(
    emptyDiary(new Date().toISOString().slice(0, 10)),
  );
  const [diarySaving, setDiarySaving] = useState(false);
  const [diaryFormError, setDiaryFormError] = useState('');

  const [assessmentResult, setAssessmentResult] =
    useState<PracticeResult>('not_assessed');
  const [assessmentGrade, setAssessmentGrade] = useState('');
  const [assessmentSaving, setAssessmentSaving] = useState(false);
  const [assessmentError, setAssessmentError] = useState('');

  const practiceComponents = useMemo<PracticeComponent[]>(
    () =>
      curricula.flatMap((curriculum) =>
        curriculum.components
          .filter((component) =>
            ['practice', 'internship'].includes(component.component_type),
          )
          .map((component) => ({
            ...component,
            curriculum_id: curriculum.id,
            curriculum_name: curriculum.name,
            program_id: curriculum.program_id,
            program_name: curriculum.program_name,
          })),
      ),
    [curricula],
  );

  const selectedPlacement = useMemo(
    () => placements.find((item) => item.id === selectedPlacementId) ?? null,
    [placements, selectedPlacementId],
  );

  async function loadAll() {
    if (!schoolId) return;
    setLoading(true);
    setError('');
    try {
      const [placeRows, contractRows, placementRows] = await Promise.all([
        fetchPracticePlaces(level, schoolId),
        fetchPracticeContracts(level, schoolId),
        fetchPracticePlacements(level, schoolId),
      ]);
      setPlaces(placeRows);
      setContracts(contractRows);
      setPlacements(placementRows);
      setSelectedPlacementId((current) => {
        if (current && placementRows.some((item) => item.id === current)) {
          return current;
        }
        return placementRows[0]?.id ?? '';
      });
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  }

  async function loadDiary(placementId: string) {
    if (!placementId) {
      setDiary([]);
      return;
    }
    setDiaryLoading(true);
    setDiaryError('');
    try {
      setDiary(await fetchPracticeDiary(level, schoolId, placementId));
    } catch (reason) {
      setDiaryError(errorText(reason));
      setDiary([]);
    } finally {
      setDiaryLoading(false);
    }
  }

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level, schoolId]);

  useEffect(() => {
    void loadDiary(selectedPlacementId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPlacementId, level, schoolId]);

  useEffect(() => {
    if (!selectedPlacement) return;
    setAssessmentResult(selectedPlacement.result);
    setAssessmentGrade(
      selectedPlacement.grade === null ? '' : String(selectedPlacement.grade),
    );
    setAssessmentError('');
  }, [selectedPlacement]);

  function openCreatePlace() {
    setEditingPlace(null);
    setPlaceForm(EMPTY_PLACE);
    setPlaceFormError('');
    setPlaceModalOpen(true);
  }

  function openEditPlace(item: PracticePlace) {
    setEditingPlace(item);
    setPlaceForm({
      code: item.code,
      name: item.name,
      industry: item.industry ?? '',
      address: item.address ?? '',
      contact_person: item.contact_person ?? '',
      contact_phone: item.contact_phone ?? '',
      contact_email: item.contact_email ?? '',
      is_active: item.is_active,
    });
    setPlaceFormError('');
    setPlaceModalOpen(true);
  }

  async function savePlace() {
    setPlaceSaving(true);
    setPlaceFormError('');
    try {
      const payload = {
        code: placeForm.code.trim(),
        name: placeForm.name.trim(),
        industry: placeForm.industry.trim() || null,
        address: placeForm.address.trim() || null,
        contact_person: placeForm.contact_person.trim() || null,
        contact_phone: placeForm.contact_phone.trim() || null,
        contact_email: placeForm.contact_email.trim() || null,
        is_active: placeForm.is_active,
      };
      if (editingPlace) {
        await updatePracticePlace(level, schoolId, editingPlace.id, payload);
      } else {
        await createPracticePlace(level, schoolId, payload);
      }
      setPlaceModalOpen(false);
      await loadAll();
      onDataChanged();
    } catch (reason) {
      setPlaceFormError(errorText(reason));
    } finally {
      setPlaceSaving(false);
    }
  }

  function openCreateContract() {
    setEditingContract(null);
    const next = emptyContract(academicYear);
    setContractForm({
      ...next,
      practice_place_id: places[0]?.id ?? '',
      component_id: practiceComponents[0]?.id ?? '',
    });
    setContractFormError('');
    setContractModalOpen(true);
  }

  function openEditContract(item: PracticeContract) {
    setEditingContract(item);
    setContractForm({
      practice_place_id: item.practice_place_id,
      component_id: item.component_id ?? '',
      contract_number: item.contract_number,
      academic_year: item.academic_year,
      starts_on: item.starts_on,
      ends_on: item.ends_on,
      signed_on: item.signed_on ?? '',
      status: item.status,
      document_number: item.document_number ?? '',
      notes: item.notes ?? '',
    });
    setContractFormError('');
    setContractModalOpen(true);
  }

  async function saveContract() {
    setContractSaving(true);
    setContractFormError('');
    try {
      const component = practiceComponents.find(
        (item) => item.id === contractForm.component_id,
      );
      const payload = {
        practice_place_id: contractForm.practice_place_id,
        component_id: contractForm.component_id || null,
        program_id: component?.program_id ?? null,
        contract_number: contractForm.contract_number.trim(),
        academic_year: contractForm.academic_year,
        starts_on: contractForm.starts_on,
        ends_on: contractForm.ends_on,
        signed_on: contractForm.signed_on || null,
        status: contractForm.status,
        document_number: contractForm.document_number.trim() || null,
        notes: contractForm.notes.trim() || null,
      };
      if (editingContract) {
        await updatePracticeContract(
          level,
          schoolId,
          editingContract.id,
          payload,
        );
      } else {
        await createPracticeContract(level, schoolId, payload);
      }
      setContractModalOpen(false);
      await loadAll();
      onDataChanged();
    } catch (reason) {
      setContractFormError(errorText(reason));
    } finally {
      setContractSaving(false);
    }
  }

  function applyContractToPlacement(contractId: string) {
    const contract = contracts.find((item) => item.id === contractId);
    if (!contract) {
      setPlacementForm((current) => ({
        ...current,
        contract_id: contractId,
      }));
      return;
    }
    const component = practiceComponents.find(
      (item) => item.id === contract.component_id,
    );
    setPlacementForm((current) => ({
      ...current,
      contract_id: contractId,
      component_id: contract.component_id ?? '',
      starts_on: contract.starts_on,
      ends_on: contract.ends_on,
      total_hours: component ? String(component.academic_hours) : '0',
      enterprise_supervisor:
        places.find((item) => item.id === contract.practice_place_id)
          ?.contact_person ?? current.enterprise_supervisor,
    }));
  }

  function openCreatePlacement() {
    setEditingPlacement(null);
    const next = emptyPlacement(academicYear);
    const firstContract = contracts[0];
    const firstProfile = profiles[0];
    setPlacementForm({
      ...next,
      contract_id: firstContract?.id ?? '',
      student_id: firstProfile?.user_id ?? '',
      group_id: firstProfile?.group_id ?? '',
      component_id: firstContract?.component_id ?? '',
      starts_on: firstContract?.starts_on ?? next.starts_on,
      ends_on: firstContract?.ends_on ?? next.ends_on,
      total_hours: (() => {
        const component = practiceComponents.find(
          (item) => item.id === firstContract?.component_id,
        );
        return component ? String(component.academic_hours) : '0';
      })(),
    });
    setPlacementFormError('');
    setPlacementModalOpen(true);
  }

  function openEditPlacement(item: PracticePlacement) {
    setEditingPlacement(item);
    setPlacementForm({
      contract_id: item.contract_id,
      student_id: item.student_id,
      group_id: item.group_id ?? '',
      component_id: item.component_id ?? '',
      supervisor_id: item.supervisor_id ?? '',
      enterprise_supervisor: item.enterprise_supervisor ?? '',
      starts_on: item.starts_on,
      ends_on: item.ends_on,
      total_hours: String(item.total_hours),
      status: item.status,
      notes: item.notes ?? '',
    });
    setPlacementFormError('');
    setPlacementModalOpen(true);
  }

  async function savePlacement() {
    setPlacementSaving(true);
    setPlacementFormError('');
    try {
      const payload = {
        group_id: placementForm.group_id || null,
        component_id: placementForm.component_id || null,
        supervisor_id: placementForm.supervisor_id || null,
        enterprise_supervisor:
          placementForm.enterprise_supervisor.trim() || null,
        starts_on: placementForm.starts_on,
        ends_on: placementForm.ends_on,
        total_hours: Number(placementForm.total_hours || 0),
        status: placementForm.status,
        notes: placementForm.notes.trim() || null,
      };
      if (editingPlacement) {
        await updatePracticePlacement(
          level,
          schoolId,
          editingPlacement.id,
          payload,
        );
      } else {
        await createPracticePlacement(level, schoolId, {
          ...payload,
          contract_id: placementForm.contract_id,
          student_id: placementForm.student_id,
        });
      }
      setPlacementModalOpen(false);
      await loadAll();
      onDataChanged();
    } catch (reason) {
      setPlacementFormError(errorText(reason));
    } finally {
      setPlacementSaving(false);
    }
  }

  function openCreateDiary() {
    if (!selectedPlacement) return;
    setEditingDiary(null);
    setDiaryForm(emptyDiary(selectedPlacement.starts_on));
    setDiaryFormError('');
    setDiaryModalOpen(true);
  }

  function openEditDiary(item: PracticeDiaryEntry) {
    setEditingDiary(item);
    setDiaryForm({
      entry_date: item.entry_date,
      hours: String(item.hours),
      activity: item.activity,
      outcome: item.outcome ?? '',
      supervisor_comment: item.supervisor_comment ?? '',
      status: item.status,
    });
    setDiaryFormError('');
    setDiaryModalOpen(true);
  }

  async function saveDiary() {
    if (!selectedPlacement) return;
    setDiarySaving(true);
    setDiaryFormError('');
    try {
      const payload = {
        entry_date: diaryForm.entry_date,
        hours: Number(diaryForm.hours || 0),
        activity: diaryForm.activity.trim(),
        outcome: diaryForm.outcome.trim() || null,
        supervisor_comment: diaryForm.supervisor_comment.trim() || null,
        status: diaryForm.status,
      };
      if (editingDiary) {
        await updatePracticeDiaryEntry(
          level,
          schoolId,
          editingDiary.id,
          payload,
        );
      } else {
        await createPracticeDiaryEntry(
          level,
          schoolId,
          selectedPlacement.id,
          payload,
        );
      }
      setDiaryModalOpen(false);
      await loadAll();
      await loadDiary(selectedPlacement.id);
      onDataChanged();
    } catch (reason) {
      setDiaryFormError(errorText(reason));
    } finally {
      setDiarySaving(false);
    }
  }

  async function decideDiary(item: PracticeDiaryEntry, status: PracticeDiaryStatus) {
    setDiaryError('');
    try {
      await updatePracticeDiaryEntry(level, schoolId, item.id, { status });
      await loadAll();
      await loadDiary(item.placement_id);
      onDataChanged();
    } catch (reason) {
      setDiaryError(errorText(reason));
    }
  }

  async function saveAssessment() {
    if (!selectedPlacement) return;
    setAssessmentSaving(true);
    setAssessmentError('');
    try {
      await assessPracticePlacement(level, schoolId, selectedPlacement.id, {
        result: assessmentResult,
        grade:
          assessmentResult === 'not_assessed' || assessmentGrade === ''
            ? null
            : Number(assessmentGrade),
      });
      await loadAll();
      await loadDiary(selectedPlacement.id);
      onDataChanged();
    } catch (reason) {
      setAssessmentError(errorText(reason));
    } finally {
      setAssessmentSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Практика и договоры с предприятиями
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Партнёрские организации, договоры, распределение обучающихся,
              дневники практики и итоговая оценка.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadAll()}
            loading={loading}
          >
            <RefreshCw className="h-4 w-4" />
            Обновить
          </Button>
        </div>
        {error ? (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {error}
          </div>
        ) : null}
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Предприятия
            </p>
            <p className="mt-0.5 text-lg font-semibold text-slate-800">
              {places.length}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Договоры
            </p>
            <p className="mt-0.5 text-lg font-semibold text-slate-800">
              {contracts.length}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Практиканты
            </p>
            <p className="mt-0.5 text-lg font-semibold text-slate-800">
              {placements.length}
            </p>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Оценено
            </p>
            <p className="mt-0.5 text-lg font-semibold text-slate-800">
              {
                placements.filter(
                  (item) => item.result !== 'not_assessed',
                ).length
              }
            </p>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Предприятия и организации
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Синтетические и реальные партнёры учреждения для прохождения
              практики.
            </p>
          </div>
          {canManage ? (
            <Button size="sm" onClick={openCreatePlace}>
              <Plus className="h-4 w-4" />
              Предприятие
            </Button>
          ) : null}
        </div>
        {loading ? (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        ) : places.length === 0 ? (
          <EmptyState
            title="Предприятий пока нет"
            description="Добавьте организацию, с которой учреждение заключает договор о практике."
            icon={<Building2 className="h-6 w-6" />}
          />
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {places.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-slate-100 px-3 py-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {item.name}
                      </p>
                      <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                        {item.code}
                      </Badge>
                      <Badge
                        className={
                          item.is_active
                            ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                            : 'bg-rose-50 text-rose-700 ring-rose-200'
                        }
                      >
                        {item.is_active ? 'Активно' : 'Неактивно'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {item.industry ?? 'Отрасль не указана'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {item.address ?? 'Адрес не указан'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {item.contact_person ?? 'Контактное лицо не указано'}
                      {item.contact_phone ? ` · ${item.contact_phone}` : ''}
                      {item.contact_email ? ` · ${item.contact_email}` : ''}
                    </p>
                  </div>
                  {canManage ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditPlace(item)}
                      aria-label="Изменить предприятие"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Договоры с предприятиями
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Договор связывает предприятие, образовательную программу и
              компонент учебного плана.
            </p>
          </div>
          {canManage ? (
            <Button
              size="sm"
              onClick={openCreateContract}
              disabled={!places.length || !practiceComponents.length}
            >
              <Plus className="h-4 w-4" />
              Договор
            </Button>
          ) : null}
        </div>
        {contracts.length === 0 ? (
          <EmptyState
            title="Договоров пока нет"
            description="Создайте договор после добавления предприятия и практики в учебный план."
            icon={<FileText className="h-6 w-6" />}
          />
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2 font-semibold">Договор</th>
                  <th className="px-2 py-2 font-semibold">Предприятие</th>
                  <th className="px-2 py-2 font-semibold">Программа</th>
                  <th className="px-2 py-2 font-semibold">Период</th>
                  <th className="px-2 py-2 font-semibold">Статус</th>
                  <th className="px-2 py-2 text-right font-semibold">
                    Практиканты
                  </th>
                  {canManage ? (
                    <th className="px-2 py-2 text-right font-semibold"> </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {contracts.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-slate-50 last:border-0"
                  >
                    <td className="px-2 py-2.5">
                      <p className="font-semibold text-slate-800">
                        № {item.contract_number}
                      </p>
                      <p className="text-xs text-slate-500">
                        {item.academic_year}
                        {item.document_number
                          ? ` · ${item.document_number}`
                          : ''}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      {item.place_name}
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      <p>{item.program_name ?? '—'}</p>
                      <p className="text-xs text-slate-500">
                        {item.component_name ?? 'Без компонента'}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      {formatDate(item.starts_on)} —{' '}
                      {formatDate(item.ends_on)}
                    </td>
                    <td className="px-2 py-2.5">
                      <Badge
                        className={
                          item.status === 'active'
                            ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                            : item.status === 'draft'
                              ? 'bg-amber-50 text-amber-700 ring-amber-200'
                              : 'bg-slate-100 text-slate-600 ring-slate-200'
                        }
                      >
                        {CONTRACT_STATUS_LABELS[item.status]}
                      </Badge>
                    </td>
                    <td className="px-2 py-2.5 text-right text-slate-600">
                      {item.placements_count}
                    </td>
                    {canManage ? (
                      <td className="px-2 py-2.5 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditContract(item)}
                          aria-label="Изменить договор"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
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
              Практиканты
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Распределение обучающихся по договорам, руководители и часы
              практики.
            </p>
          </div>
          {canManage ? (
            <Button
              size="sm"
              onClick={openCreatePlacement}
              disabled={!contracts.length || !profiles.length}
            >
              <Plus className="h-4 w-4" />
              Практикант
            </Button>
          ) : null}
        </div>
        {placements.length === 0 ? (
          <EmptyState
            title="Практикантов пока нет"
            description="Назначьте обучающегося на практику по действующему договору."
            icon={<ClipboardList className="h-6 w-6" />}
          />
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                  <th className="px-2 py-2 font-semibold">Обучающийся</th>
                  <th className="px-2 py-2 font-semibold">Договор</th>
                  <th className="px-2 py-2 font-semibold">Практика</th>
                  <th className="px-2 py-2 font-semibold">Период</th>
                  <th className="px-2 py-2 text-right font-semibold">Часы</th>
                  <th className="px-2 py-2 font-semibold">Статус</th>
                  <th className="px-2 py-2 font-semibold">Итог</th>
                  {canManage ? (
                    <th className="px-2 py-2 text-right font-semibold"> </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {placements.map((item) => (
                  <tr
                    key={item.id}
                    className={
                      item.id === selectedPlacementId
                        ? 'border-b border-brand-100 bg-brand-50/40'
                        : 'border-b border-slate-50 last:border-0'
                    }
                  >
                    <td className="px-2 py-2.5">
                      <button
                        type="button"
                        className="text-left"
                        onClick={() => setSelectedPlacementId(item.id)}
                      >
                        <p className="font-semibold text-slate-800">
                          {item.student_name}
                        </p>
                        <p className="text-xs text-slate-500">
                          {item.student_login}
                          {item.group_name ? ` · ${item.group_name}` : ''}
                        </p>
                      </button>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      <p>№ {item.contract_number}</p>
                      <p className="text-xs text-slate-500">
                        {item.place_name}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      <p>{item.component_name ?? 'Без компонента'}</p>
                      <p className="text-xs text-slate-500">
                        {item.supervisor_name ?? 'Руководитель не назначен'}
                      </p>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      {formatDate(item.starts_on)} —{' '}
                      {formatDate(item.ends_on)}
                    </td>
                    <td className="px-2 py-2.5 text-right text-slate-600">
                      {numberText(item.completed_hours)} / {item.total_hours}
                    </td>
                    <td className="px-2 py-2.5">
                      <Badge
                        className={
                          item.status === 'completed'
                            ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                            : item.status === 'active'
                              ? 'bg-sky-50 text-sky-700 ring-sky-200'
                              : 'bg-slate-100 text-slate-600 ring-slate-200'
                        }
                      >
                        {PLACEMENT_STATUS_LABELS[item.status]}
                      </Badge>
                    </td>
                    <td className="px-2 py-2.5 text-slate-600">
                      {RESULT_LABELS[item.result]}
                      {item.grade ? ` · ${item.grade}` : ''}
                    </td>
                    {canManage ? (
                      <td className="px-2 py-2.5 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditPlacement(item)}
                          aria-label="Изменить практику"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selectedPlacement ? (
        <Card className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Дневник практики
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {selectedPlacement.student_name} ·{' '}
                {selectedPlacement.place_name} ·{' '}
                {selectedPlacement.component_name ?? 'без компонента'}
              </p>
            </div>
            {canManage ? (
              <Button
                size="sm"
                onClick={openCreateDiary}
                disabled={selectedPlacement.status === 'completed'}
              >
                <Plus className="h-4 w-4" />
                Запись
              </Button>
            ) : null}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Период
              </p>
              <p className="mt-0.5 flex items-center gap-1 text-sm font-semibold text-slate-800">
                <CalendarDays className="h-4 w-4 text-slate-400" />
                {formatDate(selectedPlacement.starts_on)} —{' '}
                {formatDate(selectedPlacement.ends_on)}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Руководитель
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                {selectedPlacement.supervisor_name ?? '—'}
              </p>
              <p className="text-xs text-slate-500">
                {selectedPlacement.enterprise_supervisor ?? 'Наставник не указан'}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Часы
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                {numberText(selectedPlacement.completed_hours)} из{' '}
                {selectedPlacement.total_hours}
              </p>
              <p className="text-xs text-slate-500">
                {pluralize(
                  diary.length,
                  'запись',
                  'записи',
                  'записей',
                )}
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Итог
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                {RESULT_LABELS[selectedPlacement.result]}
                {selectedPlacement.grade
                  ? ` · ${selectedPlacement.grade}`
                  : ''}
              </p>
              <p className="text-xs text-slate-500">
                {PLACEMENT_STATUS_LABELS[selectedPlacement.status]}
              </p>
            </div>
          </div>

          {canManage ? (
            <div className="mt-4 rounded-xl border border-slate-100 px-3 py-3">
              <div className="flex flex-wrap items-end gap-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                    Результат практики
                  </span>
                  <select
                    value={assessmentResult}
                    onChange={(event) =>
                      setAssessmentResult(event.target.value as PracticeResult)
                    }
                    className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                  >
                    {(Object.keys(RESULT_LABELS) as PracticeResult[]).map(
                      (value) => (
                        <option key={value} value={value}>
                          {RESULT_LABELS[value]}
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                    Оценка
                  </span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={assessmentGrade}
                    onChange={(event) =>
                      setAssessmentGrade(event.target.value)
                    }
                    className="h-9 w-24 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                  />
                </label>
                <Button
                  size="sm"
                  onClick={() => void saveAssessment()}
                  loading={assessmentSaving}
                  disabled={
                    assessmentResult === 'not_assessed' && assessmentGrade !== ''
                  }
                >
                  <Award className="h-4 w-4" />
                  Сохранить оценку
                </Button>
              </div>
              {assessmentError ? (
                <p className="mt-2 text-xs text-rose-600">{assessmentError}</p>
              ) : null}
            </div>
          ) : null}

          {diaryError ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              {diaryError}
            </div>
          ) : null}

          {diaryLoading ? (
            <div className="mt-4 space-y-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : diary.length === 0 ? (
            <EmptyState
              title="Дневник пока пуст"
              description="Добавьте первую запись о выполнении задания на предприятии."
              icon={<ClipboardList className="h-6 w-6" />}
            />
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                    <th className="px-2 py-2 font-semibold">Дата</th>
                    <th className="px-2 py-2 text-right font-semibold">Часы</th>
                    <th className="px-2 py-2 font-semibold">Содержание</th>
                    <th className="px-2 py-2 font-semibold">Статус</th>
                    {canManage ? (
                      <th className="px-2 py-2 text-right font-semibold"> </th>
                    ) : null}
                  </tr>
                </thead>
                <tbody>
                  {diary.map((item) => (
                    <tr
                      key={item.id}
                      className="border-b border-slate-50 last:border-0"
                    >
                      <td className="px-2 py-2.5 text-slate-600">
                        {formatDate(item.entry_date)}
                      </td>
                      <td className="px-2 py-2.5 text-right text-slate-600">
                        {numberText(item.hours)}
                      </td>
                      <td className="px-2 py-2.5 text-slate-600">
                        <p className="font-medium text-slate-800">
                          {item.activity}
                        </p>
                        {item.outcome ? (
                          <p className="text-xs text-slate-500">
                            {item.outcome}
                          </p>
                        ) : null}
                        {item.supervisor_comment ? (
                          <p className="text-xs text-slate-500">
                            Комментарий: {item.supervisor_comment}
                          </p>
                        ) : null}
                      </td>
                      <td className="px-2 py-2.5">
                        <Badge
                          className={
                            item.status === 'approved'
                              ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                              : item.status === 'rejected'
                                ? 'bg-rose-50 text-rose-700 ring-rose-200'
                                : item.status === 'submitted'
                                  ? 'bg-amber-50 text-amber-700 ring-amber-200'
                                  : 'bg-slate-100 text-slate-600 ring-slate-200'
                          }
                        >
                          {DIARY_STATUS_LABELS[item.status]}
                        </Badge>
                      </td>
                      {canManage ? (
                        <td className="px-2 py-2.5 text-right">
                          <div className="flex justify-end gap-1">
                            {item.status !== 'approved' ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  void decideDiary(item, 'approved')
                                }
                                aria-label="Утвердить запись"
                              >
                                <Check className="h-4 w-4 text-emerald-600" />
                              </Button>
                            ) : null}
                            {item.status !== 'rejected' ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  void decideDiary(item, 'rejected')
                                }
                                aria-label="Отклонить запись"
                              >
                                <X className="h-4 w-4 text-rose-500" />
                              </Button>
                            ) : null}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEditDiary(item)}
                              aria-label="Изменить запись"
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      ) : (
        <Card className="p-5">
          <EmptyState
            title="Выберите практиканта"
            description="Нажмите на обучающегося в таблице, чтобы открыть дневник и оценку практики."
            icon={<ClipboardList className="h-6 w-6" />}
          />
        </Card>
      )}

      <Modal
        open={placeModalOpen}
        onClose={() => setPlaceModalOpen(false)}
        title={editingPlace ? 'Изменить предприятие' : 'Новое предприятие'}
        description="Организация, которая принимает обучающихся на практику."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setPlaceModalOpen(false)}
              disabled={placeSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void savePlace()}
              loading={placeSaving}
              disabled={!placeForm.code.trim() || !placeForm.name.trim()}
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {placeFormError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {placeFormError}
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Код
              </span>
              <input
                value={placeForm.code}
                onChange={(event) =>
                  setPlaceForm({ ...placeForm, code: event.target.value })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Название
              </span>
              <input
                value={placeForm.name}
                onChange={(event) =>
                  setPlaceForm({ ...placeForm, name: event.target.value })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Отрасль
              </span>
              <input
                value={placeForm.industry}
                onChange={(event) =>
                  setPlaceForm({ ...placeForm, industry: event.target.value })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Адрес
              </span>
              <input
                value={placeForm.address}
                onChange={(event) =>
                  setPlaceForm({ ...placeForm, address: event.target.value })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Контактное лицо
              </span>
              <input
                value={placeForm.contact_person}
                onChange={(event) =>
                  setPlaceForm({
                    ...placeForm,
                    contact_person: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Телефон
              </span>
              <input
                value={placeForm.contact_phone}
                onChange={(event) =>
                  setPlaceForm({
                    ...placeForm,
                    contact_phone: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Электронная почта
              </span>
              <input
                type="email"
                value={placeForm.contact_email}
                onChange={(event) =>
                  setPlaceForm({
                    ...placeForm,
                    contact_email: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
        </div>
      </Modal>

      <Modal
        open={contractModalOpen}
        onClose={() => setContractModalOpen(false)}
        title={editingContract ? 'Изменить договор' : 'Новый договор'}
        description="Договор связывает предприятие, программу и практику учебного плана."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setContractModalOpen(false)}
              disabled={contractSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveContract()}
              loading={contractSaving}
              disabled={
                !contractForm.practice_place_id ||
                !contractForm.contract_number.trim()
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {contractFormError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {contractFormError}
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Предприятие
              </span>
              <select
                value={contractForm.practice_place_id}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    practice_place_id: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Выберите предприятие</option>
                {places.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Практика учебного плана
              </span>
              <select
                value={contractForm.component_id}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    component_id: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Без компонента</option>
                {practiceComponents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.program_name} · {item.code} {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Номер договора
              </span>
              <input
                value={contractForm.contract_number}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    contract_number: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учебный год
              </span>
              <input
                value={contractForm.academic_year}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    academic_year: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Начало
              </span>
              <input
                type="date"
                value={contractForm.starts_on}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    starts_on: event.target.value,
                  })
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
                value={contractForm.ends_on}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    ends_on: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Подписан
              </span>
              <input
                type="date"
                value={contractForm.signed_on}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    signed_on: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Статус
              </span>
              <select
                value={contractForm.status}
                onChange={(event) =>
                  setContractForm({
                    ...contractForm,
                    status: event.target.value as PracticeContractStatus,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {(Object.keys(CONTRACT_STATUS_LABELS) as PracticeContractStatus[]).map(
                  (value) => (
                    <option key={value} value={value}>
                      {CONTRACT_STATUS_LABELS[value]}
                    </option>
                  ),
                )}
              </select>
            </label>
          </div>
        </div>
      </Modal>

      <Modal
        open={placementModalOpen}
        onClose={() => setPlacementModalOpen(false)}
        title={
          editingPlacement ? 'Изменить практику' : 'Назначить практику'
        }
        description="Обучающийся, договор, руководители и период практики."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setPlacementModalOpen(false)}
              disabled={placementSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void savePlacement()}
              loading={placementSaving}
              disabled={
                !placementForm.contract_id ||
                !placementForm.student_id ||
                !placementForm.starts_on ||
                !placementForm.ends_on
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {placementFormError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {placementFormError}
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Договор
              </span>
              <select
                value={placementForm.contract_id}
                onChange={(event) =>
                  applyContractToPlacement(event.target.value)
                }
                disabled={Boolean(editingPlacement)}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
              >
                <option value="">Выберите договор</option>
                {contracts.map((item) => (
                  <option key={item.id} value={item.id}>
                    № {item.contract_number} · {item.place_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Обучающийся
              </span>
              <select
                value={placementForm.student_id}
                onChange={(event) => {
                  const profile = profiles.find(
                    (item) => item.user_id === event.target.value,
                  );
                  setPlacementForm({
                    ...placementForm,
                    student_id: event.target.value,
                    group_id: profile?.group_id ?? placementForm.group_id,
                  });
                }}
                disabled={Boolean(editingPlacement)}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
              >
                <option value="">Выберите обучающегося</option>
                {profiles.map((profile) => (
                  <option key={profile.user_id} value={profile.user_id}>
                    {profile.full_name}
                    {profile.group_name ? ` · ${profile.group_name}` : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Группа
              </span>
              <select
                value={placementForm.group_id}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    group_id: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Без группы</option>
                {groups.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Компонент практики
              </span>
              <select
                value={placementForm.component_id}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    component_id: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Из договора</option>
                {practiceComponents.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Руководитель от учреждения
              </span>
              <select
                value={placementForm.supervisor_id}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    supervisor_id: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Не назначен</option>
                {staff.map((item) => (
                  <option key={item.user_id} value={item.user_id}>
                    {item.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Наставник предприятия
              </span>
              <input
                value={placementForm.enterprise_supervisor}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    enterprise_supervisor: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Начало
              </span>
              <input
                type="date"
                value={placementForm.starts_on}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    starts_on: event.target.value,
                  })
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
                value={placementForm.ends_on}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    ends_on: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Часы
              </span>
              <input
                type="number"
                min={0}
                max={2000}
                value={placementForm.total_hours}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    total_hours: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Статус
              </span>
              <select
                value={placementForm.status}
                onChange={(event) =>
                  setPlacementForm({
                    ...placementForm,
                    status: event.target.value as PracticePlacementStatus,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {(Object.keys(PLACEMENT_STATUS_LABELS) as PracticePlacementStatus[]).map(
                  (value) => (
                    <option key={value} value={value}>
                      {PLACEMENT_STATUS_LABELS[value]}
                    </option>
                  ),
                )}
              </select>
            </label>
          </div>
        </div>
      </Modal>

      <Modal
        open={diaryModalOpen}
        onClose={() => setDiaryModalOpen(false)}
        title={editingDiary ? 'Изменить запись' : 'Новая запись дневника'}
        description="Что сделано на практике, сколько часов и результат."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setDiaryModalOpen(false)}
              disabled={diarySaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveDiary()}
              loading={diarySaving}
              disabled={
                !diaryForm.entry_date ||
                !diaryForm.activity.trim() ||
                Number(diaryForm.hours || 0) <= 0
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {diaryFormError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {diaryFormError}
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Дата
              </span>
              <input
                type="date"
                value={diaryForm.entry_date}
                onChange={(event) =>
                  setDiaryForm({
                    ...diaryForm,
                    entry_date: event.target.value,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Часы
              </span>
              <input
                type="number"
                min={0}
                max={24}
                step={0.5}
                value={diaryForm.hours}
                onChange={(event) =>
                  setDiaryForm({ ...diaryForm, hours: event.target.value })
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Содержание работы
              </span>
              <textarea
                rows={3}
                value={diaryForm.activity}
                onChange={(event) =>
                  setDiaryForm({
                    ...diaryForm,
                    activity: event.target.value,
                  })
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Результат
              </span>
              <textarea
                rows={2}
                value={diaryForm.outcome}
                onChange={(event) =>
                  setDiaryForm({
                    ...diaryForm,
                    outcome: event.target.value,
                  })
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Комментарий руководителя
              </span>
              <textarea
                rows={2}
                value={diaryForm.supervisor_comment}
                onChange={(event) =>
                  setDiaryForm({
                    ...diaryForm,
                    supervisor_comment: event.target.value,
                  })
                }
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Статус
              </span>
              <select
                value={diaryForm.status}
                onChange={(event) =>
                  setDiaryForm({
                    ...diaryForm,
                    status: event.target.value as PracticeDiaryStatus,
                  })
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {(Object.keys(DIARY_STATUS_LABELS) as PracticeDiaryStatus[]).map(
                  (value) => (
                    <option key={value} value={value}>
                      {DIARY_STATUS_LABELS[value]}
                    </option>
                  ),
                )}
              </select>
            </label>
          </div>
        </div>
      </Modal>
    </div>
  );
}
