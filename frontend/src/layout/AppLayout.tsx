import { useEffect, useState, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  Boxes,
  ChevronRight,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  UserCircle,
  Users,
  X,
} from 'lucide-react';

import { useAccess } from '../access/AccessContext';
import { useAuth } from '../auth/AuthContext';
import type { EffectiveService } from '../api/types';
import { cn } from '../lib/cn';
import {
  initials,
  roleLabels,
  serviceRoute,
} from '../lib/labels';

const hiddenServiceCodes = new Set(['iam', 'org', 'system', 'audit']);

function NavItem({
  to,
  label,
  icon,
  end,
  onNavigate,
  badge,
}: {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
  onNavigate?: () => void;
  badge?: string;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
          isActive
            ? 'bg-white/10 text-white shadow-sm ring-1 ring-white/10'
            : 'text-slate-400 hover:bg-white/5 hover:text-slate-100',
        )
      }
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/5 text-base ring-1 ring-white/10">
        {icon}
      </span>
      <span className="flex-1 truncate">{label}</span>
      {badge ? (
        <span className="rounded-full bg-accent-500/15 px-2 py-0.5 text-[10px] font-bold text-accent-300 ring-1 ring-accent-400/20">
          {badge}
        </span>
      ) : null}
    </NavLink>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="px-3 pb-2 pt-5 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
      {children}
    </p>
  );
}

function ServiceNavItem({
  service,
  onNavigate,
}: {
  service: EffectiveService;
  onNavigate: () => void;
}) {
  return (
    <NavItem
      to={serviceRoute(service.code)}
      label={service.name}
      icon={<span>{service.icon}</span>}
      onNavigate={onNavigate}
      badge={service.status === 'beta' ? 'β' : undefined}
    />
  );
}

function pageTitle(pathname: string, services: EffectiveService[]): string {
  const map: Record<string, string> = {
    '/': 'Обзор платформы',
    '/groups': 'Группы и права',
    '/services': 'Сервисы платформы',
    '/profile': 'Профиль',
    '/journal': 'Электронный журнал',
    '/library': 'Библиотека',
    '/lms': 'Обучение (LMS)',
    '/assessment': 'Оценивание',
    '/analytics': 'Аналитика',
    '/communication': 'Коммуникации',
    '/documents': 'Документы',
    '/safety': 'Безопасность',
    '/ai': 'AI-помощник',
    '/admin': 'Администрирование',
  };
  if (map[pathname]) return map[pathname];
  const service = services.find((item) => serviceRoute(item.code) === pathname);
  return service?.name ?? 'Школьник';
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const { services, can } = useAccess();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  if (!user) return null;

  const educationServices = services.filter(
    (service) => service.category === 'education' && !hiddenServiceCodes.has(service.code),
  );
  const managementServices = services.filter(
    (service) =>
      ['management', 'analytics', 'communication', 'security', 'ai'].includes(
        service.category,
      ) && !hiddenServiceCodes.has(service.code),
  );

  const closeMobile = () => setMobileOpen(false);

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {mobileOpen ? (
        <button
          type="button"
          aria-label="Закрыть меню"
          className="fixed inset-0 z-30 bg-slate-950/50 backdrop-blur-sm lg:hidden"
          onClick={closeMobile}
        />
      ) : null}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-slate-950 text-slate-300 transition-transform duration-200 lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-20 items-center gap-3 border-b border-white/5 px-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 text-white shadow-lg shadow-brand-900/40">
            <GraduationCap className="h-6 w-6" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-base font-bold tracking-tight text-white">
              Школьник
            </p>
            <p className="truncate text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">
              ЕООП · пилот 0.7
            </p>
          </div>
          <button
            type="button"
            className="ml-auto rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white lg:hidden"
            onClick={closeMobile}
            aria-label="Закрыть меню"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
          <SectionLabel>Обзор</SectionLabel>
          <NavItem
            to="/"
            label="Дашборд"
            icon={<LayoutDashboard className="h-4 w-4" />}
            end
            onNavigate={closeMobile}
          />

          {educationServices.length > 0 ? (
            <>
              <SectionLabel>Обучение</SectionLabel>
              {educationServices.map((service) => (
                <ServiceNavItem
                  key={service.code}
                  service={service}
                  onNavigate={closeMobile}
                />
              ))}
            </>
          ) : null}

          {managementServices.length > 0 ? (
            <>
              <SectionLabel>Управление</SectionLabel>
              {managementServices.map((service) => (
                <ServiceNavItem
                  key={service.code}
                  service={service}
                  onNavigate={closeMobile}
                />
              ))}
            </>
          ) : null}

          {can('iam.groups.read') || can('system.services.read') ? (
            <>
              <SectionLabel>Администрирование</SectionLabel>
              {can('iam.groups.read') ? (
                <NavItem
                  to="/groups"
                  label="Группы и права"
                  icon={<Users className="h-4 w-4" />}
                  onNavigate={closeMobile}
                />
              ) : null}
              {can('system.services.read') ? (
                <NavItem
                  to="/services"
                  label="Сервисы"
                  icon={<Boxes className="h-4 w-4" />}
                  onNavigate={closeMobile}
                />
              ) : null}
            </>
          ) : null}

          <SectionLabel>Аккаунт</SectionLabel>
          <NavItem
            to="/profile"
            label="Профиль и доступ"
            icon={<UserCircle className="h-4 w-4" />}
            onNavigate={closeMobile}
          />
        </nav>

        <div className="border-t border-white/5 p-4">
          <div className="flex items-center gap-3 rounded-2xl bg-white/5 p-3 ring-1 ring-white/5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-400 to-accent-400 text-sm font-bold text-white">
              {initials(user.full_name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{user.full_name}</p>
              <p className="truncate text-[11px] text-slate-400">{roleLabels[user.role]}</p>
            </div>
            <button
              type="button"
              onClick={() => void handleLogout()}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-white/10 hover:text-white"
              aria-label="Выйти"
              title="Выйти"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-3 px-1 text-[10px] leading-4 text-slate-600">
            {services.length} сервисов доступно · пилотный контур
          </p>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-20 items-center gap-3 border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur-md sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-xl p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Открыть меню"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
              <span>Школьник</span>
              <ChevronRight className="h-3 w-3" />
              <span className="truncate text-brand-600">
                {pageTitle(location.pathname, services)}
              </span>
            </div>
            <p className="mt-0.5 truncate text-lg font-bold tracking-tight text-slate-900">
              {pageTitle(location.pathname, services)}
            </p>
          </div>

          <div className="hidden items-center gap-2 md:flex">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                placeholder="Поиск по платформе…"
                className="h-10 w-56 rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-brand-300 focus:bg-white focus:ring-2 focus:ring-brand-100"
              />
            </div>
            <button
              type="button"
              className="relative rounded-xl border border-slate-200 bg-white p-2.5 text-slate-500 transition hover:bg-slate-50 hover:text-slate-700"
              aria-label="Уведомления"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500 ring-2 ring-white" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden rounded-lg bg-slate-100 px-2 py-1 text-[10px] font-bold tracking-wide text-slate-500 sm:inline">
              RU
            </span>
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white py-1.5 pl-1.5 pr-3 text-left transition hover:border-slate-300 hover:bg-slate-50"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-accent-500 text-xs font-bold text-white">
                {initials(user.full_name)}
              </span>
              <span className="hidden min-w-0 sm:block">
                <span className="block max-w-[140px] truncate text-xs font-semibold text-slate-800">
                  {user.full_name}
                </span>
                <span className="block max-w-[140px] truncate text-[10px] text-slate-500">
                  {roleLabels[user.role]}
                </span>
              </span>
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
