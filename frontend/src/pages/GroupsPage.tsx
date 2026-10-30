import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Crown,
  Filter,
  Layers,
  Lock,
  Plus,
  Search,
  Shield,
  ShieldOff,
  Trash2,
  UserPlus,
  Users,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  addGroupMembers,
  apiErrorMessage,
  createGroup,
  fetchClasses,
  fetchGroup,
  fetchGroups,
  fetchPermissions,
  fetchSchools,
  fetchUsers,
  removeGroupMember,
  removeGroupPermission,
  setGroupPermission,
} from '../api/client';
import type {
  Group,
  GroupDetail,
  Permission,
  School,
  SchoolClass,
  ScopeType,
  User,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  IconButton,
  Modal,
  PageHeader,
  Skeleton,
  Spinner,
} from '../components/ui';
import { cn } from '../lib/cn';
import {
  categoryColors,
  categoryLabels,
  formatDate,
  initials,
  pluralize,
  roleLabels,
  scopeColors,
  scopeLabels,
  scopeShortLabels,
} from '../lib/labels';

const scopeDepth: Record<ScopeType, number> = {
  country: 0,
  region: 1,
  city: 2,
  school: 3,
  class: 4,
};

const creatableScopes: ScopeType[] = ['country', 'school', 'class'];

const categories = Object.keys(categoryLabels) as Group['category'][];

interface CreateForm {
  code: string;
  name: string;
  description: string;
  category: Group['category'];
  scopeType: ScopeType;
  schoolId: string;
  classId: string;
  parentId: string;
}

const emptyForm: CreateForm = {
  code: '',
  name: '',
  description: '',
  category: 'other',
  scopeType: 'school',
  schoolId: '',
  classId: '',
  parentId: '',
};

export function GroupsPage() {
  const { can, groups: myGroups, reload: reloadAccess } = useAccess();
  const { user } = useAuth();
  const canWrite = can('iam.groups.write');

  const [groups, setGroups] = useState<Group[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [scopeFilter, setScopeFilter] = useState<'all' | ScopeType>('all');
  const [categoryFilter, setCategoryFilter] = useState<'all' | Group['category']>('all');
  const [showInactive, setShowInactive] = useState(false);

  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [schools, setSchools] = useState<School[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [classesLoading, setClassesLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<CreateForm>(emptyForm);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GroupDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailVersion, setDetailVersion] = useState(0);

  const [permissionToAdd, setPermissionToAdd] = useState('');
  const [permissionEffect, setPermissionEffect] = useState<'allow' | 'deny'>('allow');
  const [permissionSaving, setPermissionSaving] = useState(false);
  const [memberSaving, setMemberSaving] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [memberToAdd, setMemberToAdd] = useState('');

  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 4500);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const loadGroups = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGroups({ limit: 200, include_inactive: showInactive });
      setGroups(data.items);
      setTotal(data.total);
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [showInactive]);

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  useEffect(() => {
    let cancelled = false;
    async function loadCatalogs() {
      const [permissionsResult, schoolsResult] = await Promise.allSettled([
        fetchPermissions(),
        fetchSchools(),
      ]);
      if (cancelled) return;
      if (permissionsResult.status === 'fulfilled') {
        setPermissions(permissionsResult.value.items);
      }
      if (schoolsResult.status === 'fulfilled') {
        setSchools(schoolsResult.value);
        if (schoolsResult.value.length > 0) {
          setForm((current) =>
            current.schoolId ? current : { ...current, schoolId: schoolsResult.value[0].id },
          );
        }
      }
    }
    void loadCatalogs();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (form.scopeType !== 'class' || !form.schoolId) {
      setClasses([]);
      return;
    }
    setClassesLoading(true);
    fetchClasses(form.schoolId)
      .then((data) => {
        if (!cancelled) {
          setClasses(data);
          setForm((current) => ({
            ...current,
            classId: current.classId || data[0]?.id || '',
          }));
        }
      })
      .catch(() => {
        if (!cancelled) setClasses([]);
      })
      .finally(() => {
        if (!cancelled) setClassesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [form.scopeType, form.schoolId]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    fetchGroup(selectedId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((caught) => {
        if (!cancelled) setDetailError(apiErrorMessage(caught));
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, detailVersion]);

  useEffect(() => {
    if (!detail || detail.scope_type !== 'school') {
      setUsers([]);
      return;
    }
    let cancelled = false;
    setUsersLoading(true);
    fetchUsers(detail.scope_id)
      .then((data) => {
        if (!cancelled) setUsers(data.items);
      })
      .catch(() => {
        if (!cancelled) setUsers([]);
      })
      .finally(() => {
        if (!cancelled) setUsersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [detail]);

  const filteredGroups = useMemo(() => {
    const query = search.trim().toLowerCase();
    return groups.filter((group) => {
      if (scopeFilter !== 'all' && group.scope_type !== scopeFilter) return false;
      if (categoryFilter !== 'all' && group.category !== categoryFilter) return false;
      if (!query) return true;
      return (
        group.name.toLowerCase().includes(query) ||
        group.code.toLowerCase().includes(query) ||
        (group.description ?? '').toLowerCase().includes(query)
      );
    });
  }, [groups, search, scopeFilter, categoryFilter]);

  const schoolById = useMemo(
    () => new Map(schools.map((school) => [school.id, school])),
    [schools],
  );

  const availableParents = useMemo(() => {
    if (form.scopeType === 'country') return [];
    return groups.filter(
      (group) =>
        group.is_active &&
        group.depth < scopeDepth[form.scopeType] &&
        (form.scopeType !== 'school' || group.scope_type !== 'school'),
    );
  }, [groups, form.scopeType]);

  const alreadyGranted = useMemo(
    () => new Set(detail?.permissions.map((item) => item.permission_code) ?? []),
    [detail],
  );

  const availablePermissions = useMemo(
    () => permissions.filter((permission) => !alreadyGranted.has(permission.code)),
    [permissions, alreadyGranted],
  );

  const availableUsers = useMemo(() => {
    const memberIds = new Set(detail?.members.map((member) => member.user_id) ?? []);
    return users.filter((item) => !memberIds.has(item.id));
  }, [users, detail]);

  function openCreate() {
    setForm({
      ...emptyForm,
      schoolId: schools[0]?.id ?? '',
      scopeType: user?.role === 'superadmin' ? 'country' : 'school',
    });
    setCreateError(null);
    setCreateOpen(true);
  }

  async function handleCreate() {
    setCreateError(null);
    setCreating(true);
    try {
      const scopeId =
        form.scopeType === 'country'
          ? null
          : form.scopeType === 'school'
            ? form.schoolId
            : form.classId;
      if (form.scopeType !== 'country' && !scopeId) {
        throw new Error('Выберите школу или класс для этой группы.');
      }
      const created = await createGroup({
        code: form.code.trim(),
        name: form.name.trim(),
        description: form.description.trim() || null,
        category: form.category,
        scope_type: form.scopeType,
        scope_id: scopeId,
        parent_id: form.parentId || null,
      });
      setCreateOpen(false);
      setNotice(`Группа «${created.name}» создана.`);
      await loadGroups();
      setSelectedId(created.id);
      setDetailVersion((current) => current + 1);
    } catch (caught) {
      setCreateError(apiErrorMessage(caught));
    } finally {
      setCreating(false);
    }
  }

  async function handleAddPermission() {
    if (!detail || !permissionToAdd) return;
    setPermissionSaving(true);
    setDetailError(null);
    try {
      await setGroupPermission(detail.id, permissionToAdd, permissionEffect);
      setPermissionToAdd('');
      setNotice('Право добавлено в группу.');
      setDetailVersion((current) => current + 1);
      await loadGroups();
      await reloadAccess();
    } catch (caught) {
      setDetailError(apiErrorMessage(caught));
    } finally {
      setPermissionSaving(false);
    }
  }

  async function handleRemovePermission(code: string) {
    if (!detail) return;
    if (!window.confirm(`Удалить право ${code} из группы «${detail.name}»?`)) return;
    setPermissionSaving(true);
    setDetailError(null);
    try {
      await removeGroupPermission(detail.id, code);
      setNotice('Право удалено из группы.');
      setDetailVersion((current) => current + 1);
      await loadGroups();
      await reloadAccess();
    } catch (caught) {
      setDetailError(apiErrorMessage(caught));
    } finally {
      setPermissionSaving(false);
    }
  }

  async function handleAddMember() {
    if (!detail || !memberToAdd) return;
    setMemberSaving(true);
    setDetailError(null);
    try {
      await addGroupMembers(detail.id, [memberToAdd]);
      setMemberToAdd('');
      setNotice('Участник добавлен в группу.');
      setDetailVersion((current) => current + 1);
      await loadGroups();
      await reloadAccess();
    } catch (caught) {
      setDetailError(apiErrorMessage(caught));
    } finally {
      setMemberSaving(false);
    }
  }

  async function handleRemoveMember(userId: string) {
    if (!detail) return;
    if (!window.confirm('Удалить участника из группы?')) return;
    setMemberSaving(true);
    setDetailError(null);
    try {
      await removeGroupMember(detail.id, userId);
      setNotice('Участник удалён из группы.');
      setDetailVersion((current) => current + 1);
      await loadGroups();
      await reloadAccess();
    } catch (caught) {
      setDetailError(apiErrorMessage(caught));
    } finally {
      setMemberSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Доступ и иерархия"
        title="Группы и права"
        subtitle="Права выдаются группам на уровне страны, области, города, школы или класса. Более конкретный уровень имеет приоритет, а запрет побеждает разрешение."
        actions={
          canWrite ? (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4" />
              Создать группу
            </Button>
          ) : null
        }
      />

      {notice ? (
        <div className="flex items-center gap-2 rounded-2xl border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-accent-800">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {notice}
        </div>
      ) : null}

      {error ? <ErrorAlert message={error} onRetry={() => void loadGroups()} /> : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniStat
          label="Всего групп"
          value={total}
          icon={<Users className="h-5 w-5" />}
          tone="brand"
        />
        <MiniStat
          label="В реестре прав"
          value={permissions.length}
          icon={<Shield className="h-5 w-5" />}
          tone="accent"
        />
        <MiniStat
          label="Уровней иерархии"
          value={5}
          icon={<Layers className="h-5 w-5" />}
          tone="amber"
        />
        <MiniStat
          label="Мои группы"
          value={myGroups.length}
          icon={<Crown className="h-5 w-5" />}
          tone="sky"
        />
      </div>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Поиск по названию или коду…"
              className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Filter className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <select
                value={scopeFilter}
                onChange={(event) =>
                  setScopeFilter(event.target.value as 'all' | ScopeType)
                }
                className="h-10 appearance-none rounded-xl border border-slate-200 bg-white pl-8 pr-8 text-xs font-semibold text-slate-600 outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="all">Все уровни</option>
                {Object.entries(scopeLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            </div>
            <div className="relative">
              <select
                value={categoryFilter}
                onChange={(event) =>
                  setCategoryFilter(event.target.value as 'all' | Group['category'])
                }
                className="h-10 appearance-none rounded-xl border border-slate-200 bg-white pl-3 pr-8 text-xs font-semibold text-slate-600 outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="all">Все категории</option>
                {categories.map((value) => (
                  <option key={value} value={value}>
                    {categoryLabels[value]}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            </div>
            <label className="flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-600">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(event) => setShowInactive(event.target.checked)}
                className="h-3.5 w-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-400"
              />
              Неактивные
            </label>
          </div>
        </div>

        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full" />
            ))}
          </div>
        ) : filteredGroups.length === 0 ? (
          <EmptyState
            title="Группы не найдены"
            description="Измените фильтры или создайте новую группу для выдачи прав."
            action={
              canWrite ? (
                <Button size="sm" variant="outline" onClick={openCreate}>
                  <Plus className="h-4 w-4" />
                  Создать группу
                </Button>
              ) : null
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left">
              <thead className="border-b border-slate-100 bg-slate-50/70 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  <th className="px-5 py-3">Группа</th>
                  <th className="px-4 py-3">Уровень</th>
                  <th className="px-4 py-3">Категория</th>
                  <th className="px-4 py-3 text-center">Участники</th>
                  <th className="px-4 py-3 text-center">Права</th>
                  <th className="px-4 py-3">Статус</th>
                  <th className="w-12 px-2 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredGroups.map((group) => (
                  <tr
                    key={group.id}
                    onClick={() => setSelectedId(group.id)}
                    className="cursor-pointer transition hover:bg-brand-50/40"
                  >
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-500">
                          {group.code.slice(0, 2).toUpperCase()}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-800">
                            {group.name}
                          </p>
                          <p className="truncate font-mono text-[10px] text-slate-400">
                            {group.code}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex flex-col items-start gap-1">
                        <Badge className={scopeColors[group.scope_type]}>
                          {scopeShortLabels[group.scope_type]}
                        </Badge>
                        <span className="max-w-[150px] truncate text-[10px] text-slate-400">
                          {group.scope_type === 'school'
                            ? schoolById.get(group.scope_id)?.short_name ??
                              schoolById.get(group.scope_id)?.name ??
                              group.scope_id.slice(0, 8)
                            : group.scope_id === '00000000-0000-0000-0000-000000000000'
                              ? 'Все школы'
                              : group.scope_id.slice(0, 8)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge className={categoryColors[group.category]}>
                        {categoryLabels[group.category]}
                      </Badge>
                    </td>
                    <td className="px-4 py-3.5 text-center text-sm font-semibold text-slate-700">
                      {group.members_count}
                    </td>
                    <td className="px-4 py-3.5 text-center text-sm font-semibold text-slate-700">
                      {group.permissions_count}
                    </td>
                    <td className="px-4 py-3.5">
                      <Badge
                        className={
                          group.is_active
                            ? 'bg-accent-50 text-accent-700 ring-accent-200'
                            : 'bg-slate-100 text-slate-500 ring-slate-200'
                        }
                      >
                        <span
                          className={cn(
                            'h-1.5 w-1.5 rounded-full',
                            group.is_active ? 'bg-accent-500' : 'bg-slate-400',
                          )}
                        />
                        {group.is_active ? 'Активна' : 'Выключена'}
                      </Badge>
                    </td>
                    <td className="px-2 py-3.5">
                      <ArrowRight className="h-4 w-4 text-slate-300" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
          <span>
            Показано {filteredGroups.length} из {total}{' '}
            {pluralize(total, 'группы', 'групп', 'групп')}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Lock className="h-3.5 w-3.5" />
            Изменения прав применяются сразу
          </span>
        </div>
      </Card>

      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Новая группа доступа"
        description="Группа получает права на выбранном уровне и передаёт их участникам."
        footer={
          <>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Отмена
            </Button>
            <Button
              onClick={() => void handleCreate()}
              loading={creating}
              disabled={!form.code.trim() || !form.name.trim()}
            >
              <Plus className="h-4 w-4" />
              Создать группу
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {createError ? <ErrorAlert message={createError} /> : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Код группы *
              </span>
              <input
                value={form.code}
                onChange={(event) =>
                  setForm((current) => ({ ...current, code: event.target.value }))
                }
                placeholder="school.teachers"
                className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 font-mono text-sm outline-none focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
              />
              <span className="mt-1 block text-[10px] text-slate-400">
                Только латиница, цифры и символы . _ : -
              </span>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Название *
              </span>
              <input
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="Педагогический совет"
                className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Уровень
              </span>
              <select
                value={form.scopeType}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    scopeType: event.target.value as ScopeType,
                    classId: '',
                    parentId: '',
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {creatableScopes.map((scope) => (
                  <option key={scope} value={scope}>
                    {scopeLabels[scope]}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Категория
              </span>
              <select
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    category: event.target.value as Group['category'],
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {categoryLabels[category]}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {form.scopeType !== 'country' ? (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Школа *
              </span>
              <select
                value={form.schoolId}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    schoolId: event.target.value,
                    classId: '',
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Выберите школу</option>
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {form.scopeType === 'class' ? (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Класс *
              </span>
              <select
                value={form.classId}
                onChange={(event) =>
                  setForm((current) => ({ ...current, classId: event.target.value }))
                }
                disabled={classesLoading || !form.schoolId}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-100"
              >
                <option value="">
                  {classesLoading ? 'Загрузка классов…' : 'Выберите класс'}
                </option>
                {classes.map((schoolClass) => (
                  <option key={schoolClass.id} value={schoolClass.id}>
                    {schoolClass.display_name} · {schoolClass.academic_year}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {availableParents.length > 0 ? (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Родительская группа (необязательно)
              </span>
              <select
                value={form.parentId}
                onChange={(event) =>
                  setForm((current) => ({ ...current, parentId: event.target.value }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Без родителя</option>
                {availableParents.map((group) => (
                  <option key={group.id} value={group.id}>
                    {group.name} · {scopeShortLabels[group.scope_type]}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Описание
            </span>
            <textarea
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
              rows={3}
              placeholder="Назначение группы и правила membership…"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <div className="rounded-xl border border-brand-100 bg-brand-50/60 p-3 text-[11px] leading-5 text-brand-700">
            <p className="font-semibold">Как будут работать права</p>
            <p className="mt-1">
              Группа на уровне класса перекрывает школьную, школьная — городскую.
              При равной глубине запрет (deny) побеждает разрешение (allow).
            </p>
          </div>
        </div>
      </Modal>

      <Modal
        open={Boolean(selectedId)}
        onClose={() => setSelectedId(null)}
        title={detail?.name ?? 'Карточка группы'}
        description={detail?.description ?? detail?.code}
        size="lg"
        footer={
          <Button variant="outline" onClick={() => setSelectedId(null)}>
            Закрыть
          </Button>
        }
      >
        {detailLoading ? (
          <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
            <Spinner />
            Загружаем карточку группы…
          </div>
        ) : detailError ? (
          <ErrorAlert message={detailError} onRetry={() => setDetailVersion((v) => v + 1)} />
        ) : detail ? (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={scopeColors[detail.scope_type]}>
                {scopeLabels[detail.scope_type]}
              </Badge>
              <Badge className={categoryColors[detail.category]}>
                {categoryLabels[detail.category]}
              </Badge>
              <Badge
                className={
                  detail.is_active
                    ? 'bg-accent-50 text-accent-700 ring-accent-200'
                    : 'bg-slate-100 text-slate-500 ring-slate-200'
                }
              >
                {detail.is_active ? 'Активна' : 'Выключена'}
              </Badge>
              {detail.is_system ? (
                <Badge className="bg-brand-50 text-brand-700 ring-brand-200">
                  <Lock className="h-3 w-3" />
                  Системная
                </Badge>
              ) : null}
              <span className="ml-auto font-mono text-[11px] text-slate-400">
                {detail.code}
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <DetailStat label="Участники" value={detail.members.length} />
              <DetailStat label="Права" value={detail.permissions.length} />
              <DetailStat label="Глубина" value={detail.depth} />
            </div>

            <section>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                    <Shield className="h-4 w-4 text-brand-500" />
                    Права группы
                  </h3>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    Разрешения и запреты наследуются участниками группы.
                  </p>
                </div>
                {detail.permissions.length > 0 ? (
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    {detail.permissions.length}{' '}
                    {pluralize(detail.permissions.length, 'право', 'права', 'прав')}
                  </Badge>
                ) : null}
              </div>

              <div className="mt-3 divide-y divide-slate-100 rounded-2xl border border-slate-200">
                {detail.permissions.length === 0 ? (
                  <p className="px-4 py-6 text-center text-xs text-slate-500">
                    У группы пока нет прав.
                  </p>
                ) : (
                  detail.permissions.map((permission) => (
                    <div
                      key={permission.permission_code}
                      className="flex items-center gap-3 px-4 py-2.5"
                    >
                      <span
                        className={cn(
                          'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg',
                          permission.effect === 'allow'
                            ? 'bg-accent-50 text-accent-600'
                            : 'bg-rose-50 text-rose-600',
                        )}
                      >
                        {permission.effect === 'allow' ? (
                          <Shield className="h-3.5 w-3.5" />
                        ) : (
                          <ShieldOff className="h-3.5 w-3.5" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold text-slate-800">
                          {permission.permission_name}
                        </p>
                        <p className="truncate font-mono text-[10px] text-slate-400">
                          {permission.permission_code}
                        </p>
                      </div>
                      <Badge
                        className={
                          permission.effect === 'allow'
                            ? 'bg-accent-50 text-accent-700 ring-accent-200'
                            : 'bg-rose-50 text-rose-700 ring-rose-200'
                        }
                      >
                        {permission.effect === 'allow' ? 'allow' : 'deny'}
                      </Badge>
                      {canWrite ? (
                        <IconButton
                          label="Удалить право"
                          onClick={() => void handleRemovePermission(permission.permission_code)}
                          disabled={permissionSaving}
                          className="text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </IconButton>
                      ) : null}
                    </div>
                  ))
                )}
              </div>

              {canWrite ? (
                <div className="mt-3 flex flex-col gap-2 rounded-2xl bg-slate-50 p-3 sm:flex-row sm:items-center">
                  <select
                    value={permissionToAdd}
                    onChange={(event) => setPermissionToAdd(event.target.value)}
                    className="h-9 min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="">Добавить право…</option>
                    {availablePermissions.map((permission) => (
                      <option key={permission.code} value={permission.code}>
                        {permission.name} ({permission.code})
                      </option>
                    ))}
                  </select>
                  <select
                    value={permissionEffect}
                    onChange={(event) =>
                      setPermissionEffect(event.target.value as 'allow' | 'deny')
                    }
                    className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="allow">Разрешить</option>
                    <option value="deny">Запретить</option>
                  </select>
                  <Button
                    size="sm"
                    onClick={() => void handleAddPermission()}
                    loading={permissionSaving}
                    disabled={!permissionToAdd}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Добавить
                  </Button>
                </div>
              ) : null}
            </section>

            <section>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                    <Users className="h-4 w-4 text-brand-500" />
                    Участники
                  </h3>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    Пользователи, которые получают права этой группы.
                  </p>
                </div>
                <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                  {detail.members.length}
                </Badge>
              </div>

              <div className="mt-3 divide-y divide-slate-100 rounded-2xl border border-slate-200">
                {detail.members.length === 0 ? (
                  <p className="px-4 py-6 text-center text-xs text-slate-500">
                    В группе пока нет участников.
                  </p>
                ) : (
                  detail.members.map((member) => (
                    <div key={member.user_id} className="flex items-center gap-3 px-4 py-2.5">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-accent-500 text-[10px] font-bold text-white">
                        {initials(member.full_name)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-semibold text-slate-800">
                          {member.full_name}
                        </p>
                        <p className="truncate text-[10px] text-slate-400">
                          {member.login} · {roleLabels[member.role as keyof typeof roleLabels] ?? member.role}
                        </p>
                      </div>
                      <span className="hidden text-[10px] text-slate-400 sm:inline">
                        с {formatDate(member.assigned_at)}
                      </span>
                      {canWrite ? (
                        <IconButton
                          label="Удалить участника"
                          onClick={() => void handleRemoveMember(member.user_id)}
                          disabled={memberSaving}
                          className="text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </IconButton>
                      ) : null}
                    </div>
                  ))
                )}
              </div>

              {canWrite && detail.scope_type === 'school' ? (
                <div className="mt-3 flex flex-col gap-2 rounded-2xl bg-slate-50 p-3 sm:flex-row sm:items-center">
                  <select
                    value={memberToAdd}
                    onChange={(event) => setMemberToAdd(event.target.value)}
                    disabled={usersLoading}
                    className="h-9 min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-100"
                  >
                    <option value="">
                      {usersLoading ? 'Загрузка пользователей…' : 'Добавить участника…'}
                    </option>
                    {availableUsers.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.full_name} ({item.login})
                      </option>
                    ))}
                  </select>
                  <Button
                    size="sm"
                    onClick={() => void handleAddMember()}
                    loading={memberSaving}
                    disabled={!memberToAdd}
                  >
                    <UserPlus className="h-3.5 w-3.5" />
                    Добавить
                  </Button>
                </div>
              ) : canWrite ? (
                <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2.5 text-[11px] leading-5 text-slate-500">
                  {detail.scope_type === 'class'
                    ? 'Состав классной группы синхронизируется с учениками класса. Управление участниками — в модуле «Организация».'
                    : 'Участники республиканских, областных и городских групп назначаются через API администратором соответствующего уровня.'}
                </p>
              ) : null}
            </section>

            {detail.children.length > 0 ? (
              <section>
                <h3 className="text-sm font-bold text-slate-900">Дочерние группы</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {detail.children.map((child) => (
                    <button
                      key={child.id}
                      type="button"
                      onClick={() => setSelectedId(child.id)}
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-brand-200 hover:bg-brand-50"
                    >
                      <Layers className="h-3.5 w-3.5 text-brand-500" />
                      {child.name}
                    </button>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        ) : (
          <EmptyState title="Группа не выбрана" />
        )}
      </Modal>
    </div>
  );
}

function MiniStat({
  label,
  value,
  icon,
  tone,
}: {
  label: string;
  value: number;
  icon: ReactNode;
  tone: 'brand' | 'accent' | 'amber' | 'sky';
}) {
  const tones = {
    brand: 'bg-brand-50 text-brand-600',
    accent: 'bg-accent-50 text-accent-600',
    amber: 'bg-amber-50 text-amber-600',
    sky: 'bg-sky-50 text-sky-600',
  } as const;

  return (
    <Card className="flex items-center gap-3 p-4">
      <span className={cn('flex h-10 w-10 items-center justify-center rounded-xl', tones[tone])}>
        {icon}
      </span>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
        <p className="text-xl font-bold text-slate-900">{value}</p>
      </div>
    </Card>
  );
}

function DetailStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-0.5 text-lg font-bold text-slate-900">{value}</p>
    </div>
  );
}
