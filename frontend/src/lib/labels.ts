import type { Group, Role, ScopeType, Service } from '../api/types';

export const roleLabels: Record<Role, string> = {
  superadmin: 'Республиканский администратор',
  admin: 'Администратор школы',
  methodologist: 'Методист',
  teacher: 'Учитель',
  student: 'Ученик',
  parent: 'Родитель',
  psychologist: 'Психолог',
  secretary: 'Секретарь',
};

export const categoryLabels: Record<Group['category'], string> = {
  students: 'Ученики',
  teachers: 'Учителя',
  administration: 'Администрация',
  methodologists: 'Методисты',
  psychologists: 'Психологи',
  secretaries: 'Секретариат',
  parents: 'Родители',
  other: 'Прочие',
};

export const categoryColors: Record<Group['category'], string> = {
  students: 'bg-sky-100 text-sky-700 ring-sky-200',
  teachers: 'bg-emerald-100 text-emerald-700 ring-emerald-200',
  administration: 'bg-violet-100 text-violet-700 ring-violet-200',
  methodologists: 'bg-amber-100 text-amber-700 ring-amber-200',
  psychologists: 'bg-rose-100 text-rose-700 ring-rose-200',
  secretaries: 'bg-slate-100 text-slate-700 ring-slate-200',
  parents: 'bg-orange-100 text-orange-700 ring-orange-200',
  other: 'bg-slate-100 text-slate-600 ring-slate-200',
};

export const scopeLabels: Record<ScopeType, string> = {
  country: 'Республика',
  region: 'Область',
  city: 'Город / район',
  school: 'Школа',
  class: 'Класс',
};

export const scopeShortLabels: Record<ScopeType, string> = {
  country: 'Страна',
  region: 'Область',
  city: 'Город',
  school: 'Школа',
  class: 'Класс',
};

export const scopeColors: Record<ScopeType, string> = {
  country: 'bg-indigo-100 text-indigo-700 ring-indigo-200',
  region: 'bg-blue-100 text-blue-700 ring-blue-200',
  city: 'bg-cyan-100 text-cyan-700 ring-cyan-200',
  school: 'bg-emerald-100 text-emerald-700 ring-emerald-200',
  class: 'bg-amber-100 text-amber-700 ring-amber-200',
};

export const serviceCategoryLabels: Record<Service['category'], string> = {
  core: 'Ядро',
  education: 'Обучение',
  management: 'Управление',
  communication: 'Коммуникации',
  analytics: 'Аналитика',
  ai: 'Искусственный интеллект',
  security: 'Безопасность',
};

export const serviceCategoryColors: Record<Service['category'], string> = {
  core: 'bg-slate-100 text-slate-700 ring-slate-200',
  education: 'bg-emerald-100 text-emerald-700 ring-emerald-200',
  management: 'bg-violet-100 text-violet-700 ring-violet-200',
  communication: 'bg-sky-100 text-sky-700 ring-sky-200',
  analytics: 'bg-amber-100 text-amber-700 ring-amber-200',
  ai: 'bg-fuchsia-100 text-fuchsia-700 ring-fuchsia-200',
  security: 'bg-rose-100 text-rose-700 ring-rose-200',
};

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 6) return 'Доброй ночи';
  if (hour < 12) return 'Доброе утро';
  if (hour < 18) return 'Добрый день';
  return 'Добрый вечер';
}

export function todayLabel(): string {
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date());
}

export function pluralize(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

export function serviceRoute(code: string): string {
  const known: Record<string, string> = {
    journal: '/journal',
    library: '/library',
    lms: '/lms',
    assessment: '/assessment',
    analytics: '/analytics',
    communication: '/communication',
    documents: '/documents',
    safety: '/safety',
    ai: '/ai',
    admin: '/admin',
  };
  return known[code] ?? `/service/${code}`;
}
