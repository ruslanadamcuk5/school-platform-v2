import { useEffect, useMemo, useState } from 'react';
import {
  BookOpenCheck,
  Check,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Search,
  Target,
} from 'lucide-react';

import {
  apiErrorMessage,
  createCompetency,
  fetchCompetencies,
  fetchCompetencyMatrix,
  fetchProgramCompetencies,
  replaceCompetencyMatrix,
  replaceProgramCompetencies,
  updateCompetency,
} from '../api/client';
import type {
  Competency,
  CompetencyMatrix,
  CompetencyType,
  EducationCurriculum,
  EducationLevel,
  EducationProgram,
  ProgramCompetency,
} from '../api/types';
import { Badge, Button, Card, Modal, Skeleton } from '../components/ui';

const COMPETENCY_TYPE_LABELS: Record<CompetencyType, string> = {
  universal: 'Универсальная',
  general: 'Общая профессиональная',
  professional: 'Профессиональная',
  other: 'Иная',
};

const COMPETENCY_TYPE_CLASSES: Record<CompetencyType, string> = {
  universal: 'bg-sky-50 text-sky-700 ring-sky-200',
  general: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  professional: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  other: 'bg-slate-100 text-slate-600 ring-slate-200',
};

type CompetencyForm = {
  code: string;
  name: string;
  description: string;
  competency_type: CompetencyType;
  is_active: boolean;
};

type ProgramDraft = Record<
  string,
  { selected: boolean; target_level: string; weight: string }
>;

type MatrixDraft = Record<string, { selected: boolean; weight: string }>;

const EMPTY_FORM: CompetencyForm = {
  code: '',
  name: '',
  description: '',
  competency_type: 'professional',
  is_active: true,
};

function errorText(reason: unknown): string {
  return apiErrorMessage(reason);
}

export function EducationCompetenciesCard({
  level,
  schoolId,
  programs,
  curricula,
  canManage,
}: {
  level: EducationLevel;
  schoolId: string;
  programs: EducationProgram[];
  curricula: EducationCurriculum[];
  canManage: boolean;
}) {
  const [competencies, setCompetencies] = useState<Competency[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<CompetencyType | ''>('');
  const [activeOnly, setActiveOnly] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Competency | null>(null);
  const [form, setForm] = useState<CompetencyForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const [selectedProgramId, setSelectedProgramId] = useState('');
  const [programLinks, setProgramLinks] = useState<ProgramCompetency[]>([]);
  const [programLoading, setProgramLoading] = useState(false);
  const [programSaving, setProgramSaving] = useState(false);
  const [programError, setProgramError] = useState('');
  const [programDraft, setProgramDraft] = useState<ProgramDraft>({});

  const [selectedCurriculumId, setSelectedCurriculumId] = useState('');
  const [matrix, setMatrix] = useState<CompetencyMatrix | null>(null);
  const [matrixLoading, setMatrixLoading] = useState(false);
  const [matrixSaving, setMatrixSaving] = useState(false);
  const [matrixError, setMatrixError] = useState('');
  const [matrixDraft, setMatrixDraft] = useState<MatrixDraft>({});

  async function loadCompetencies() {
    if (!schoolId) return;
    setLoading(true);
    setError('');
    try {
      const rows = await fetchCompetencies(level, schoolId);
      setCompetencies(rows);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  }

  async function loadProgram(programId: string) {
    setProgramLoading(true);
    setProgramError('');
    try {
      const rows = await fetchProgramCompetencies(level, schoolId, programId);
      setProgramLinks(rows);
    } catch (reason) {
      setProgramError(errorText(reason));
      setProgramLinks([]);
    } finally {
      setProgramLoading(false);
    }
  }

  async function loadMatrix(curriculumId: string) {
    setMatrixLoading(true);
    setMatrixError('');
    try {
      const data = await fetchCompetencyMatrix(level, schoolId, curriculumId);
      setMatrix(data);
    } catch (reason) {
      setMatrixError(errorText(reason));
      setMatrix(null);
    } finally {
      setMatrixLoading(false);
    }
  }

  useEffect(() => {
    void loadCompetencies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level, schoolId]);

  useEffect(() => {
    if (!selectedProgramId && programs.length > 0) {
      setSelectedProgramId(programs[0].id);
    }
  }, [programs, selectedProgramId]);

  useEffect(() => {
    if (!selectedCurriculumId && curricula.length > 0) {
      setSelectedCurriculumId(curricula[0].id);
    }
  }, [curricula, selectedCurriculumId]);

  useEffect(() => {
    if (!selectedProgramId) {
      setProgramLinks([]);
      return;
    }
    void loadProgram(selectedProgramId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProgramId]);

  useEffect(() => {
    if (!selectedCurriculumId) {
      setMatrix(null);
      return;
    }
    void loadMatrix(selectedCurriculumId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCurriculumId]);

  useEffect(() => {
    const next: ProgramDraft = {};
    for (const competency of competencies) {
      const link = programLinks.find(
        (item) => item.competency_id === competency.id,
      );
      next[competency.id] = {
        selected: Boolean(link),
        target_level:
          link?.target_level === null || link?.target_level === undefined
            ? '3'
            : String(link.target_level),
        weight: link ? String(link.weight) : '10',
      };
    }
    setProgramDraft(next);
  }, [competencies, programLinks]);

  useEffect(() => {
    if (!matrix) {
      setMatrixDraft({});
      return;
    }
    const links = new Map(
      matrix.links.map((link) => [
        `${link.component_id}:${link.competency_id}`,
        link.weight,
      ]),
    );
    const next: MatrixDraft = {};
    for (const component of matrix.components) {
      for (const competency of matrix.competencies) {
        const key = `${component.id}:${competency.id}`;
        const weight = links.get(key);
        next[key] = {
          selected: weight !== undefined,
          weight: weight === undefined ? '10' : String(weight),
        };
      }
    }
    setMatrixDraft(next);
  }, [matrix]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return competencies.filter((item) => {
      if (query && !`${item.code} ${item.name}`.toLowerCase().includes(query)) {
        return false;
      }
      if (typeFilter && item.competency_type !== typeFilter) return false;
      if (activeOnly && !item.is_active) return false;
      return true;
    });
  }, [competencies, search, typeFilter, activeOnly]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormError('');
    setModalOpen(true);
  }

  function openEdit(item: Competency) {
    setEditing(item);
    setForm({
      code: item.code,
      name: item.name,
      description: item.description ?? '',
      competency_type: item.competency_type,
      is_active: item.is_active,
    });
    setFormError('');
    setModalOpen(true);
  }

  async function saveCompetency() {
    if (!form.code.trim() || !form.name.trim()) return;
    setSaving(true);
    setFormError('');
    try {
      const payload = {
        code: form.code.trim(),
        name: form.name.trim(),
        description: form.description.trim() || null,
        competency_type: form.competency_type,
        is_active: form.is_active,
      };
      if (editing) {
        await updateCompetency(level, schoolId, editing.id, payload);
      } else {
        await createCompetency(level, schoolId, payload);
      }
      setModalOpen(false);
      await loadCompetencies();
      if (selectedCurriculumId) {
        await loadMatrix(selectedCurriculumId);
      }
    } catch (reason) {
      setFormError(errorText(reason));
    } finally {
      setSaving(false);
    }
  }

  async function saveProgramMatrix() {
    if (!selectedProgramId) return;
    setProgramSaving(true);
    setProgramError('');
    try {
      const items = competencies
        .filter((competency) => programDraft[competency.id]?.selected)
        .map((competency) => {
          const draft = programDraft[competency.id];
          const target = Number.parseInt(draft.target_level, 10);
          const weight = Number.parseFloat(draft.weight);
          return {
            competency_id: competency.id,
            target_level: Number.isFinite(target) ? target : null,
            weight: Number.isFinite(weight) ? weight : 0,
          };
        });
      const rows = await replaceProgramCompetencies(
        level,
        schoolId,
        selectedProgramId,
        items,
      );
      setProgramLinks(rows);
    } catch (reason) {
      setProgramError(errorText(reason));
    } finally {
      setProgramSaving(false);
    }
  }

  async function saveCurriculumMatrix() {
    if (!matrix) return;
    setMatrixSaving(true);
    setMatrixError('');
    try {
      const links = [];
      for (const component of matrix.components) {
        for (const competency of matrix.competencies) {
          const key = `${component.id}:${competency.id}`;
          const draft = matrixDraft[key];
          if (!draft?.selected) continue;
          const weight = Number.parseFloat(draft.weight);
          links.push({
            component_id: component.id,
            competency_id: competency.id,
            weight: Number.isFinite(weight) ? weight : 0,
          });
        }
      }
      const data = await replaceCompetencyMatrix(
        level,
        schoolId,
        matrix.curriculum_id,
        links,
      );
      setMatrix(data);
    } catch (reason) {
      setMatrixError(errorText(reason));
    } finally {
      setMatrixSaving(false);
    }
  }

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpenCheck className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-slate-900">
              Компетенции и матрица
            </h2>
            <Badge className="bg-brand-50 text-brand-700 ring-brand-200">
              {competencies.length}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Каталог компетенций, целевые уровни программ и вклад дисциплин
            учебного плана.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void loadCompetencies()}
            disabled={loading}
            aria-label="Обновить компетенции"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          {canManage ? (
            <Button size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Компетенция
            </Button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_220px_auto]">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Поиск по коду или названию"
            className="h-10 w-full rounded-xl border border-slate-200 pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
          />
        </label>
        <select
          value={typeFilter}
          onChange={(event) =>
            setTypeFilter(event.target.value as CompetencyType | '')
          }
          className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
        >
          <option value="">Все типы</option>
          {Object.entries(COMPETENCY_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(event) => setActiveOnly(event.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-brand-600"
          />
          Только активные
        </label>
      </div>

      <div className="mt-4">
        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
            Компетенции не найдены. Добавьте первую компетенцию или измените
            фильтр.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((item) => (
              <div
                key={item.id}
                className="flex flex-col rounded-2xl border border-slate-200 bg-slate-50/40 p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-lg bg-white px-2 py-1 font-mono text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                      {item.code}
                    </span>
                    <Badge className={COMPETENCY_TYPE_CLASSES[item.competency_type]}>
                      {COMPETENCY_TYPE_LABELS[item.competency_type]}
                    </Badge>
                  </div>
                  {canManage ? (
                    <button
                      type="button"
                      onClick={() => openEdit(item)}
                      className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white hover:text-slate-600"
                      aria-label="Изменить компетенцию"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-900">
                  {item.name}
                </p>
                {item.description ? (
                  <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                    {item.description}
                  </p>
                ) : null}
                <div className="mt-auto pt-3">
                  <Badge
                    className={
                      item.is_active
                        ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                        : 'bg-slate-100 text-slate-500 ring-slate-200'
                    }
                  >
                    {item.is_active ? 'Активна' : 'Неактивна'}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Target className="h-4 w-4 text-brand-600" />
                Матрица программы
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Целевой уровень и вес компетенции в образовательной программе.
              </p>
            </div>
            {canManage ? (
              <Button
                size="sm"
                onClick={() => void saveProgramMatrix()}
                loading={programSaving}
                disabled={
                  !selectedProgramId ||
                  programLoading ||
                  competencies.length === 0 ||
                  Boolean(programError)
                }
              >
                <Save className="h-4 w-4" />
                Сохранить
              </Button>
            ) : null}
          </div>

          <select
            value={selectedProgramId}
            onChange={(event) => setSelectedProgramId(event.target.value)}
            className="mt-3 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
          >
            {programs.length === 0 ? (
              <option value="">Нет программ</option>
            ) : null}
            {programs.map((program) => (
              <option key={program.id} value={program.id}>
                {program.code} · {program.name}
              </option>
            ))}
          </select>

          {programError ? (
            <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {programError}
            </div>
          ) : null}

          <div className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1">
            {programLoading ? (
              <>
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
                <Skeleton className="h-12" />
              </>
            ) : competencies.length === 0 ? (
              <p className="py-6 text-center text-sm text-slate-500">
                Сначала добавьте компетенции.
              </p>
            ) : (
              competencies.map((competency) => {
                const draft = programDraft[competency.id] ?? {
                  selected: false,
                  target_level: '3',
                  weight: '10',
                };
                return (
                  <div
                    key={competency.id}
                    className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 px-3 py-2"
                  >
                    <label className="flex min-w-0 flex-1 items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={draft.selected}
                        onChange={(event) =>
                          setProgramDraft((current) => ({
                            ...current,
                            [competency.id]: {
                              ...draft,
                              selected: event.target.checked,
                            },
                          }))
                        }
                        className="h-4 w-4 rounded border-slate-300 text-brand-600"
                      />
                      <span className="truncate">
                        <span className="font-mono text-xs text-slate-500">
                          {competency.code}
                        </span>{' '}
                        {competency.name}
                      </span>
                    </label>
                    <label className="flex items-center gap-1 text-xs text-slate-500">
                      Уровень
                      <select
                        value={draft.target_level}
                        onChange={(event) =>
                          setProgramDraft((current) => ({
                            ...current,
                            [competency.id]: {
                              ...draft,
                              target_level: event.target.value,
                            },
                          }))
                        }
                        className="h-8 rounded-lg border border-slate-200 bg-white px-1 text-xs"
                      >
                        {[1, 2, 3, 4, 5].map((value) => (
                          <option key={value} value={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="flex items-center gap-1 text-xs text-slate-500">
                      Вес
                      <input
                        type="number"
                        min={0}
                        max={100}
                        value={draft.weight}
                        onChange={(event) =>
                          setProgramDraft((current) => ({
                            ...current,
                            [competency.id]: {
                              ...draft,
                              weight: event.target.value,
                            },
                          }))
                        }
                        className="h-8 w-16 rounded-lg border border-slate-200 px-1 text-xs"
                      />
                    </label>
                  </div>
                );
              })
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <BookOpenCheck className="h-4 w-4 text-brand-600" />
                Матрица учебного плана
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Отметьте компоненты, которые формируют компетенцию, и укажите
                вес вклада.
              </p>
            </div>
            {canManage ? (
              <Button
                size="sm"
                onClick={() => void saveCurriculumMatrix()}
                loading={matrixSaving}
                disabled={!matrix || matrixLoading || Boolean(matrixError)}
              >
                <Check className="h-4 w-4" />
                Сохранить
              </Button>
            ) : null}
          </div>

          <select
            value={selectedCurriculumId}
            onChange={(event) => setSelectedCurriculumId(event.target.value)}
            className="mt-3 h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
          >
            {curricula.length === 0 ? (
              <option value="">Нет учебных планов</option>
            ) : null}
            {curricula.map((curriculum) => (
              <option key={curriculum.id} value={curriculum.id}>
                {curriculum.program_name} · {curriculum.name}
              </option>
            ))}
          </select>

          {matrixError ? (
            <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {matrixError}
            </div>
          ) : null}

          {matrixLoading ? (
            <div className="mt-3 space-y-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : !matrix || matrix.components.length === 0 ? (
            <p className="mt-4 rounded-xl border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-500">
              В учебном плане нет компонентов.
            </p>
          ) : matrix.competencies.length === 0 ? (
            <p className="mt-4 rounded-xl border border-dashed border-slate-200 px-3 py-8 text-center text-sm text-slate-500">
              Сначала добавьте компетенции.
            </p>
          ) : (
            <div className="mt-3 max-h-80 overflow-auto rounded-xl border border-slate-200">
              <table className="min-w-full border-collapse text-xs">
                <thead className="sticky top-0 bg-slate-50">
                  <tr>
                    <th className="sticky left-0 z-10 min-w-48 bg-slate-50 px-3 py-2 text-left font-semibold text-slate-600">
                      Компонент
                    </th>
                    {matrix.competencies.map((competency) => (
                      <th
                        key={competency.id}
                        className="min-w-16 px-2 py-2 text-center font-semibold text-slate-600"
                        title={competency.name}
                      >
                        {competency.code}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {matrix.components.map((component) => (
                    <tr key={component.id} className="border-t border-slate-100">
                      <td className="sticky left-0 z-10 bg-white px-3 py-2">
                        <p className="font-medium text-slate-800">
                          {component.code} · {component.name}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          {component.semester} семестр
                        </p>
                      </td>
                      {matrix.competencies.map((competency) => {
                        const key = `${component.id}:${competency.id}`;
                        const draft = matrixDraft[key] ?? {
                          selected: false,
                          weight: '10',
                        };
                        return (
                          <td
                            key={competency.id}
                            className="px-1 py-2 text-center align-middle"
                          >
                            <input
                              type="checkbox"
                              checked={draft.selected}
                              onChange={(event) =>
                                setMatrixDraft((current) => ({
                                  ...current,
                                  [key]: {
                                    ...draft,
                                    selected: event.target.checked,
                                  },
                                }))
                              }
                              className="h-4 w-4 rounded border-slate-300 text-brand-600"
                              aria-label={`${component.code} — ${competency.code}`}
                            />
                            {draft.selected ? (
                              <input
                                type="number"
                                min={0}
                                max={100}
                                value={draft.weight}
                                onChange={(event) =>
                                  setMatrixDraft((current) => ({
                                    ...current,
                                    [key]: {
                                      ...draft,
                                      weight: event.target.value,
                                    },
                                  }))
                                }
                                className="mt-1 block h-7 w-12 rounded-md border border-slate-200 px-1 text-center"
                                aria-label={`Вес ${component.code} — ${competency.code}`}
                              />
                            ) : null}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? 'Изменить компетенцию' : 'Новая компетенция'}
        description="Код уникален в пределах учреждения. Тип влияет на отображение в матрице."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setModalOpen(false)}
              disabled={saving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveCompetency()}
              loading={saving}
              disabled={!form.code.trim() || !form.name.trim()}
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {formError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {formError}
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-[160px_1fr]">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Код
              </span>
              <input
                value={form.code}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
                placeholder="ПК-01"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Название
              </span>
              <input
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
                placeholder="Профессиональная коммуникация"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Тип
            </span>
            <select
              value={form.competency_type}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  competency_type: event.target.value as CompetencyType,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              {Object.entries(COMPETENCY_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Описание
            </span>
            <textarea
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              rows={4}
              placeholder="Что должен уметь обучающийся"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  is_active: event.target.checked,
                }))
              }
              className="h-4 w-4 rounded border-slate-300 text-brand-600"
            />
            Компетенция активна
          </label>
        </div>
      </Modal>
    </Card>
  );
}
