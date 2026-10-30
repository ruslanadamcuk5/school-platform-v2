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
  apiErrorMessage,
  fetchMyPermissions,
  fetchMyServices,
} from '../api/client';
import type {
  EffectivePermission,
  EffectiveService,
  Group,
  MyPermissions,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';

interface AccessContextValue {
  permissions: Set<string>;
  details: EffectivePermission[];
  denied: string[];
  groups: Group[];
  services: EffectiveService[];
  loading: boolean;
  error: string | null;
  can: (code: string) => boolean;
  reload: () => Promise<void>;
}

const AccessContext = createContext<AccessContextValue | null>(null);

export function AccessProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [details, setDetails] = useState<EffectivePermission[]>([]);
  const [denied, setDenied] = useState<string[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [services, setServices] = useState<EffectiveService[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) {
      setPermissions(new Set());
      setDetails([]);
      setDenied([]);
      setGroups([]);
      setServices([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    const [permissionsResult, servicesResult] = await Promise.allSettled([
      fetchMyPermissions(),
      fetchMyServices(),
    ]);

    if (permissionsResult.status === 'fulfilled') {
      const payload: MyPermissions = permissionsResult.value;
      setPermissions(new Set(payload.permissions));
      setDetails(payload.details);
      setDenied(payload.denied);
      setGroups(payload.groups);
    } else {
      setError(apiErrorMessage(permissionsResult.reason));
    }

    if (servicesResult.status === 'fulfilled') {
      setServices(
        [...servicesResult.value.items].sort((a, b) =>
          `${a.category}-${a.name}`.localeCompare(`${b.category}-${b.name}`, 'ru'),
        ),
      );
    } else {
      setError((current) => current ?? apiErrorMessage(servicesResult.reason));
    }

    setLoading(false);
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  const can = useCallback((code: string) => permissions.has(code), [permissions]);

  const value = useMemo(
    () => ({
      permissions,
      details,
      denied,
      groups,
      services,
      loading,
      error,
      can,
      reload: load,
    }),
    [permissions, details, denied, groups, services, loading, error, can, load],
  );

  return <AccessContext.Provider value={value}>{children}</AccessContext.Provider>;
}

export function useAccess(): AccessContextValue {
  const context = useContext(AccessContext);
  if (!context) {
    throw new Error('useAccess must be used inside AccessProvider');
  }
  return context;
}
