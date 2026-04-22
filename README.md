# Personal VPN Control Plane MVP

Портфолио-проект для сервиса персонального VPN.

Идея продукта: один платящий клиент получает отдельный VPN-сервер, а доступ к нему выдается через ограниченные `device slots`. Один слот равен одному устройству и одному уникальному VPN-профилю. Клиент может отправлять друзьям одноразовые ссылки активации, но не может бесконтрольно раздать один общий файл.

## Что реализовано

- Техническое задание MVP и продуктовой архитектуры.
- JSON-based mock control plane без внешних зависимостей.
- Управление клиентами, серверами, слотами и invite-ссылками.
- Жесткий лимит `20` устройств на клиента.
- Одноразовые invite-ссылки с TTL.
- Автоматическая генерация VPN-пакетов:
  - Apple: `.mobileconfig`
  - Android: `.sswan`
  - Windows: `.zip` с `client.pfx`, `root-ca.cer`, `install.ps1`, `README.txt`
- Dev PKI через локальный `openssl`: CA, server cert, client cert, PKCS#12/PFX.
- Генерация примера `swanctl.conf` для strongSwan с `unique = keep`.
- Unit tests на invite-flow, лимиты, revoke и генерацию профилей.
- GitHub Actions workflow для тестов.
- Static product demo в `web_demo/`.
- OpenAPI-контракт для будущего backend API.
- ADR-документы с ключевыми архитектурными решениями.

## Документы

- [Полное ТЗ](docs/vpn_service_tz.md)
- [PDF-версия ТЗ](docs/vpn_service_tz.pdf)
- [Архитектура](docs/architecture.md)
- [Безопасность](docs/security.md)
- [MVP scope](docs/mvp_scope.md)
- [OpenAPI](docs/api/openapi.yaml)
- [Roadmap](docs/roadmap.md)
- [ADR: Dedicated server per customer](docs/adr/0001-dedicated-server-per-customer.md)
- [ADR: Device slots and one-time invites](docs/adr/0002-device-slots-and-one-time-invites.md)
- [ADR: IKEv2/strongSwan for Apple-first MVP](docs/adr/0003-ikev2-strongswan-over-wireguard-for-apple-first-mvp.md)

## Static demo

Локально открыть:

```bash
open web_demo/index.html
```

GitHub Pages workflow лежит в `.github/workflows/pages.yml`. Публикация запускается вручную после включения Pages в настройках репозитория. Инструкция: [docs/pages.md](docs/pages.md).

## Быстрый старт

Требования:

- Python 3.9+
- OpenSSL CLI

Проверить тесты:

```bash
make test
```

Создать demo-state:

```bash
python3 -m vpn_control_plane.cli init-demo
```

Создать одноразовую ссылку:

```bash
python3 -m vpn_control_plane.cli create-invite --customer-id demo-customer
```

Активировать ссылку и получить Apple-профиль:

```bash
python3 -m vpn_control_plane.cli activate-invite \
  --token <TOKEN> \
  --platform apple \
  --device-name "Vaka iPhone"
```

Сгенерировать профиль напрямую без state-файла:

```bash
python3 -m vpn_control_plane.cli generate-profile \
  --customer-id demo-customer \
  --slot 1 \
  --platform apple \
  --server-fqdn vpn-demo.example.com \
  --device-name "Test iPhone"
```

Сгенерировать server config для strongSwan:

```bash
make server-config
```

Сгенерировать демо-пакеты:

```bash
make profile-apple
make profile-android
make profile-windows
```

## Принцип анти-шаринга

Один профиль нельзя сделать физически “некопируемым”, потому что `.mobileconfig`, `.sswan` и `PFX` являются файлами. Поэтому контроль делается на уровне identity:

- каждый слот получает уникальный client certificate;
- на сервере включается `unique = keep`;
- один identity может иметь только один активный сеанс;
- если тот же профиль поставили на второе устройство, одновременное подключение второго устройства будет отклонено.

## Структура

```text
docs/                  ТЗ и проектная документация
web_demo/              Static product demo
vpn_control_plane/      Python MVP ядро
tests/                 Unit tests
scripts/               Demo scripts
tools/                 Генератор PDF/HTML из Markdown
.github/workflows/     CI
```
