# ADR 0002: Device slots and one-time invites

## Status

Accepted for MVP.

## Context

Giving one VPN file to a customer creates uncontrolled sharing. A copied file cannot reliably identify physical devices.

## Decision

Use `device slots`.

Rules:

- one slot equals one device;
- one slot gets one unique client certificate;
- one invite link activates one slot;
- invite links are one-time and short-lived;
- the default MVP plan has 20 slots.

## Consequences

Benefits:

- sharing is controlled by server-side issuance;
- a copied profile cannot be used concurrently on multiple devices;
- revoke can target one slot without breaking others.

Tradeoffs:

- sequential sharing of one profile cannot be fully prevented without MDM or a device agent;
- users must understand that iPhone, iPad and Mac are three different slots.

