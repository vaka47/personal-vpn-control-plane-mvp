# ADR 0003: IKEv2/strongSwan over WireGuard for Apple-first MVP

## Status

Accepted for MVP.

## Context

WireGuard is simple and fast, but it requires a WireGuard client app and does not support the desired Apple UX of opening a system configuration profile.

The MVP should make iPhone, iPad and Mac setup feel native.

## Decision

Use IKEv2 with strongSwan for the MVP.

## Consequences

Benefits:

- native Apple `.mobileconfig` setup;
- certificate-based authentication;
- device-level revoke;
- On Demand VPN support;
- split tunnel support.

Tradeoffs:

- Android needs strongSwan VPN Client;
- Windows setup needs PFX import and a PowerShell script;
- strongSwan configuration is more complex than WireGuard.

