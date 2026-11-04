import { useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
  Building2,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  GraduationCap,
  Layers3,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Users,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import {
  apiErrorMessage,
  createCurriculum,
  createCurriculumComponent,
  createEducationProgram,
  createSchool,
  createStaffProfile,
  createStudentProfile,
  deleteCurriculumComponent,
  fetchCurricula,
  fetchEducationOverview,
  fetchSchools,
  fetchStaffProfiles,
  fetchStudentProfiles,
  fetchUsers,
  updateCurriculum,
  updateCurriculumComponent,
  updateEducationProgram,
  updateStaffProfile,
  updateStudentProfile,
} from '../api/client';
import type {
  AssessmentType,
  CurriculumComponent,
  CurriculumComponentType,
  CurriculumStatus,
  EducationCurriculum,
  EducationLevel,
  EducationOverview,
  EducationProgram,
  School,
  StaffAcademicProfile,
  StudentAcademicProfile,
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
  StatCard,
} from '../components/ui';
import { cn } from '../lib/cn';
import { formatDate, pluralize } from '../lib/labels';
import { EducationSessionsCard } from './EducationSessionsCard';

const LEVEL_META: Record<
  EducationLevel,
  { name: string; short: string; icon: string; description: string }
> = {
  primary: {
    name: 'Начальное образование',
    short: '1–4 классы',
    icon: '🎒',
    description:
      'Первые учителя, адаптация, безопасность и ежедневная связь с родителями.',
  },
  secondary: {
    name: 'Среднее образование',
    short: '5–11 классы',
    icon: '📘',
    description:
      'Предметное обучение, профили, экзамены и профессиональная ориентация.',
  },
  vocational: {
    name: 'Среднее специальное образование',
    short: 'Колледжи и техникумы',
    icon: '🛠️',
    description:
      'Специальности, учебные группы, курсы, практика и зачётные книжки.',
  },
  higher: {
    name: 'Высшее образование',
    short: 'Университеты и академии',
    icon: '🏛️',
    description:
      'Факультеты, кафедры, образовательные программы, кредиты и научная работа.',
  },
};

const FUNDING_LABELS: Record<string, string> = {
  budget: 'Бюджет',
  paid: 'Платно',
  target: 'Целевое',
  other: 'Другое',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Обучается',
  academic_leave: 'Академический отпуск',
  expelled: 'Отчислен',
  graduated: 'Выпускник',
};

type StudentProfileForm = {
  user_id: string;
  program_id: string;
  group_id: string;
  course_year: string;
  record_book_number: string;
  funding_type: StudentAcademicProfile['funding_type'];
  enrollment_year: string;
  academic_status: StudentAcademicProfile['academic_status'];
};

const EMPTY_STUDENT_PROFILE_FORM: StudentProfileForm = {
  user_id: '',
  program_id: '',
  group_id: '',
  course_year: '',
  record_book_number: '',
  funding_type: 'budget',
  enrollment_year: '',
  academic_status: 'active',
};

type StaffProfileForm = {
  user_id: string;
  department: string;
  position: string;
  academic_degree: string;
  academic_title: string;
};

const EMPTY_STAFF_PROFILE_FORM: StaffProfileForm = {
  user_id: '',
  department: '',
  position: '',
  academic_degree: '',
  academic_title: '',
};

const CURRICULUM_STATUS_LABELS: Record<CurriculumStatus, string> = {
  draft: 'Черновик',
  approved: 'Утверждён',
  archived: 'Архив',
};

const COMPONENT_TYPE_LABELS: Record<CurriculumComponentType, string> = {
  discipline: 'Дисциплина',
  module: 'Модуль',
  practice: 'Практика',
  coursework: 'Курсовая работа',
  internship: 'Стажировка',
  other: 'Другое',
};

const ASSESSMENT_LABELS: Record<AssessmentType, string> = {
  exam: 'Экзамен',
  credit: 'Зачёт',
  differentiated_credit: 'Дифференцированный зачёт',
  coursework: 'Курсовая работа',
  practice_report: 'Отчёт по практике',
  other: 'Другое',
};

type CurriculumForm = {
  program_id: string;
  academic_year: string;
  name: string;
  description: string;
  status: CurriculumStatus;
};

const EMPTY_CURRICULUM_FORM: CurriculumForm = {
  program_id: '',
  academic_year: '',
  name: '',
  description: '',
  status: 'draft',
};

type ComponentForm = {
  code: string;
  name: string;
  component_type: CurriculumComponentType;
  semester: string;
  credits: string;
  academic_hours: string;
  contact_hours: string;
  assessment_type: AssessmentType;
  is_optional: boolean;
  order_index: string;
  description: string;
};

const EMPTY_COMPONENT_FORM: ComponentForm = {
  code: '',
  name: '',
  component_type: 'discipline',
  semester: '1',
  credits: '3',
  academic_hours: '0',
  contact_hours: '0',
  assessment_type: 'exam',
  is_optional: false,
  order_index: '0',
  description: '',
};

function number(value: number): string {
  return new Intl.NumberFormat('ru-RU').format(value);
}

function groupLabel(group: { course_year: number | null; name: string }): string {
  if (!group.course_year) return group.name;
  return `${group.course_year} курс · ${group.name}`;
}

export function EducationLevelPage({ level }: { level: EducationLevel }) {
  const { user } = useAuth();
  const { can } = useAccess();
  const meta = LEVEL_META[level];
  const professional = level === 'vocational' || level === 'higher';

  const [schools, setSchools] = useState<School[]>([]);
  const [schoolId, setSchoolId] = useState(user?.school_id ?? '');
  const [year, setYear] = useState('');
  const [data, setData] = useState<EducationOverview | null>(null);
  const [profiles, setProfiles] = useState<StudentAcademicProfile[]>([]);
  const [staffProfiles, setStaffProfiles] = useState<StaffAcademicProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [profilesLoading, setProfilesLoading] = useState(false);
  const [staffProfilesLoading, setStaffProfilesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profilesError, setProfilesError] = useState<string | null>(null);
  const [staffProfilesError, setStaffProfilesError] = useState<string | null>(
    null,
  );
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [programModalOpen, setProgramModalOpen] = useState(false);
  const [editingProgram, setEditingProgram] = useState<EducationProgram | null>(
    null,
  );
  const [programSaving, setProgramSaving] = useState(false);
  const [programError, setProgramError] = useState<string | null>(null);
  const [programForm, setProgramForm] = useState({
    code: '',
    name: '',
    qualification: '',
    duration_years: '',
  });

  const [institutionModalOpen, setInstitutionModalOpen] = useState(false);
  const [institutionSaving, setInstitutionSaving] = useState(false);
  const [institutionError, setInstitutionError] = useState<string | null>(null);
  const [institutionForm, setInstitutionForm] = useState({
    code: '',
    name: '',
    short_name: '',
    city: '',
  });

  const [studentModalOpen, setStudentModalOpen] = useState(false);
  const [editingStudentProfile, setEditingStudentProfile] =
    useState<StudentAcademicProfile | null>(null);
  const [studentSaving, setStudentSaving] = useState(false);
  const [studentError, setStudentError] = useState<string | null>(null);
  const [studentForm, setStudentForm] = useState<StudentProfileForm>({
    ...EMPTY_STUDENT_PROFILE_FORM,
  });

  const [staffModalOpen, setStaffModalOpen] = useState(false);
  const [editingStaffProfile, setEditingStaffProfile] =
    useState<StaffAcademicProfile | null>(null);
  const [staffSaving, setStaffSaving] = useState(false);
  const [staffError, setStaffError] = useState<string | null>(null);
  const [staffForm, setStaffForm] = useState<StaffProfileForm>({
    ...EMPTY_STAFF_PROFILE_FORM,
  });

  const [curricula, setCurricula] = useState<EducationCurriculum[]>([]);
  const [curriculaLoading, setCurriculaLoading] = useState(false);
  const [curriculaError, setCurriculaError] = useState<string | null>(null);
  const [expandedCurriculumId, setExpandedCurriculumId] = useState<
    string | null
  >(null);

  const [curriculumModalOpen, setCurriculumModalOpen] = useState(false);
  const [editingCurriculum, setEditingCurriculum] =
    useState<EducationCurriculum | null>(null);
  const [curriculumSaving, setCurriculumSaving] = useState(false);
  const [curriculumError, setCurriculumError] = useState<string | null>(null);
  const [curriculumForm, setCurriculumForm] = useState<CurriculumForm>({
    ...EMPTY_CURRICULUM_FORM,
  });

  const [componentModalOpen, setComponentModalOpen] = useState(false);
  const [componentCurriculum, setComponentCurriculum] =
    useState<EducationCurriculum | null>(null);
  const [editingComponent, setEditingComponent] =
    useState<CurriculumComponent | null>(null);
  const [componentSaving, setComponentSaving] = useState(false);
  const [componentError, setComponentError] = useState<string | null>(null);
  const [componentForm, setComponentForm] = useState<ComponentForm>({
    ...EMPTY_COMPONENT_FORM,
  });

  const managePermission =
    level === 'primary'
      ? 'primary_education.manage'
      : level === 'secondary'
        ? 'secondary_education.manage'
        : level === 'vocational'
          ? 'vocational_education.programs.manage'
          : 'higher_education.programs.manage';
  const canManagePrograms = professional && can(managePermission);
  const canManageProfiles =
    professional &&
    can(
      level === 'vocational'
        ? 'vocational_education.profiles.manage'
        : 'higher_education.profiles.manage',
    );

  useEffect(() => {
    if (user?.role !== 'superadmin') return;
    let cancelled = false;
    fetchSchools()
      .then((items) => {
        if (cancelled) return;
        const compatible = items.filter((item) =>
          item.education_levels.includes(level),
        );
        setSchools(compatible);
        setSchoolId((current) => current || compatible[0]?.id || '');
      })
      .catch(() => {
        // The overview call reports the access error.
      });
    return () => {
      cancelled = true;
    };
  }, [user?.role, level]);

  useEffect(() => {
    let cancelled = false;
    if (!schoolId) {
      setLoading(false);
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetchEducationOverview(level, {
      school_id: schoolId,
      academic_year: year || undefined,
    })
      .then((payload) => {
        if (cancelled) return;
        setData(payload);
      })
      .catch((reason) => {
        if (!cancelled) setError(apiErrorMessage(reason));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [level, schoolId, year, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    if (!professional || !schoolId) {
      setProfiles([]);
      return;
    }
    setProfilesLoading(true);
    setProfilesError(null);
    fetchStudentProfiles(level, schoolId)
      .then((items) => {
        if (!cancelled) setProfiles(items);
      })
      .catch((reason) => {
        if (!cancelled) setProfilesError(apiErrorMessage(reason));
      })
      .finally(() => {
        if (!cancelled) setProfilesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [level, professional, schoolId, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    if (!professional || !schoolId) {
      setStaffProfiles([]);
      return;
    }
    setStaffProfilesLoading(true);
    setStaffProfilesError(null);
    fetchStaffProfiles(level, schoolId)
      .then((items) => {
        if (!cancelled) setStaffProfiles(items);
      })
      .catch((reason) => {
        if (!cancelled) setStaffProfilesError(apiErrorMessage(reason));
      })
      .finally(() => {
        if (!cancelled) setStaffProfilesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [level, professional, schoolId, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    if (!professional || !schoolId) {
      setCurricula([]);
      return;
    }
    setCurriculaLoading(true);
    setCurriculaError(null);
    fetchCurricula(level, schoolId)
      .then((items) => {
        if (!cancelled) setCurricula(items);
      })
      .catch((reason) => {
        if (!cancelled) setCurriculaError(apiErrorMessage(reason));
      })
      .finally(() => {
        if (!cancelled) setCurriculaLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [level, professional, schoolId, reloadKey]);

  const studentUsers = useMemo(
    () => users.filter((item) => item.role === 'student' && item.is_active),
    [users],
  );
  const staffUsers = useMemo(
    () =>
      users.filter(
        (item) =>
          item.is_active &&
          item.role !== 'student' &&
          item.role !== 'parent',
      ),
    [users],
  );

  const compatibleSchools = useMemo(
    () => schools.filter((item) => item.education_levels.includes(level)),
    [schools, level],
  );

  function openCreateProgram() {
    setEditingProgram(null);
    setProgramError(null);
    setProgramForm({
      code: '',
      name: '',
      qualification: '',
      duration_years: '',
    });
    setProgramModalOpen(true);
  }

  function openEditProgram(program: EducationProgram) {
    setEditingProgram(program);
    setProgramError(null);
    setProgramForm({
      code: program.code,
      name: program.name,
      qualification: program.qualification ?? '',
      duration_years: program.duration_years
        ? String(program.duration_years)
        : '',
    });
    setProgramModalOpen(true);
  }

  async function saveProgram() {
    setProgramError(null);
    setProgramSaving(true);
    try {
      const payload = {
        code: programForm.code.trim(),
        name: programForm.name.trim(),
        qualification: programForm.qualification.trim() || null,
        duration_years: programForm.duration_years
          ? Number(programForm.duration_years)
          : null,
      };
      if (editingProgram) {
        await updateEducationProgram(
          level,
          schoolId || undefined,
          editingProgram.id,
          payload,
        );
      } else {
        await createEducationProgram(level, schoolId || undefined, payload);
      }
      setProgramModalOpen(false);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setProgramError(apiErrorMessage(reason));
    } finally {
      setProgramSaving(false);
    }
  }

  async function loadUsers() {
    if (!schoolId) return;
    setUsersLoading(true);
    setUsersError(null);
    try {
      const result = await fetchUsers(schoolId);
      setUsers(result.items);
    } catch (reason) {
      setUsers([]);
      setUsersError(apiErrorMessage(reason));
    } finally {
      setUsersLoading(false);
    }
  }

  function openCreateStudentProfile() {
    setEditingStudentProfile(null);
    setStudentError(null);
    setStudentForm({
      ...EMPTY_STUDENT_PROFILE_FORM,
      course_year: '1',
      enrollment_year: data?.academic_year.split('/')[0] ?? '',
    });
    setStudentModalOpen(true);
    void loadUsers();
  }

  function openEditStudentProfile(profile: StudentAcademicProfile) {
    setEditingStudentProfile(profile);
    setStudentError(null);
    setStudentForm({
      user_id: profile.user_id,
      program_id: profile.program_id ?? '',
      group_id: profile.group_id ?? '',
      course_year: profile.course_year ? String(profile.course_year) : '',
      record_book_number: profile.record_book_number ?? '',
      funding_type: profile.funding_type,
      enrollment_year: profile.enrollment_year
        ? String(profile.enrollment_year)
        : '',
      academic_status: profile.academic_status,
    });
    setStudentModalOpen(true);
  }

  async function saveStudentProfile() {
    setStudentError(null);
    if (!schoolId) {
      setStudentError('Не выбрано учреждение образования.');
      return;
    }
    if (!editingStudentProfile && !studentForm.user_id) {
      setStudentError('Выберите обучающегося.');
      return;
    }
    setStudentSaving(true);
    try {
      const payload = {
        program_id: studentForm.program_id || null,
        group_id: studentForm.group_id || null,
        course_year: studentForm.course_year
          ? Number(studentForm.course_year)
          : null,
        record_book_number: studentForm.record_book_number.trim() || null,
        funding_type: studentForm.funding_type,
        enrollment_year: studentForm.enrollment_year
          ? Number(studentForm.enrollment_year)
          : null,
        academic_status: studentForm.academic_status,
      };
      if (editingStudentProfile) {
        await updateStudentProfile(
          level,
          schoolId,
          editingStudentProfile.id,
          payload,
        );
      } else {
        await createStudentProfile(level, schoolId, {
          user_id: studentForm.user_id,
          ...payload,
        });
      }
      setStudentModalOpen(false);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setStudentError(apiErrorMessage(reason));
    } finally {
      setStudentSaving(false);
    }
  }

  function openCreateStaffProfile() {
    setEditingStaffProfile(null);
    setStaffError(null);
    setStaffForm({ ...EMPTY_STAFF_PROFILE_FORM });
    setStaffModalOpen(true);
    void loadUsers();
  }

  function openEditStaffProfile(profile: StaffAcademicProfile) {
    setEditingStaffProfile(profile);
    setStaffError(null);
    setStaffForm({
      user_id: profile.user_id,
      department: profile.department ?? '',
      position: profile.position ?? '',
      academic_degree: profile.academic_degree ?? '',
      academic_title: profile.academic_title ?? '',
    });
    setStaffModalOpen(true);
  }

  async function saveStaffProfile() {
    setStaffError(null);
    if (!schoolId) {
      setStaffError('Не выбрано учреждение образования.');
      return;
    }
    if (!editingStaffProfile && !staffForm.user_id) {
      setStaffError('Выберите сотрудника.');
      return;
    }
    setStaffSaving(true);
    try {
      const payload = {
        department: staffForm.department.trim() || null,
        position: staffForm.position.trim() || null,
        academic_degree: staffForm.academic_degree.trim() || null,
        academic_title: staffForm.academic_title.trim() || null,
      };
      if (editingStaffProfile) {
        await updateStaffProfile(
          level,
          schoolId,
          editingStaffProfile.id,
          payload,
        );
      } else {
        await createStaffProfile(level, schoolId, {
          user_id: staffForm.user_id,
          ...payload,
        });
      }
      setStaffModalOpen(false);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setStaffError(apiErrorMessage(reason));
    } finally {
      setStaffSaving(false);
    }
  }

  function openCreateCurriculum() {
    setEditingCurriculum(null);
    setCurriculumError(null);
    setCurriculumForm({
      ...EMPTY_CURRICULUM_FORM,
      program_id: data?.programs[0]?.id ?? '',
      academic_year: data?.academic_year ?? '',
    });
    setCurriculumModalOpen(true);
  }

  function openEditCurriculum(curriculum: EducationCurriculum) {
    setEditingCurriculum(curriculum);
    setCurriculumError(null);
    setCurriculumForm({
      program_id: curriculum.program_id,
      academic_year: curriculum.academic_year,
      name: curriculum.name,
      description: curriculum.description ?? '',
      status: curriculum.status,
    });
    setCurriculumModalOpen(true);
  }

  async function saveCurriculum() {
    setCurriculumError(null);
    if (!schoolId) {
      setCurriculumError('Не выбрано учреждение образования.');
      return;
    }
    if (
      !editingCurriculum &&
      (!curriculumForm.program_id ||
        !/^\d{4}\/\d{4}$/.test(curriculumForm.academic_year.trim()))
    ) {
      setCurriculumError(
        'Выберите программу и укажите учебный год в формате 2026/2027.',
      );
      return;
    }
    if (!curriculumForm.name.trim()) {
      setCurriculumError('Укажите название учебного плана.');
      return;
    }
    setCurriculumSaving(true);
    try {
      const payload = {
        name: curriculumForm.name.trim(),
        description: curriculumForm.description.trim() || null,
        status: curriculumForm.status,
      };
      const saved = editingCurriculum
        ? await updateCurriculum(
            level,
            schoolId,
            editingCurriculum.id,
            payload,
          )
        : await createCurriculum(level, schoolId, {
            program_id: curriculumForm.program_id,
            academic_year: curriculumForm.academic_year.trim(),
            ...payload,
          });
      setCurriculumModalOpen(false);
      setExpandedCurriculumId(saved.id);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setCurriculumError(apiErrorMessage(reason));
    } finally {
      setCurriculumSaving(false);
    }
  }

  function openCreateComponent(curriculum: EducationCurriculum) {
    setComponentCurriculum(curriculum);
    setEditingComponent(null);
    setComponentError(null);
    setComponentForm({ ...EMPTY_COMPONENT_FORM });
    setExpandedCurriculumId(curriculum.id);
    setComponentModalOpen(true);
  }

  function openEditComponent(
    curriculum: EducationCurriculum,
    component: CurriculumComponent,
  ) {
    setComponentCurriculum(curriculum);
    setEditingComponent(component);
    setComponentError(null);
    setComponentForm({
      code: component.code,
      name: component.name,
      component_type: component.component_type,
      semester: String(component.semester),
      credits: String(component.credits),
      academic_hours: String(component.academic_hours),
      contact_hours: String(component.contact_hours),
      assessment_type: component.assessment_type,
      is_optional: component.is_optional,
      order_index: String(component.order_index),
      description: component.description ?? '',
    });
    setComponentModalOpen(true);
  }

  async function saveComponent() {
    setComponentError(null);
    if (!schoolId || !componentCurriculum) {
      setComponentError('Не выбран учебный план.');
      return;
    }
    if (!componentForm.code.trim() || !componentForm.name.trim()) {
      setComponentError('Укажите код и название компонента.');
      return;
    }
    const academicHours = Number(componentForm.academic_hours || 0);
    const contactHours = Number(componentForm.contact_hours || 0);
    if (contactHours > academicHours) {
      setComponentError(
        'Контактные часы не могут превышать общую академическую нагрузку.',
      );
      return;
    }
    setComponentSaving(true);
    try {
      const payload = {
        code: componentForm.code.trim(),
        name: componentForm.name.trim(),
        component_type: componentForm.component_type,
        semester: Number(componentForm.semester || 1),
        credits: Number(componentForm.credits || 0),
        academic_hours: academicHours,
        contact_hours: contactHours,
        assessment_type: componentForm.assessment_type,
        is_optional: componentForm.is_optional,
        order_index: Number(componentForm.order_index || 0),
        description: componentForm.description.trim() || null,
      };
      if (editingComponent) {
        await updateCurriculumComponent(
          level,
          schoolId,
          componentCurriculum.id,
          editingComponent.id,
          payload,
        );
      } else {
        await createCurriculumComponent(
          level,
          schoolId,
          componentCurriculum.id,
          payload,
        );
      }
      setComponentModalOpen(false);
      setExpandedCurriculumId(componentCurriculum.id);
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setComponentError(apiErrorMessage(reason));
    } finally {
      setComponentSaving(false);
    }
  }

  async function removeComponent(
    curriculum: EducationCurriculum,
    component: CurriculumComponent,
  ) {
    if (!schoolId) return;
    if (!window.confirm(`Удалить компонент «${component.name}»?`)) return;
    setCurriculaError(null);
    try {
      await deleteCurriculumComponent(
        level,
        schoolId,
        curriculum.id,
        component.id,
      );
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setCurriculaError(apiErrorMessage(reason));
    }
  }

  function toggleCurriculum(curriculumId: string) {
    setExpandedCurriculumId((current) =>
      current === curriculumId ? null : curriculumId,
    );
  }

  async function saveInstitution() {
    setInstitutionError(null);
    setInstitutionSaving(true);
    try {
      const institutionType =
        level === 'vocational'
          ? 'college'
          : level === 'higher'
            ? 'university'
            : 'school';
      const educationLevels: EducationLevel[] =
        level === 'vocational'
          ? ['vocational']
          : level === 'higher'
            ? ['higher']
            : ['primary', 'secondary'];
      const created = await createSchool({
        code: institutionForm.code.trim(),
        name: institutionForm.name.trim(),
        short_name: institutionForm.short_name.trim() || null,
        institution_type: institutionType,
        education_levels: educationLevels,
        city: institutionForm.city.trim() || null,
      });
      setSchools((current) => [...current, created]);
      setSchoolId(created.id);
      setInstitutionModalOpen(false);
      setInstitutionForm({ code: '', name: '', short_name: '', city: '' });
      setReloadKey((value) => value + 1);
    } catch (reason) {
      setInstitutionError(apiErrorMessage(reason));
    } finally {
      setInstitutionSaving(false);
    }
  }

  const selectedSchool = compatibleSchools.find((item) => item.id === schoolId);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`Ступень образования · ${meta.short}`}
        title={meta.name}
        subtitle={`${meta.description} Ступень включается и отключается отдельно в панели республиканского администратора.`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-brand-50 text-brand-700 ring-brand-200">
              <Layers3 className="h-3 w-3" />
              {professional ? 'Профессиональная ступень' : 'Школьная ступень'}
            </Badge>
            {user?.role === 'superadmin' ? (
              <Button
                variant="outline"
                onClick={() => {
                  setInstitutionError(null);
                  setInstitutionModalOpen(true);
                }}
              >
                <Building2 className="h-4 w-4" />
                Учреждение
              </Button>
            ) : null}
            {canManagePrograms ? (
              <Button onClick={openCreateProgram}>
                <Plus className="h-4 w-4" />
                Программа
              </Button>
            ) : null}
            <Button
              variant="outline"
              onClick={() => {
                setYear('');
                setReloadKey((value) => value + 1);
              }}
              disabled={loading}
            >
              <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
              Обновить
            </Button>
          </div>
        }
      />

      <Card className="p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row">
            {user?.role === 'superadmin' ? (
              <label className="block min-w-0 flex-1">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Учреждение образования
                </span>
                <div className="relative">
                  <Building2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <select
                    value={schoolId}
                    onChange={(event) => {
                      setSchoolId(event.target.value);
                      setYear('');
                    }}
                    className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                  >
                    <option value="">Выберите учреждение</option>
                    {compatibleSchools.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>
              </label>
            ) : (
              <div className="flex min-w-0 flex-1 items-center gap-3 rounded-xl bg-slate-50 px-3 py-2.5">
                <Building2 className="h-4 w-4 text-slate-400" />
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Учреждение
                  </p>
                  <p className="truncate text-sm font-semibold text-slate-800">
                    {data?.institution_name ?? 'Ваше учреждение'}
                  </p>
                </div>
              </div>
            )}

            <label className="block sm:w-48">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учебный год
              </span>
              <div className="relative">
                <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <select
                  value={year || data?.academic_year || ''}
                  onChange={(event) => setYear(event.target.value)}
                  className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                >
                  {(data?.available_years ?? []).map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                  {data && !data.available_years.includes(year) && year ? (
                    <option value={year}>{year}</option>
                  ) : null}
                  {!data?.available_years.length ? (
                    <option value={year || ''}>{year || 'Нет учебных годов'}</option>
                  ) : null}
                </select>
              </div>
            </label>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="h-4 w-4 text-accent-500" />
            Изоляция по учреждению и правам
          </div>
        </div>
      </Card>

      {error ? (
        <ErrorAlert
          message={error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : null}

      {!loading && !error && data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Обучающиеся"
              value={number(data.totals.students)}
              hint={
                professional
                  ? `${data.student_profiles_count} профилей`
                  : 'в группах ступени'
              }
              icon={<Users className="h-5 w-5" />}
              accent="brand"
            />
            <StatCard
              label="Преподаватели"
              value={number(data.totals.teachers)}
              hint="активные аккаунты"
              icon={<GraduationCap className="h-5 w-5" />}
              accent="accent"
            />
            <StatCard
              label="Группы"
              value={number(data.totals.groups)}
              hint={data.academic_year}
              icon={<Building2 className="h-5 w-5" />}
              accent="sky"
            />
            <StatCard
              label={professional ? 'Программы' : 'Сотрудники с профилем'}
              value={number(
                professional ? data.totals.programs : data.staff_profiles_count,
              )}
              hint={
                professional
                  ? `${data.staff_profiles_count} профилей преподавателей`
                  : 'академические профили'
              }
              icon={<BookOpen className="h-5 w-5" />}
              accent="amber"
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
            <Card className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    {professional ? 'Учебные группы' : 'Классы ступени'}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Состав групп и кураторы за {data.academic_year} учебный год.
                  </p>
                </div>
                <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                  {pluralize(data.groups.length, 'группа', 'группы', 'групп')}
                </Badge>
              </div>

              {data.groups.length === 0 ? (
                <EmptyState
                  title="Группы не найдены"
                  description="Для выбранного учебного года в учреждении ещё нет групп или классов этой ступени."
                  icon={<Building2 className="h-6 w-6" />}
                />
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                        <th className="px-2 py-2 font-semibold">Группа</th>
                        <th className="px-2 py-2 font-semibold">Программа</th>
                        <th className="px-2 py-2 text-right font-semibold">Люди</th>
                        <th className="px-2 py-2 font-semibold">Куратор</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.groups.map((group) => (
                        <tr
                          key={group.id}
                          className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60"
                        >
                          <td className="px-2 py-2.5 font-semibold text-slate-800">
                            {groupLabel(group)}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {group.program_name ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-right text-slate-600">
                            {number(group.students)}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {group.curator_name ?? '—'}
                          </td>
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
                    {professional ? 'Образовательные программы' : 'Как устроена ступень'}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {professional
                      ? 'Специальности и программы, доступные в учреждении.'
                      : 'Ступень использует классы, права и сервисы платформы.'}
                  </p>
                </div>
                {professional ? (
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    {pluralize(data.programs.length, 'программа', 'программы', 'программ')}
                  </Badge>
                ) : null}
              </div>

              {!professional ? (
                <div className="mt-4 space-y-3 text-sm text-slate-600">
                  <p>
                    Для этой ступени доступны классы, расписание, журнал,
                    библиотека и аналитика. Дополнительные академические профили
                    не требуются.
                  </p>
                  <div className="rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
                    Уровень: {data.level.name}. Учреждение:{' '}
                    {data.institution_type_label}.
                  </div>
                </div>
              ) : data.programs.length === 0 ? (
                <EmptyState
                  title="Программ пока нет"
                  description="Создайте первую специальность или образовательную программу, чтобы привязать к ней группы и профили."
                  icon={<BookOpen className="h-6 w-6" />}
                  action={
                    canManagePrograms ? (
                      <Button size="sm" onClick={openCreateProgram}>
                        <Plus className="h-4 w-4" />
                        Создать программу
                      </Button>
                    ) : undefined
                  }
                />
              ) : (
                <div className="mt-4 space-y-3">
                  {data.programs.map((program) => (
                    <div
                      key={program.id}
                      className="rounded-xl border border-slate-100 px-3 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-slate-800">
                            {program.name}
                          </p>
                          <p className="mt-0.5 text-xs text-slate-500">
                            {program.code}
                            {program.qualification
                              ? ` · ${program.qualification}`
                              : ''}
                            {program.duration_years
                              ? ` · ${program.duration_years} г.`
                              : ''}
                          </p>
                        </div>
                        {canManagePrograms ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditProgram(program)}
                            aria-label="Изменить программу"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        ) : null}
                      </div>
                      <Badge className="mt-2 bg-accent-50 text-accent-700 ring-accent-200">
                        {program.is_active ? 'Активна' : 'Неактивна'}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {professional ? (
            <Card className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Академические профили
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Зачётные книжки, курс, форма финансирования и академический статус.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    {pluralize(
                      profiles.length,
                      'профиль',
                      'профиля',
                      'профилей',
                    )}
                  </Badge>
                  {canManageProfiles ? (
                    <Button size="sm" onClick={openCreateStudentProfile}>
                      <Plus className="h-4 w-4" />
                      Добавить профиль
                    </Button>
                  ) : null}
                </div>
              </div>

              {profilesError ? (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {profilesError}
                </div>
              ) : profilesLoading ? (
                <div className="mt-4 space-y-2">
                  <Skeleton className="h-10" />
                  <Skeleton className="h-10" />
                </div>
              ) : profiles.length === 0 ? (
                <EmptyState
                  title="Профилей пока нет"
                  description="Профили создаются для обучающихся колледжа или вуза и связываются с программой и группой."
                  icon={<Users className="h-6 w-6" />}
                  action={
                    canManageProfiles ? (
                      <Button size="sm" onClick={openCreateStudentProfile}>
                        <Plus className="h-4 w-4" />
                        Создать профиль
                      </Button>
                    ) : undefined
                  }
                />
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                        <th className="px-2 py-2 font-semibold">Обучающийся</th>
                        <th className="px-2 py-2 font-semibold">Программа</th>
                        <th className="px-2 py-2 font-semibold">Группа</th>
                        <th className="px-2 py-2 text-right font-semibold">Курс</th>
                        <th className="px-2 py-2 font-semibold">Финансирование</th>
                        <th className="px-2 py-2 font-semibold">Статус</th>
                        {canManageProfiles ? (
                          <th className="px-2 py-2 text-right font-semibold">
                            {' '}
                          </th>
                        ) : null}
                      </tr>
                    </thead>
                    <tbody>
                      {profiles.map((profile) => (
                        <tr
                          key={profile.id}
                          className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60"
                        >
                          <td className="px-2 py-2.5">
                            <p className="font-semibold text-slate-800">
                              {profile.full_name}
                            </p>
                            <p className="text-xs text-slate-500">
                              {profile.record_book_number ?? profile.login}
                            </p>
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {profile.program_name ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {profile.group_name ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-right text-slate-600">
                            {profile.course_year ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {FUNDING_LABELS[profile.funding_type] ??
                              profile.funding_type}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {STATUS_LABELS[profile.academic_status] ??
                              profile.academic_status}
                          </td>
                          {canManageProfiles ? (
                            <td className="px-2 py-2.5 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditStudentProfile(profile)}
                                aria-label="Изменить профиль обучающегося"
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
          ) : null}

          {professional ? (
            <Card className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Профили преподавателей
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Кафедры, должности, учёные степени и звания сотрудников.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    {pluralize(
                      staffProfiles.length,
                      'профиль',
                      'профиля',
                      'профилей',
                    )}
                  </Badge>
                  {canManageProfiles ? (
                    <Button size="sm" onClick={openCreateStaffProfile}>
                      <Plus className="h-4 w-4" />
                      Добавить преподавателя
                    </Button>
                  ) : null}
                </div>
              </div>

              {staffProfilesError ? (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {staffProfilesError}
                </div>
              ) : staffProfilesLoading ? (
                <div className="mt-4 space-y-2">
                  <Skeleton className="h-10" />
                  <Skeleton className="h-10" />
                </div>
              ) : staffProfiles.length === 0 ? (
                <EmptyState
                  title="Профилей преподавателей пока нет"
                  description="Профиль связывает сотрудника с кафедрой, должностью и учёной степенью."
                  icon={<GraduationCap className="h-6 w-6" />}
                  action={
                    canManageProfiles ? (
                      <Button size="sm" onClick={openCreateStaffProfile}>
                        <Plus className="h-4 w-4" />
                        Создать профиль
                      </Button>
                    ) : undefined
                  }
                />
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                        <th className="px-2 py-2 font-semibold">Сотрудник</th>
                        <th className="px-2 py-2 font-semibold">Подразделение</th>
                        <th className="px-2 py-2 font-semibold">Должность</th>
                        <th className="px-2 py-2 font-semibold">Учёная степень</th>
                        <th className="px-2 py-2 font-semibold">Учёное звание</th>
                        {canManageProfiles ? (
                          <th className="px-2 py-2 text-right font-semibold">
                            {' '}
                          </th>
                        ) : null}
                      </tr>
                    </thead>
                    <tbody>
                      {staffProfiles.map((profile) => (
                        <tr
                          key={profile.id}
                          className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60"
                        >
                          <td className="px-2 py-2.5">
                            <p className="font-semibold text-slate-800">
                              {profile.full_name}
                            </p>
                            <p className="text-xs text-slate-500">
                              {profile.login}
                            </p>
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {profile.department ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {profile.position ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {profile.academic_degree ?? '—'}
                          </td>
                          <td className="px-2 py-2.5 text-slate-600">
                            {profile.academic_title ?? '—'}
                          </td>
                          {canManageProfiles ? (
                            <td className="px-2 py-2.5 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditStaffProfile(profile)}
                                aria-label="Изменить профиль преподавателя"
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
          ) : null}

          {professional ? (
            <Card className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Учебные планы и кредиты
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Дисциплины, модули, практика, кредиты и формы аттестации.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="bg-slate-100 text-slate-600 ring-slate-200">
                    {pluralize(
                      curricula.length,
                      'план',
                      'плана',
                      'планов',
                    )}
                  </Badge>
                  {canManagePrograms ? (
                    <Button
                      size="sm"
                      onClick={openCreateCurriculum}
                      disabled={!data.programs.length}
                    >
                      <Plus className="h-4 w-4" />
                      Добавить учебный план
                    </Button>
                  ) : null}
                </div>
              </div>

              {curriculaError ? (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {curriculaError}
                </div>
              ) : curriculaLoading ? (
                <div className="mt-4 space-y-2">
                  <Skeleton className="h-12" />
                  <Skeleton className="h-12" />
                </div>
              ) : curricula.length === 0 ? (
                <EmptyState
                  title="Учебных планов пока нет"
                  description={
                    data.programs.length
                      ? 'Создайте учебный план, добавьте дисциплины, модули и практику с кредитами и часами.'
                      : 'Сначала создайте образовательную программу, затем добавьте к ней учебный план.'
                  }
                  icon={<BookOpen className="h-6 w-6" />}
                  action={
                    canManagePrograms && data.programs.length ? (
                      <Button size="sm" onClick={openCreateCurriculum}>
                        <Plus className="h-4 w-4" />
                        Создать учебный план
                      </Button>
                    ) : canManagePrograms ? (
                      <Button size="sm" onClick={openCreateProgram}>
                        <Plus className="h-4 w-4" />
                        Создать программу
                      </Button>
                    ) : undefined
                  }
                />
              ) : (
                <div className="mt-4 space-y-3">
                  {curricula.map((curriculum) => {
                    const expanded =
                      expandedCurriculumId === curriculum.id;
                    return (
                      <div
                        key={curriculum.id}
                        className="rounded-xl border border-slate-100"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3 px-3 py-3">
                          <button
                            type="button"
                            onClick={() => toggleCurriculum(curriculum.id)}
                            className="min-w-0 flex-1 text-left"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="truncate text-sm font-semibold text-slate-800">
                                {curriculum.name}
                              </p>
                              <Badge
                                className={
                                  curriculum.status === 'approved'
                                    ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                                    : curriculum.status === 'archived'
                                      ? 'bg-slate-100 text-slate-500 ring-slate-200'
                                      : 'bg-amber-50 text-amber-700 ring-amber-200'
                                }
                              >
                                {CURRICULUM_STATUS_LABELS[curriculum.status]}
                              </Badge>
                            </div>
                            <p className="mt-1 text-xs text-slate-500">
                              {curriculum.program_name} ·{' '}
                              {curriculum.academic_year} ·{' '}
                              {number(curriculum.total_credits)} з.е. ·{' '}
                              {pluralize(
                                curriculum.components.length,
                                'компонент',
                                'компонента',
                                'компонентов',
                              )}
                            </p>
                          </button>
                          <div className="flex items-center gap-1">
                            {canManagePrograms ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditCurriculum(curriculum)}
                                aria-label="Изменить учебный план"
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                            ) : null}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleCurriculum(curriculum.id)}
                              aria-label={
                                expanded
                                  ? 'Свернуть учебный план'
                                  : 'Развернуть учебный план'
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
                              <div>
                                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                  Компоненты плана
                                </p>
                                {curriculum.description ? (
                                  <p className="mt-1 text-xs text-slate-500">
                                    {curriculum.description}
                                  </p>
                                ) : null}
                              </div>
                              {canManagePrograms ? (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() =>
                                    openCreateComponent(curriculum)
                                  }
                                >
                                  <Plus className="h-4 w-4" />
                                  Компонент
                                </Button>
                              ) : null}
                            </div>

                            {curriculum.components.length === 0 ? (
                              <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
                                В плане пока нет дисциплин и практик. Добавьте
                                первый компонент, чтобы рассчитать кредиты и
                                нагрузку.
                              </p>
                            ) : (
                              <div className="mt-3 overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                  <thead>
                                    <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-500">
                                      <th className="px-2 py-2 font-semibold">
                                        Компонент
                                      </th>
                                      <th className="px-2 py-2 font-semibold">
                                        Тип
                                      </th>
                                      <th className="px-2 py-2 text-right font-semibold">
                                        Сем.
                                      </th>
                                      <th className="px-2 py-2 text-right font-semibold">
                                        Кредиты
                                      </th>
                                      <th className="px-2 py-2 text-right font-semibold">
                                        Часы
                                      </th>
                                      <th className="px-2 py-2 font-semibold">
                                        Аттестация
                                      </th>
                                      {canManagePrograms ? (
                                        <th className="px-2 py-2 text-right font-semibold">
                                          {' '}
                                        </th>
                                      ) : null}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {curriculum.components.map((component) => (
                                      <tr
                                        key={component.id}
                                        className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60"
                                      >
                                        <td className="px-2 py-2.5">
                                          <p className="font-semibold text-slate-800">
                                            {component.name}
                                          </p>
                                          <p className="text-xs text-slate-500">
                                            {component.code}
                                            {component.is_optional
                                              ? ' · по выбору'
                                              : ''}
                                          </p>
                                        </td>
                                        <td className="px-2 py-2.5 text-slate-600">
                                          {
                                            COMPONENT_TYPE_LABELS[
                                              component.component_type
                                            ]
                                          }
                                        </td>
                                        <td className="px-2 py-2.5 text-right text-slate-600">
                                          {component.semester}
                                        </td>
                                        <td className="px-2 py-2.5 text-right text-slate-600">
                                          {number(component.credits)}
                                        </td>
                                        <td className="px-2 py-2.5 text-right text-slate-600">
                                          {number(component.academic_hours)}
                                          {component.contact_hours
                                            ? ` / ${number(
                                                component.contact_hours,
                                              )}`
                                            : ''}
                                        </td>
                                        <td className="px-2 py-2.5 text-slate-600">
                                          {
                                            ASSESSMENT_LABELS[
                                              component.assessment_type
                                            ]
                                          }
                                        </td>
                                        {canManagePrograms ? (
                                          <td className="px-2 py-2.5 text-right">
                                            <div className="flex justify-end gap-1">
                                              <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() =>
                                                  openEditComponent(
                                                    curriculum,
                                                    component,
                                                  )
                                                }
                                                aria-label="Изменить компонент"
                                              >
                                                <Pencil className="h-4 w-4" />
                                              </Button>
                                              <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() =>
                                                  void removeComponent(
                                                    curriculum,
                                                    component,
                                                  )
                                                }
                                                aria-label="Удалить компонент"
                                              >
                                                <Trash2 className="h-4 w-4 text-rose-500" />
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
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          ) : null}

          {professional ? (
            <EducationSessionsCard
              level={level}
              schoolId={schoolId}
              academicYear={data.academic_year}
              groups={data.groups}
              curricula={curricula}
              profiles={profiles}
              staff={staffProfiles}
              canManage={canManagePrograms}
              onDataChanged={() => setReloadKey((value) => value + 1)}
            />
          ) : null}

          <p className="text-xs text-slate-400">
            Сводка сформирована {formatDate(data.generated_at)} ·{' '}
            {selectedSchool?.name ?? data.institution_name}
          </p>
        </>
      ) : null}

      {!loading && !error && !schoolId ? (
        <Card>
          <EmptyState
            title="Выберите учреждение"
            description="Для республиканского администратора учреждение выбирается явно, чтобы не смешивать данные разных контуров."
            icon={<Building2 className="h-6 w-6" />}
            action={
              user?.role === 'superadmin' ? (
                <Button
                  size="sm"
                  onClick={() => setInstitutionModalOpen(true)}
                >
                  <Plus className="h-4 w-4" />
                  Создать учреждение
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : null}

      <Modal
        open={programModalOpen}
        onClose={() => setProgramModalOpen(false)}
        title={editingProgram ? 'Изменить программу' : 'Новая программа'}
        description="Программа связывает специальность, учебные группы и академические профили."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setProgramModalOpen(false)}
              disabled={programSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveProgram()}
              loading={programSaving}
              disabled={
                !programForm.code.trim() || !programForm.name.trim() || !schoolId
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {programError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {programError}
            </div>
          ) : null}
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Код программы
            </span>
            <input
              value={programForm.code}
              onChange={(event) =>
                setProgramForm((current) => ({
                  ...current,
                  code: event.target.value,
                }))
              }
              placeholder="например, 09.02.07"
              className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Название
            </span>
            <input
              value={programForm.name}
              onChange={(event) =>
                setProgramForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              placeholder="Информационные системы и программирование"
              className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Квалификация
              </span>
              <input
                value={programForm.qualification}
                onChange={(event) =>
                  setProgramForm((current) => ({
                    ...current,
                    qualification: event.target.value,
                  }))
                }
                placeholder="Программист"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Срок, лет
              </span>
              <input
                type="number"
                min={1}
                max={10}
                value={programForm.duration_years}
                onChange={(event) =>
                  setProgramForm((current) => ({
                    ...current,
                    duration_years: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
        </div>
      </Modal>

      <Modal
        open={institutionModalOpen}
        onClose={() => setInstitutionModalOpen(false)}
        title="Новое учреждение образования"
        description={
          level === 'vocational'
            ? 'Колледж или техникум для ступени среднего специального образования.'
            : level === 'higher'
              ? 'Университет или академия для ступени высшего образования.'
              : 'Школа, реализующая начальное и среднее образование.'
        }
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setInstitutionModalOpen(false)}
              disabled={institutionSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveInstitution()}
              loading={institutionSaving}
              disabled={
                !institutionForm.code.trim() || !institutionForm.name.trim()
              }
            >
              Создать
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {institutionError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {institutionError}
            </div>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Код учреждения
              </span>
              <input
                value={institutionForm.code}
                onChange={(event) =>
                  setInstitutionForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
                placeholder="by.minsk.college-01"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Краткое название
              </span>
              <input
                value={institutionForm.short_name}
                onChange={(event) =>
                  setInstitutionForm((current) => ({
                    ...current,
                    short_name: event.target.value,
                  }))
                }
                placeholder="Колледж №1"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Полное название
            </span>
            <input
              value={institutionForm.name}
              onChange={(event) =>
                setInstitutionForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              placeholder="Минский государственный колледж"
              className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Город
            </span>
            <input
              value={institutionForm.city}
              onChange={(event) =>
                setInstitutionForm((current) => ({
                  ...current,
                  city: event.target.value,
                }))
              }
              placeholder="Минск"
              className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <div className="rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
            Будет создано учреждение типа «
            {level === 'vocational'
              ? 'колледж / техникум'
              : level === 'higher'
                ? 'университет / академия'
                : 'школа'}
            » со ступенью «{meta.name}». Уровни можно изменить позже через API
            республиканского администратора.
          </div>
        </div>
      </Modal>

      <Modal
        open={studentModalOpen}
        onClose={() => setStudentModalOpen(false)}
        title={
          editingStudentProfile
            ? 'Изменить академический профиль'
            : 'Новый академический профиль'
        }
        description="Профиль связывает обучающегося с программой, группой, курсом и формой финансирования."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setStudentModalOpen(false)}
              disabled={studentSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveStudentProfile()}
              loading={studentSaving}
              disabled={
                studentSaving ||
                (!editingStudentProfile &&
                  (usersLoading || !studentForm.user_id))
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {studentError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {studentError}
            </div>
          ) : null}

          {editingStudentProfile ? (
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Обучающийся
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                {editingStudentProfile.full_name}
              </p>
              <p className="text-xs text-slate-500">
                {editingStudentProfile.login}
              </p>
            </div>
          ) : (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Обучающийся
              </span>
              <select
                value={studentForm.user_id}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    user_id: event.target.value,
                  }))
                }
                disabled={usersLoading || !studentUsers.length}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
              >
                <option value="">
                  {usersLoading
                    ? 'Загрузка пользователей…'
                    : studentUsers.length
                      ? 'Выберите обучающегося'
                      : 'Нет доступных обучающихся'}
                </option>
                {studentUsers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.full_name} · {item.login}
                  </option>
                ))}
              </select>
              {usersError ? (
                <p className="mt-1.5 text-xs text-rose-600">{usersError}</p>
              ) : null}
            </label>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Образовательная программа
              </span>
              <select
                value={studentForm.program_id}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    program_id: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Не выбрана</option>
                {(data?.programs ?? []).map((program) => (
                  <option key={program.id} value={program.id}>
                    {program.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Группа
              </span>
              <select
                value={studentForm.group_id}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    group_id: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Не выбрана</option>
                {(data?.groups ?? []).map((group) => (
                  <option key={group.id} value={group.id}>
                    {groupLabel(group)}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Курс
              </span>
              <input
                type="number"
                min={1}
                max={10}
                value={studentForm.course_year}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    course_year: event.target.value,
                  }))
                }
                placeholder="1"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Год поступления
              </span>
              <input
                type="number"
                min={2000}
                max={2100}
                value={studentForm.enrollment_year}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    enrollment_year: event.target.value,
                  }))
                }
                placeholder="2025"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Номер зачётной книжки
              </span>
              <input
                value={studentForm.record_book_number}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    record_book_number: event.target.value,
                  }))
                }
                placeholder="например, 2025-001"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Форма финансирования
              </span>
              <select
                value={studentForm.funding_type}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    funding_type: event.target
                      .value as StudentAcademicProfile['funding_type'],
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="budget">Бюджет</option>
                <option value="paid">Платно</option>
                <option value="target">Целевое</option>
                <option value="other">Другое</option>
              </select>
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Академический статус
              </span>
              <select
                value={studentForm.academic_status}
                onChange={(event) =>
                  setStudentForm((current) => ({
                    ...current,
                    academic_status: event.target
                      .value as StudentAcademicProfile['academic_status'],
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="active">Обучается</option>
                <option value="academic_leave">Академический отпуск</option>
                <option value="expelled">Отчислен</option>
                <option value="graduated">Выпускник</option>
              </select>
            </label>
          </div>
        </div>
      </Modal>

      <Modal
        open={staffModalOpen}
        onClose={() => setStaffModalOpen(false)}
        title={
          editingStaffProfile
            ? 'Изменить профиль преподавателя'
            : 'Новый профиль преподавателя'
        }
        description="Профиль хранит подразделение, должность и учёные степени сотрудника."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setStaffModalOpen(false)}
              disabled={staffSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveStaffProfile()}
              loading={staffSaving}
              disabled={
                staffSaving ||
                (!editingStaffProfile &&
                  (usersLoading || !staffForm.user_id))
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {staffError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {staffError}
            </div>
          ) : null}

          {editingStaffProfile ? (
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Сотрудник
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                {editingStaffProfile.full_name}
              </p>
              <p className="text-xs text-slate-500">
                {editingStaffProfile.login}
              </p>
            </div>
          ) : (
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Сотрудник
              </span>
              <select
                value={staffForm.user_id}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    user_id: event.target.value,
                  }))
                }
                disabled={usersLoading || !staffUsers.length}
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50 disabled:text-slate-400"
              >
                <option value="">
                  {usersLoading
                    ? 'Загрузка пользователей…'
                    : staffUsers.length
                      ? 'Выберите сотрудника'
                      : 'Нет доступных сотрудников'}
                </option>
                {staffUsers.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.full_name} · {item.login}
                  </option>
                ))}
              </select>
              {usersError ? (
                <p className="mt-1.5 text-xs text-rose-600">{usersError}</p>
              ) : null}
            </label>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Подразделение
              </span>
              <input
                value={staffForm.department}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    department: event.target.value,
                  }))
                }
                placeholder="Кафедра информатики"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Должность
              </span>
              <input
                value={staffForm.position}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    position: event.target.value,
                  }))
                }
                placeholder="Доцент"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учёная степень
              </span>
              <input
                value={staffForm.academic_degree}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    academic_degree: event.target.value,
                  }))
                }
                placeholder="Кандидат наук"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Учёное звание
              </span>
              <input
                value={staffForm.academic_title}
                onChange={(event) =>
                  setStaffForm((current) => ({
                    ...current,
                    academic_title: event.target.value,
                  }))
                }
                placeholder="Доцент"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>
        </div>
      </Modal>

      <Modal
        open={curriculumModalOpen}
        onClose={() => setCurriculumModalOpen(false)}
        title={
          editingCurriculum ? 'Изменить учебный план' : 'Новый учебный план'
        }
        description="Учебный план задаёт состав дисциплин, практик, кредитов и форм аттестации на учебный год."
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setCurriculumModalOpen(false)}
              disabled={curriculumSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveCurriculum()}
              loading={curriculumSaving}
              disabled={
                curriculumSaving ||
                !curriculumForm.name.trim() ||
                !schoolId ||
                (!editingCurriculum && !curriculumForm.program_id)
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {curriculumError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {curriculumError}
            </div>
          ) : null}

          {editingCurriculum ? (
            <div className="rounded-xl bg-slate-50 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Программа и учебный год
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-800">
                {editingCurriculum.program_name}
              </p>
              <p className="text-xs text-slate-500">
                {editingCurriculum.academic_year}
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Образовательная программа
                </span>
                <select
                  value={curriculumForm.program_id}
                  onChange={(event) =>
                    setCurriculumForm((current) => ({
                      ...current,
                      program_id: event.target.value,
                    }))
                  }
                  className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                >
                  <option value="">Выберите программу</option>
                  {(data?.programs ?? []).map((program) => (
                    <option key={program.id} value={program.id}>
                      {program.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Учебный год
                </span>
                <input
                  value={curriculumForm.academic_year}
                  onChange={(event) =>
                    setCurriculumForm((current) => ({
                      ...current,
                      academic_year: event.target.value,
                    }))
                  }
                  placeholder="2026/2027"
                  className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
                />
              </label>
            </div>
          )}

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Название плана
            </span>
            <input
              value={curriculumForm.name}
              onChange={(event) =>
                setCurriculumForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              placeholder="Основной учебный план"
              className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Описание
            </span>
            <textarea
              value={curriculumForm.description}
              onChange={(event) =>
                setCurriculumForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              rows={3}
              placeholder="Профиль, форма обучения, особенности набора"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Статус
            </span>
            <select
              value={curriculumForm.status}
              onChange={(event) =>
                setCurriculumForm((current) => ({
                  ...current,
                  status: event.target.value as CurriculumStatus,
                }))
              }
              className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            >
              <option value="draft">Черновик</option>
              <option value="approved">Утверждён</option>
              <option value="archived">Архив</option>
            </select>
          </label>
        </div>
      </Modal>

      <Modal
        open={componentModalOpen}
        onClose={() => setComponentModalOpen(false)}
        title={
          editingComponent
            ? 'Изменить компонент плана'
            : 'Новый компонент плана'
        }
        description={
          componentCurriculum
            ? `${componentCurriculum.name} · ${componentCurriculum.academic_year}`
            : 'Дисциплина, модуль, практика или курсовая работа.'
        }
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setComponentModalOpen(false)}
              disabled={componentSaving}
            >
              Отмена
            </Button>
            <Button
              onClick={() => void saveComponent()}
              loading={componentSaving}
              disabled={
                componentSaving ||
                !schoolId ||
                !componentForm.code.trim() ||
                !componentForm.name.trim()
              }
            >
              Сохранить
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {componentError ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {componentError}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Код
              </span>
              <input
                value={componentForm.code}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
                placeholder="MATH-101"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Название
              </span>
              <input
                value={componentForm.name}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
                placeholder="Математический анализ"
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Тип компонента
              </span>
              <select
                value={componentForm.component_type}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    component_type: event.target
                      .value as CurriculumComponentType,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="discipline">Дисциплина</option>
                <option value="module">Модуль</option>
                <option value="practice">Практика</option>
                <option value="coursework">Курсовая работа</option>
                <option value="internship">Стажировка</option>
                <option value="other">Другое</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Семестр
              </span>
              <input
                type="number"
                min={1}
                max={12}
                value={componentForm.semester}
                onChange={(event) =>
                  setComponentForm((current) => ({
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
                Кредиты
              </span>
              <input
                type="number"
                min={0}
                max={100}
                step={0.5}
                value={componentForm.credits}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    credits: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Академические часы
              </span>
              <input
                type="number"
                min={0}
                max={20000}
                value={componentForm.academic_hours}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    academic_hours: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Контактные часы
              </span>
              <input
                type="number"
                min={0}
                max={20000}
                value={componentForm.contact_hours}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    contact_hours: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Форма аттестации
              </span>
              <select
                value={componentForm.assessment_type}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    assessment_type: event.target.value as AssessmentType,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              >
                <option value="exam">Экзамен</option>
                <option value="credit">Зачёт</option>
                <option value="differentiated_credit">
                  Дифференцированный зачёт
                </option>
                <option value="coursework">Курсовая работа</option>
                <option value="practice_report">Отчёт по практике</option>
                <option value="other">Другое</option>
              </select>
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                Порядок
              </span>
              <input
                type="number"
                min={0}
                value={componentForm.order_index}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    order_index: event.target.value,
                  }))
                }
                className="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
              />
            </label>
            <label className="flex items-center gap-2 pt-6 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={componentForm.is_optional}
                onChange={(event) =>
                  setComponentForm((current) => ({
                    ...current,
                    is_optional: event.target.checked,
                  }))
                }
                className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-200"
              />
              Компонент по выбору
            </label>
          </div>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-slate-700">
              Описание
            </span>
            <textarea
              value={componentForm.description}
              onChange={(event) =>
                setComponentForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              rows={3}
              placeholder="Содержание, база практики или особые условия"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
            />
          </label>
        </div>
      </Modal>
    </div>
  );
}
