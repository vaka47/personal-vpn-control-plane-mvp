# Roadmap

## Now

- JSON-store MVP.
- CLI control plane.
- Automated Apple, Android and Windows profile generation.
- StrongSwan config template.
- Technical specification and PDF.
- CI tests.
- Static product demo.

## Next without rented server

- Minimal API server around `ControlPlaneService`.
- Admin/customer browser UI connected to local JSON API.
- OpenAPI-generated client.
- More tests for expired invite links and package TTL.
- More detailed production PostgreSQL schema.
- Terraform/Ansible dry-run templates.

## Needs rented server

- Real strongSwan bootstrap.
- Real profile connection test.
- CRL propagation test.
- Metrics collection from live server.
- Load test with several devices.
- Split tunnel validation on Apple devices.

