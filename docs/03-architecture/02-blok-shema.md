# Блок-схема платформы

| Параметр | Значение |
|---|---|
| Код документа | ШК-03-02 |
| Версия | 0.1 |
| Статус | Черновик |
| Дата | 27.10.2026 |

## 1. Верхнеуровневая блок-схема
```mermaid
flowchart LR
  subgraph Clients[Клиенты]
    WEB[Web SPA]
    PWA[PWA]
    AND[Android]
    IOS[iOS]
  end

  subgraph Edge[Входной слой]
    WAF[WAF / Anti-DDoS]
    LB[Load Balancer]
    GW[API Gateway]
  end

  subgraph Core[Ядро платформы]
    IAM[IAM / RBAC]
    ORG[Организации]
    LMS[Обучение и контент]
    ASM[Оценивание]
    JRN[Журнал]
    COM[Коммуникации]
    SAF[Безопасность]
    DOC[Документы]
    ANA[Аналитика]
    AI[AI-оркестратор]
    AUD[Аудит]
  end

  subgraph Data[Данные]
    PG[(PostgreSQL)]
    RD[(Redis)]
    S3[(S3 / MinIO)]
    VEC[(pgvector)]
  end

  subgraph External[Внешние системы]
    EJ[ЭЖ/ЭД]
    RIOS[РИОС]
    SSO[ЕСИ/SSO]
    MSG[Telegram/Viber]
    GEO[Google/Yandex]
    LLM[OpenRouter]
    PUSH[FCM/APNs]
  end

  WEB --> WAF
  PWA --> WAF
  AND --> WAF
  IOS --> WAF
  WAF --> LB --> GW
  GW --> IAM
  GW --> ORG
  GW --> LMS
  GW --> ASM
  GW --> JRN
  GW --> COM
  GW --> SAF
  GW --> DOC
  GW --> ANA
  GW --> AI
  GW --> AUD
  IAM --> PG
  ORG --> PG
  LMS --> PG
  LMS --> S3
  ASM --> PG
  ASM --> S3
  JRN --> PG
  COM --> PG
  COM --> RD
  SAF --> PG
  DOC --> PG
  DOC --> S3
  ANA --> PG
  AI --> PG
  AI --> VEC
  AI --> LLM
  AUD --> PG
  GW --> EJ
  GW --> RIOS
  GW --> SSO
  GW --> MSG
  GW --> GEO
  GW --> PUSH
```

## 2. Схема ролей и доступов
```mermaid
flowchart TB
  G[Глобальный администратор] --> R[Администратор области]
  R --> C[Администратор города/района]
  C --> S[Администратор школы]
  S --> D[Директор / завуч]
  S --> SEC[Секретарь]
  S --> T[Учитель]
  T --> ST[Ученик]
  P[Родитель / опекун] --> ST
  M[Методист] --> CONTENT[Контент]
  PS[Психолог] --> ST
  G --> M
  G --> PS
```

## 3. Схема учебного процесса
```mermaid
sequenceDiagram
  participant U as Ученик
  participant C as Клиент
  participant API as API
  participant AI as AI-сервис
  participant T as Учитель
  participant DB as PostgreSQL

  U->>C: Открывает тему
  C->>API: GET /topics/{id}
  API->>DB: Читает тему и прогресс
  DB-->>API: Данные
  API-->>C: Тема, материалы, задания
  U->>C: Выполняет задание
  C->>API: POST /submissions
  API->>DB: Сохраняет ответ
  API->>AI: Проверка фото/аудио/текста
  AI-->>API: Результат и объяснение
  API->>DB: Сохраняет проверку
  API-->>C: Результат
  T->>API: Проверяет и подтверждает
  API->>DB: Обновляет оценку
  API-->>U: Уведомление
```

## 4. Схема офлайн-синхронизации
```mermaid
sequenceDiagram
  participant M as Мобильный клиент
  participant Q as Локальная очередь
  participant API as /sync
  participant DB as PostgreSQL

  M->>Q: Сохраняет операцию
  Note over M,Q: Нет сети
  M->>Q: Повторяет при появлении связи
  Q->>API: Пакет операций
  API->>DB: Проверка operation_id
  alt Операция уже применена
    DB-->>API: Дубликат
    API-->>Q: OK (idempotent)
  else Новая операция
    API->>DB: Применяет
    API-->>Q: OK
  end
  Q->>M: Очищает очередь
```

## 5. Схема документооборота
```mermaid
flowchart LR
  ADM[Администратор] --> TPL[Шаблон документа]
  TPL --> SEC[Секретарь]
  SEC --> PAR[Родитель]
  PAR --> SIGN[Просмотр и подпись]
  SIGN --> SEC
  SEC --> ADM[Утверждение]
  ADM --> ARCH[Архив]
```

## 6. Пояснения
- Схемы являются логическими; физическая deployment-схема — в ШК-03-01.
- Внешние системы подключаются через адаптеры и могут быть отключены.
- Для промышленной эксплуатации предполагается размещение в ЦОД на
  территории Республики Беларусь.
