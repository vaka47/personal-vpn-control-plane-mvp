# Local API dashboard

The MVP includes a local HTTP API and browser dashboard implemented with Python standard library only.

Run:

```bash
make serve
```

Open:

```text
http://127.0.0.1:8080
```

## Implemented API routes

- `GET /api/health`
- `GET /api/dashboard?customer_id=demo-customer`
- `GET /api/invites/{token}`
- `POST /api/customers/{customer_id}/invites`
- `POST /api/invites/{token}/activate`
- `POST /api/slots/{slot_id}/revoke`
- `POST /api/admin/customers`
- `POST /api/admin/customers/{customer_id}/server`

## Browser flow

The dashboard can:

- load customer/server/slot state;
- create a one-time invite;
- activate the invite for Apple, Android or Windows;
- generate a profile package;
- revoke an active slot.

Generated artifacts are written to `dist/packages/`.

