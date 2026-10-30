import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { Spinner } from '../components/ui';
import { useAuth } from './AuthContext';

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-200">
          <Spinner className="h-6 w-6 text-white" />
        </div>
        <p className="text-sm font-medium text-slate-500">Загружаем платформу…</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
