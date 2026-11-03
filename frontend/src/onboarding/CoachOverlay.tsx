import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  MousePointerClick,
  Pause,
  Sparkles,
  X,
} from 'lucide-react';

import { Button, Spinner } from '../components/ui';
import { useCoach } from './CoachContext';

interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const CARD_WIDTH = 390;

export function CoachOverlay() {
  const {
    session,
    currentStep,
    busy,
    error,
    next,
    previous,
    stop,
    clearError,
  } = useCoach();
  const location = useLocation();
  const [rect, setRect] = useState<TargetRect | null>(null);
  const [targetFound, setTargetFound] = useState(false);

  const measure = useCallback(() => {
    if (!currentStep?.target) {
      setRect(null);
      setTargetFound(false);
      return;
    }
    const element = document.querySelector(currentStep.target);
    if (!element) {
      setRect(null);
      setTargetFound(false);
      return;
    }
    const bounds = element.getBoundingClientRect();
    // A target may be taller than the viewport (for example the whole page
    // content). Keep the spotlight inside the visible area so the animated
    // pointer stays on screen and the tutorial remains readable.
    const top = Math.max(0, bounds.top);
    const left = Math.max(0, bounds.left);
    const right = Math.min(window.innerWidth, bounds.right);
    const bottom = Math.min(window.innerHeight, bounds.bottom);
    setRect({
      top,
      left,
      width: Math.max(24, right - left),
      height: Math.max(24, bottom - top),
    });
    setTargetFound(true);
  }, [currentStep?.target]);

  useEffect(() => {
    if (!session || !currentStep) return;
    const element = currentStep.target
      ? document.querySelector(currentStep.target)
      : null;
    if (element) {
      element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
    }
    const timer = window.setTimeout(measure, 260);
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
    };
  }, [currentStep, measure, session, location.pathname]);

  if (!session || !currentStep) return null;

  const viewportWidth = typeof window === 'undefined' ? 1024 : window.innerWidth;
  const viewportHeight = typeof window === 'undefined' ? 768 : window.innerHeight;
  const cardWidth = Math.min(CARD_WIDTH, viewportWidth - 32);
  const centeredLeft = Math.max(16, (viewportWidth - cardWidth) / 2);
  const centeredTop = Math.max(16, viewportHeight / 2 - 180);

  let cardLeft = centeredLeft;
  let cardTop = centeredTop;
  if (rect) {
    cardLeft = Math.min(
      Math.max(16, rect.left + rect.width / 2 - cardWidth / 2),
      viewportWidth - cardWidth - 16,
    );
    const below = rect.top + rect.height + 18;
    cardTop =
      below + 280 < viewportHeight ? below : Math.max(16, rect.top - 300);
  }

  const stepNumber = session.index + 1;
  const totalSteps = session.module.steps.length;
  const isLast = stepNumber >= totalSteps;

  return createPortal(
    <div
      className="fixed inset-0 z-[70]"
      role="dialog"
      aria-modal="false"
      aria-label="Интерактивное обучение"
      data-coach-overlay
    >
      {rect && targetFound ? (
        <>
          <div
            className="pointer-events-none absolute rounded-2xl ring-4 ring-accent-400/90 transition-all duration-500 ease-out coach-glow"
            style={{
              top: Math.max(8, rect.top - 8),
              left: Math.max(8, rect.left - 8),
              width: Math.max(24, rect.width + 16),
              height: Math.max(24, rect.height + 16),
              boxShadow: '0 0 0 9999px rgba(2, 6, 23, 0.72)',
            }}
          />
          <div
            className="pointer-events-none absolute flex h-9 w-9 items-center justify-center rounded-full bg-accent-400 text-slate-950 shadow-xl ring-4 ring-white/80 coach-pointer"
            style={{
              top: Math.max(8, rect.top + rect.height - 12),
              left: Math.max(8, rect.left + rect.width - 12),
            }}
          >
            <MousePointerClick className="h-5 w-5" />
          </div>
        </>
      ) : (
        <div className="absolute inset-0 bg-slate-950/72 backdrop-blur-[2px]" />
      )}

      <div
        className="absolute max-h-[calc(100vh-32px)] overflow-y-auto rounded-3xl border border-white/10 bg-slate-950 p-5 text-white shadow-2xl ring-1 ring-white/10 sm:p-6"
        style={{ top: cardTop, left: cardLeft, width: cardWidth }}
      >
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 text-lg shadow-lg">
            {session.module.icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="rounded-full bg-accent-400/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-accent-300 ring-1 ring-accent-400/20">
                <Sparkles className="mr-1 inline h-3 w-3" />
                Интерактивное обучение
              </span>
              <span className="text-[10px] font-semibold text-slate-500">
                {stepNumber} / {totalSteps}
              </span>
            </div>
            <p className="mt-1 truncate text-sm font-bold text-white">
              {session.module.title}
            </p>
            <p className="truncate text-[11px] text-slate-400">
              {session.module.service_name}
            </p>
          </div>
          <button
            type="button"
            onClick={stop}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white/10 hover:text-white"
            aria-label="Пауза и вернуться к обучению"
            title="Пауза"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand-400 to-accent-400 transition-all duration-500"
            style={{ width: `${Math.round((stepNumber / Math.max(totalSteps, 1)) * 100)}%` }}
          />
        </div>

        <div className="mt-4">
          <h3 className="text-lg font-bold tracking-tight text-white">
            {currentStep.title}
          </h3>
          <p className="mt-2 text-sm leading-6 text-slate-300">{currentStep.body}</p>
        </div>

        {currentStep.tip ? (
          <div className="mt-3 rounded-2xl border border-accent-400/20 bg-accent-400/10 px-3 py-2.5 text-xs leading-5 text-accent-100">
            <span className="font-semibold text-accent-300">Подсказка: </span>
            {currentStep.tip}
          </div>
        ) : null}

        {currentStep.action === 'click' && targetFound ? (
          <p className="mt-3 flex items-center gap-2 text-[11px] font-semibold text-amber-300">
            <MousePointerClick className="h-3.5 w-3.5" />
            Нажмите на подсвеченный элемент, затем продолжите.
          </p>
        ) : null}

        {!targetFound && currentStep.target ? (
          <p className="mt-3 rounded-xl bg-amber-400/10 px-3 py-2 text-[11px] leading-5 text-amber-200">
            Элемент не виден в текущем меню. Проверьте, что сервис включён, или
            продолжите — шаг всё равно будет сохранён.
          </p>
        ) : null}

        {error ? (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-rose-500/15 px-3 py-2 text-xs text-rose-200">
            <span className="flex-1">{error}</span>
            <button
              type="button"
              onClick={clearError}
              className="rounded p-0.5 hover:bg-rose-500/20"
              aria-label="Скрыть ошибку"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : null}

        <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-slate-300 hover:bg-white/10 hover:text-white"
            onClick={previous}
            disabled={session.index === 0 || busy}
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Назад
          </Button>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-slate-400 hover:bg-white/10 hover:text-white"
              onClick={stop}
              disabled={busy}
            >
              <Pause className="h-3.5 w-3.5" />
              Позже
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void next()}
              disabled={busy}
            >
              {busy ? <Spinner className="h-4 w-4 text-white" /> : null}
              {isLast ? 'Завершить модуль' : 'Далее'}
              {!isLast ? <ArrowRight className="h-3.5 w-3.5" /> : null}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
