import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  clearSession,
  getAccessToken,
  getStoredUser,
  loginRequest,
  logoutRequest,
  meRequest,
  storeSession,
  storeUser,
  verifyMfaEnrollment,
  verifyMfaLogin,
} from '../api/client';
import type { LoginResult, TokenPair, User } from '../api/types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (login: string, password: string) => Promise<LoginResult>;
  completeMfa: (mfaToken: string, code: string) => Promise<void>;
  completeMfaEnrollment: (mfaToken: string, code: string) => Promise<string[]>;
  logout: () => Promise<void>;
  reloadUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => getStoredUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!getAccessToken()) {
        setLoading(false);
        return;
      }
      try {
        const current = await meRequest();
        if (!cancelled) {
          setUser(current);
          storeUser(current);
        }
      } catch {
        if (!cancelled) {
          clearSession();
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function onLogout() {
      setUser(null);
    }
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, []);

  const applyTokens = useCallback((tokens: TokenPair) => {
    storeSession(tokens);
    setUser(tokens.user);
  }, []);

  const login = useCallback(
    async (loginValue: string, password: string) => {
      const result = await loginRequest(loginValue, password);
      if ('access_token' in result) {
        applyTokens(result);
      }
      return result;
    },
    [applyTokens],
  );

  const completeMfa = useCallback(
    async (mfaToken: string, code: string) => {
      applyTokens(await verifyMfaLogin(mfaToken, code));
    },
    [applyTokens],
  );

  const completeMfaEnrollment = useCallback(
    async (mfaToken: string, code: string) => {
      const result = await verifyMfaEnrollment(mfaToken, code);
      applyTokens(result);
      return result.recovery_codes;
    },
    [applyTokens],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      setUser(null);
    }
  }, []);

  const reloadUser = useCallback(async () => {
    const current = await meRequest();
    setUser(current);
    storeUser(current);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      completeMfa,
      completeMfaEnrollment,
      logout,
      reloadUser,
    }),
    [
      user,
      loading,
      login,
      completeMfa,
      completeMfaEnrollment,
      logout,
      reloadUser,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
