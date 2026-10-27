# Frontend (React)

Каталог для нового web-клиента. Прикладной код появится после утверждения
API-контрактов и дизайн-системы.

## Планируемая структура
```text
frontend/
├── src/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── pages/
│   ├── api/
│   ├── i18n/
│   ├── store/
│   └── styles/
├── public/
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## Правила
- React 18+ + TypeScript strict.
- Vite + TailwindCSS.
- i18next для RU/BY/EN.
- Axios с интерсепторами JWT.
- Защищённые маршруты по ролям.
- Доступность (a11y) с первого экрана.
