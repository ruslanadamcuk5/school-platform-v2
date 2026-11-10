import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  GraduationCap,
  KeyRound,
  Layers,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { apiErrorMessage, startMfaEnrollment } from '../api/client';
import type { MfaChallenge, MfaEnrollStart } from '../api/types';
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

type LoginStep = 'credentials' | 'mfa' | 'enroll' | 'recovery';

export function LoginPage() {
  const { user, login, completeMfa, completeMfaEnrollment } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';

  const [loginValue, setLoginValue] = useState('admin');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<LoginStep>('credentials');
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  const [enrollment, setEnrollment] = useState<MfaEnrollStart | null>(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);

  if (user && step !== 'recovery') {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await login(loginValue.trim(), password);
      if ('access_token' in result) {
        navigate(from, { replace: true });
        return;
      }
      setChallenge(result);
      if (result.status === 'mfa_enrollment_required') {
        const started = await startMfaEnrollment(result.mfa_token);
        setEnrollment(started);
        setStep('enroll');
      } else {
        setStep('mfa');
      }
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function handleMfaSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!challenge) return;
    setError(null);
    setLoading(true);
    try {
      await completeMfa(challenge.mfa_token, code.trim());
      navigate(from, { replace: true });
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function handleEnrollmentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!challenge) return;
    setError(null);
    setLoading(true);
    try {
      const codes = await completeMfaEnrollment(challenge.mfa_token, code.trim());
      setRecoveryCodes(codes);
      setStep('recovery');
    } catch (caught) {
      setError(apiErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function copySecret() {
    if (!enrollment) return;
    try {
      await navigator.clipboard.writeText(enrollment.secret);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Не удалось скопировать секрет. Выделите его вручную.');
    }
  }

  function resetLogin() {
    setStep('credentials');
    setChallenge(null);
    setEnrollment(null);
    setCode('');
    setRecoveryCodes([]);
    setError(null);
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
              <p className="text-lg font-bold tracking-tight">ВЕКТОР</p>
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                Единая образовательная республиканская платформа
              </p>
            </div>
          </div>

          <div className="mt-16 max-w-xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
              <Sparkles className="h-3.5 w-3.5" />
              Пилотная версия 0.8
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
              <p className="text-base font-bold text-slate-900">ВЕКТОР</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                ЕОРП · пилот 0.8
              </p>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">
                {step === 'credentials'
                  ? 'Вход в систему'
                  : step === 'mfa'
                    ? 'Двухфакторная аутентификация'
                    : step === 'enroll'
                      ? 'Настройка MFA'
                      : 'Резервные коды'}
              </p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
                {step === 'credentials'
                  ? 'С возвращением'
                  : step === 'mfa'
                    ? 'Подтвердите вход'
                    : step === 'enroll'
                      ? 'Защитите аккаунт'
                      : 'Сохраните коды'}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {step === 'credentials'
                  ? 'Используйте учётную запись, выданную администратором платформы.'
                  : step === 'mfa'
                    ? 'Введите 6-значный код из приложения-аутентификатора или резервный код.'
                    : step === 'enroll'
                      ? 'Для superadmin MFA обязательна. Добавьте секрет в приложение и подтвердите первый код.'
                      : 'Эти коды показываются один раз. Каждый код можно использовать только один раз.'}
              </p>
            </div>

            {step === 'credentials' ? (
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
            ) : null}

            {step === 'mfa' ? (
              <form className="mt-7 space-y-4" onSubmit={handleMfaSubmit}>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                    Код или резервный код
                  </span>
                  <input
                    type="text"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    autoComplete="one-time-code"
                    required
                    autoFocus
                    className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-center font-mono text-lg tracking-[0.2em] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                    placeholder="000000"
                    aria-label="Код подтверждения"
                  />
                </label>

                {error ? (
                  <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-700">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                ) : null}

                <Button type="submit" size="lg" loading={loading} className="w-full">
                  Подтвердить
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <button
                  type="button"
                  onClick={resetLogin}
                  className="w-full text-center text-xs font-medium text-slate-500 hover:text-slate-700"
                >
                  Вернуться к вводу пароля
                </button>
              </form>
            ) : null}

            {step === 'enroll' ? (
              <form className="mt-7 space-y-4" onSubmit={handleEnrollmentSubmit}>
                <div className="rounded-xl border border-brand-100 bg-brand-50/60 p-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-brand-800">
                    <KeyRound className="h-4 w-4" />
                    Секрет для приложения
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="min-w-0 flex-1 break-all rounded-lg bg-white px-2.5 py-2 font-mono text-xs text-slate-700 ring-1 ring-brand-100">
                      {enrollment?.secret ?? '—'}
                    </code>
                    <button
                      type="button"
                      onClick={() => void copySecret()}
                      className="rounded-lg p-2 text-brand-600 hover:bg-white"
                      aria-label="Скопировать секрет"
                    >
                      {copied ? (
                        <CheckCircle2 className="h-4 w-4 text-accent-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  <p className="mt-2 text-[11px] leading-4 text-brand-700">
                    Добавьте аккаунт вручную в Google Authenticator, Aegis или
                    аналогичном приложении. Ссылка для импорта:
                  </p>
                  <code className="mt-1 block break-all text-[10px] leading-4 text-slate-500">
                    {enrollment?.otpauth_uri ?? ''}
                  </code>
                </div>

                <label className="block">
                  <span className="mb-1.5 block text-xs font-semibold text-slate-700">
                    Первый 6-значный код
                  </span>
                  <input
                    type="text"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    autoComplete="one-time-code"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    required
                    autoFocus
                    className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 text-center font-mono text-lg tracking-[0.2em] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                    placeholder="000000"
                    aria-label="Первый код MFA"
                  />
                </label>

                {error ? (
                  <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-700">
                    <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                ) : null}

                <Button type="submit" size="lg" loading={loading} className="w-full">
                  Включить MFA
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <button
                  type="button"
                  onClick={resetLogin}
                  className="w-full text-center text-xs font-medium text-slate-500 hover:text-slate-700"
                >
                  Вернуться к вводу пароля
                </button>
              </form>
            ) : null}

            {step === 'recovery' ? (
              <div className="mt-7 space-y-4">
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
                  Сохраните коды в защищённом месте. Они понадобятся, если телефон
                  или приложение-аутентификатор станут недоступны.
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {recoveryCodes.map((recoveryCode) => (
                    <code
                      key={recoveryCode}
                      className="rounded-lg bg-slate-50 px-3 py-2 text-center font-mono text-xs text-slate-700 ring-1 ring-slate-200"
                    >
                      {recoveryCode}
                    </code>
                  ))}
                </div>
                <Button
                  type="button"
                  size="lg"
                  className="w-full"
                  onClick={() => navigate(from, { replace: true })}
                >
                  Я сохранил коды, продолжить
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            ) : null}

            <div className="mt-6 flex items-start gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-[11px] leading-4 text-slate-500">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-600" />
              <span>
                Пилотный контур. Все действия с персональными данными фиксируются в
                журнале аудита.
              </span>
            </div>
          </div>

          <p className="mt-5 text-center text-[11px] text-slate-400">
            ЕОРП «ВЕКТОР» · Республика Беларусь · 2026
          </p>
        </div>
      </section>
    </div>
  );
}
