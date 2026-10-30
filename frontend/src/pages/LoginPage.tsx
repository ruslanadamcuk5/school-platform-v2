import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  Layers,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { apiErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Button } from '../components/ui';

const features = [
  {
    icon: <Layers className="h-4 w-4" />,
    title: 'Пять уровней управления',
    text: 'Республика → область → город → школа → класс',
  },
  {
    icon: <ShieldCheck className="h-4 w-4" />,
    title: 'Права через группы',
    text: 'Наследование, приоритет и запреты без ручной выдачи',
  },
  {
    icon: <Sparkles className="h-4 w-4" />,
    title: '14 включаемых сервисов',
    text: 'Каждый модуль управляется на своём уровне',
  },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const [loginValue, setLoginValue] = useState('admin');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(loginValue.trim(), password);
      navigate(from, { replace: true });
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 px-10 py-12 text-white lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            backgroundImage:
              'radial-gradient(circle at 15% 15%, rgba(99,102,241,0.35), transparent 32%), radial-gradient(circle at 85% 80%, rgba(16,185,129,0.28), transparent 34%)',
          }}
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)',
            backgroundSize: '42px 42px',
          }}
        />

        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-xl shadow-brand-950/50">
              <GraduationCap className="h-7 w-7" />
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight">Школьник</p>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                Единая образовательная платформа
              </p>
            </div>
          </div>

          <div className="mt-16 max-w-xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
              <Sparkles className="h-3.5 w-3.5" />
              Пилотная версия 0.7
            </span>
            <h1 className="mt-6 text-4xl font-bold leading-[1.1] tracking-tight xl:text-5xl">
              Управление образованием{' '}
              <span className="bg-gradient-to-r from-brand-300 to-accent-300 bg-clip-text text-transparent">
                на уровне республики
              </span>
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-slate-400">
              Микросервисная платформа, где каждая школа подключает только нужные
              модули, а права наследуются от класса до страны.
            </p>
          </div>
        </div>

        <div className="relative mt-12 grid gap-3 xl:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-sm"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 text-accent-300">
                {feature.icon}
              </div>
              <p className="mt-3 text-sm font-semibold text-white">{feature.title}</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">{feature.text}</p>
            </div>
          ))}
        </div>

        <div className="relative mt-10 flex flex-wrap items-center gap-6 text-[11px] font-medium text-slate-500">
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-accent-400" />
            Аудит доступа
          </span>
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-accent-400" />
            Мультитенантность
          </span>
          <span className="inline-flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-accent-400" />
            API-first
          </span>
        </div>
      </section>

      <section className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 text-white shadow-lg shadow-brand-200">
              <GraduationCap className="h-6 w-6" />
            </div>
            <div>
              <p className="text-base font-bold text-slate-900">Школьник</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                ЕООП · пилот 0.7
              </p>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">
                Вход в систему
              </p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
                С возвращением
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Используйте учётную запись, выданную администратором платформы.
              </p>
            </div>

            <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Логин
                </span>
                <input
                  type="text"
                  value={loginValue}
                  onChange={(event) => setLoginValue(event.target.value)}
                  autoComplete="username"
                  required
                  className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                  placeholder="admin"
                />
              </label>

              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                  Пароль
                </span>
                <span className="relative block">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                    required
                    className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 pr-11 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </span>
              </label>

              {error ? (
                <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-700">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>{error}</span>
                </div>
              ) : null}

              <Button type="submit" size="lg" loading={loading} className="w-full">
                Войти
                <ArrowRight className="h-4 w-4" />
              </Button>
            </form>

            <div className="mt-6 flex items-start gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-[11px] leading-4 text-slate-500">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-600" />
              <span>
                Пилотный контур. Все действия с персональными данными фиксируются в
                журнале аудита.
              </span>
            </div>
          </div>

          <p className="mt-5 text-center text-[11px] text-slate-400">
            ЕООП «Школьник» · Республика Беларусь · 2026
          </p>
        </div>
      </section>
    </div>
  );
}
