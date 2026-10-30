import { Link } from 'react-router-dom';
import { ArrowLeft, Compass } from 'lucide-react';

import { Button, Card, EmptyState, PageHeader } from '../components/ui';

export function NotFoundPage() {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="404" title="Страница не найдена" />
      <Card>
        <EmptyState
          title="Такого раздела нет"
          description="Возможно, ссылка устарела или сервис отключён в вашем контуре."
          icon={<Compass className="h-6 w-6" />}
          action={
            <Link to="/">
              <Button variant="outline">
                <ArrowLeft className="h-4 w-4" />
                На дашборд
              </Button>
            </Link>
          }
        />
      </Card>
    </div>
  );
}
