# Архитектура

## Общая схема

```mermaid
flowchart TB
    A["Customer Portal"] --> B["Control Plane API"]
    C["Admin Panel"] --> B
    B --> D["PostgreSQL / JSON store in MVP"]
    B --> E["Profile Generator"]
    B --> F["PKI Service"]
    B --> G["Provisioning Service"]
    G --> H["Dedicated VPN Server"]
    F --> H
    E --> I["Apple / Android / Windows packages"]
```

## MVP

В MVP вместо полноценной БД используется JSON-файл. Это упрощает запуск и позволяет показать бизнес-логику без инфраструктуры.

MVP-компоненты:

- `JsonStore` хранит клиентов, серверы, слоты, invite-ссылки и audit log.
- `ControlPlaneService` реализует правила продукта.
- `ProfileGenerator` создает VPN-пакеты под платформы.
- `DevPki` создает тестовые сертификаты через OpenSSL.
- `ServerConfig` генерирует пример `swanctl.conf`.

## Product version

В продуктовой версии JSON-store заменяется на PostgreSQL, а ручное создание VPS заменяется provisioning worker.

Целевые компоненты:

- API backend
- Admin panel
- Customer portal
- PostgreSQL
- Redis queue
- Provisioning workers
- PKI service
- Package generation workers
- Monitoring service
- Per-server metrics agent

## Главный lifecycle устройства

```mermaid
sequenceDiagram
    participant Customer
    participant API
    participant PKI
    participant Generator
    participant VPN

    Customer->>API: Create invite link
    API-->>Customer: One-time URL
    Customer->>API: Friend activates URL
    API->>PKI: Issue client certificate
    PKI-->>API: Client cert and PFX
    API->>Generator: Build platform package
    Generator-->>API: Profile package
    API-->>Customer: Download package
    Customer->>VPN: Connect with unique identity
```

