# MVP scope

## Входит

- Customer records.
- Server records.
- 20 device slots.
- One-time invite links.
- Apple `.mobileconfig` generation.
- Android `.sswan` generation.
- Windows package generation.
- Dev certificates through OpenSSL.
- StrongSwan config rendering.
- Revoke slot flow.
- Unit tests.

## Не входит

- Реальная аренда VPS через API.
- Production billing.
- Production PKI.
- Mobile apps.
- Anti-detect.
- Residential IP.
- Обход анти-VPN-защит сайтов.
- SLA/high availability.

## Success criteria

- Нельзя активировать одну ссылку дважды.
- Нельзя создать 21-е устройство при лимите 20.
- Revoke переводит слот в заблокированное состояние.
- Профили генерируются автоматически для Apple, Android и Windows.
- StrongSwan config содержит `unique = keep`.

