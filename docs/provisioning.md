# Provisioning dry-run

This repository does not require a rented server. Provisioning files are included as a dry-run foundation for the future live VPS setup.

## Bash bootstrap

Run locally without changing the machine:

```bash
make provision-dry-run
```

The script prints the strongSwan installation and firewall plan. On a real server, set:

```bash
DRY_RUN=0 scripts/bootstrap_strongswan.sh
```

## Ansible

Files:

- `infra/ansible/playbook.yml`
- `infra/ansible/inventory.example.ini`
- `infra/ansible/templates/swanctl.conf.j2`

Dry-run by default:

```bash
ansible-playbook -i infra/ansible/inventory.example.ini infra/ansible/playbook.yml
```

Apply on a real server only after reviewing variables and certificates:

```bash
ansible-playbook -i inventory.ini infra/ansible/playbook.yml -e dry_run=false
```

## PostgreSQL schema

Migrations:

- `infra/postgres/migrations/001_initial_schema.sql`
- `infra/postgres/migrations/002_seed_demo.sql`

The current Python MVP uses JSON storage, but the SQL schema mirrors the product data model for a production backend.

