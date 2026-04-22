# ADR 0001: Dedicated server per customer

## Status

Accepted for MVP.

## Context

The product promise is a personal VPN, not a shared public VPN. The customer pays for a dedicated setup and can invite a limited number of devices.

## Decision

Use one dedicated VPS per paying customer.

## Consequences

Benefits:

- isolation between customers;
- simple abuse handling;
- clear economics;
- easier explanation for non-technical users;
- customer-specific suspend, revoke and migration.

Tradeoffs:

- higher infrastructure cost per customer;
- provisioning automation becomes important after MVP;
- monitoring must track many small servers.

