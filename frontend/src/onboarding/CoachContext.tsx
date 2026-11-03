import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';

import {
  apiErrorMessage,
  completeOnboardingStep,
  startOnboardingModule,
} from '../api/client';
import type { OnboardingModule, OnboardingStep } from '../api/types';

interface CoachSession {
  module: OnboardingModule;
  index: number;
}

interface CoachContextValue {
  session: CoachSession | null;
  currentStep: OnboardingStep | null;
  busy: boolean;
  error: string | null;
  start: (module: OnboardingModule) => Promise<void>;
  next: () => Promise<void>;
  previous: () => void;
  stop: () => void;
  clearError: () => void;
}

const CoachContext = createContext<CoachContextValue | null>(null);

function initialIndex(module: OnboardingModule): number {
  if (module.status === 'completed') return 0;
  if (module.current_step_code) {
    const index = module.steps.findIndex(
      (step) => step.code === module.current_step_code,
    );
    if (index >= 0) return index;
  }
  const firstOpen = module.steps.findIndex((step) => !step.completed);
  return firstOpen >= 0 ? firstOpen : 0;
}

export function CoachProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [session, setSession] = useState<CoachSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(
    async (module: OnboardingModule) => {
      setBusy(true);
      setError(null);
      try {
        await startOnboardingModule(module.code);
        setSession({ module, index: initialIndex(module) });
        const step = module.steps[initialIndex(module)];
        if (step?.route) {
          navigate(step.route);
        }
      } catch (reason) {
        setError(apiErrorMessage(reason));
      } finally {
        setBusy(false);
      }
    },
    [navigate],
  );

  const next = useCallback(async () => {
    if (!session || busy) return;
    const step = session.module.steps[session.index];
    if (!step) {
      setSession(null);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await completeOnboardingStep(session.module.code, step.code);
      const nextIndex = session.index + 1;
      const nextStep = session.module.steps[nextIndex];
      if (!nextStep) {
        setSession(null);
        navigate(`/onboarding/${session.module.code}`);
        return;
      }
      setSession({ ...session, index: nextIndex });
      if (nextStep.route) {
        navigate(nextStep.route);
      }
    } catch (reason) {
      setError(apiErrorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [busy, navigate, session]);

  const previous = useCallback(() => {
    if (!session || session.index === 0) return;
    const nextIndex = session.index - 1;
    setSession({ ...session, index: nextIndex });
    const step = session.module.steps[nextIndex];
    if (step?.route) navigate(step.route);
  }, [navigate, session]);

  const stop = useCallback(() => {
    if (!session) return;
    const code = session.module.code;
    setSession(null);
    setError(null);
    navigate(`/onboarding/${code}`);
  }, [navigate, session]);

  const clearError = useCallback(() => setError(null), []);

  const currentStep = session?.module.steps[session.index] ?? null;

  const value = useMemo(
    () => ({
      session,
      currentStep,
      busy,
      error,
      start,
      next,
      previous,
      stop,
      clearError,
    }),
    [session, currentStep, busy, error, start, next, previous, stop, clearError],
  );

  return <CoachContext.Provider value={value}>{children}</CoachContext.Provider>;
}

export function useCoach(): CoachContextValue {
  const context = useContext(CoachContext);
  if (!context) {
    throw new Error('useCoach must be used inside CoachProvider');
  }
  return context;
}
