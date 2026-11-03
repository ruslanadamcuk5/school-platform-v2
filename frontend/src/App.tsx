import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ShieldOff } from 'lucide-react';

import { AccessProvider, useAccess } from './access/AccessContext';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { AppLayout } from './layout/AppLayout';
import { Button, Card, EmptyState, PageHeader, Spinner } from './components/ui';
import { CoachProvider } from './onboarding/CoachContext';
import { CoachOverlay } from './onboarding/CoachOverlay';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { DashboardPage } from './pages/DashboardPage';
import { GroupsPage } from './pages/GroupsPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { OnboardingModulePage } from './pages/OnboardingModulePage';
import { OnboardingPage } from './pages/OnboardingPage';
import { OnboardingReportsPage } from './pages/OnboardingReportsPage';
import { ProfilePage } from './pages/ProfilePage';
import { ServicePlaceholderPage } from './pages/ServicePlaceholderPage';
import { ServicesPage } from './pages/ServicesPage';

function PermissionGate({
  permission,
  children,
}: {
  permission: string | string[];
  children: ReactNode;
}) {
  const { can, loading } = useAccess();
  const required = Array.isArray(permission) ? permission : [permission];

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-sm text-slate-500">
        <Spinner />
        Проверяем права…
      </div>
    );
  }

  if (!required.some((code) => can(code))) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Доступ ограничен" title="Недостаточно прав" />
        <Card>
          <EmptyState
            title="Раздел недоступен"
            description={`Для этого действия нужно одно из прав: ${required.join(
              ', ',
            )}. Обратитесь к администратору контура.`}
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
                  <CoachProvider>
                    <AppLayout />
                    <CoachOverlay />
                  </CoachProvider>
                </AccessProvider>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route
                path="onboarding"
                element={
                  <PermissionGate permission="onboarding.courses.read">
                    <OnboardingPage />
                  </PermissionGate>
                }
              />
              <Route
                path="onboarding/reports"
                element={
                  <PermissionGate permission="onboarding.progress.read">
                    <OnboardingReportsPage />
                  </PermissionGate>
                }
              />
              <Route
                path="onboarding/:moduleCode"
                element={
                  <PermissionGate permission="onboarding.courses.read">
                    <OnboardingModulePage />
                  </PermissionGate>
                }
              />
              <Route
                path="analytics"
                element={
                  <PermissionGate
                    permission={['analytics.reports.read', 'analytics.bi.read']}
                  >
                    <AnalyticsPage />
                  </PermissionGate>
                }
              />
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
