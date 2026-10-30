import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ShieldOff } from 'lucide-react';

import { AccessProvider, useAccess } from './access/AccessContext';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppLayout } from './layout/AppLayout';
import { Button, Card, EmptyState, PageHeader, Spinner } from './components/ui';
import { DashboardPage } from './pages/DashboardPage';
import { GroupsPage } from './pages/GroupsPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProfilePage } from './pages/ProfilePage';
import { ServicePlaceholderPage } from './pages/ServicePlaceholderPage';
import { ServicesPage } from './pages/ServicesPage';

function PermissionGate({
  permission,
  children,
}: {
  permission: string;
  children: ReactNode;
}) {
  const { can, loading } = useAccess();

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500">
        <Spinner />
        Проверяем права…
      </div>
    );
  }

  if (!can(permission)) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Доступ ограничен" title="Недостаточно прав" />
        <Card>
          <EmptyState
            title="Раздел недоступен"
            description={`Для этого действия нужно право ${permission}. Обратитесь к администратору контура.`}
            icon={<ShieldOff className="h-6 w-6" />}
          />
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}

const servicePages: Array<{ path: string; code: string }> = [
  { path: '/journal', code: 'journal' },
  { path: '/library', code: 'library' },
  { path: '/lms', code: 'lms' },
  { path: '/assessment', code: 'assessment' },
  { path: '/analytics', code: 'analytics' },
  { path: '/communication', code: 'communication' },
  { path: '/documents', code: 'documents' },
  { path: '/safety', code: 'safety' },
  { path: '/ai', code: 'ai' },
  { path: '/admin', code: 'admin' },
];

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route
              element={
                <AccessProvider>
                  <AppLayout />
                </AccessProvider>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route
                path="groups"
                element={
                  <PermissionGate permission="iam.groups.read">
                    <GroupsPage />
                  </PermissionGate>
                }
              />
              <Route
                path="services"
                element={
                  <PermissionGate permission="system.services.read">
                    <ServicesPage />
                  </PermissionGate>
                }
              />
              <Route path="profile" element={<ProfilePage />} />
              {servicePages.map((service) => (
                <Route
                  key={service.path}
                  path={service.path.slice(1)}
                  element={<ServicePlaceholderPage code={service.code} />}
                />
              ))}
              <Route path="service/:code" element={<ServicePlaceholderPage />} />
              <Route path="404" element={<NotFoundPage />} />
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export { PermissionGate };

export function UnauthorizedPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <Card className="max-w-md p-8 text-center">
        <EmptyState
          title="Требуется вход"
          description="Сессия истекла. Войдите снова, чтобы продолжить."
          icon={<ShieldOff className="h-6 w-6" />}
          action={
            <Button onClick={() => window.location.assign('/login')}>
              Перейти ко входу
            </Button>
          }
        />
      </Card>
    </div>
  );
}
