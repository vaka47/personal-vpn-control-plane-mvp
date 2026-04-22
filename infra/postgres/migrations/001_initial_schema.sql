-- Personal VPN Control Plane MVP schema
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE customer_status AS ENUM ('ACTIVE', 'BLOCKED');
CREATE TYPE subscription_status AS ENUM ('ACTIVE', 'PAST_DUE', 'GRACE', 'SUSPENDED', 'CANCELLED');
CREATE TYPE server_status AS ENUM ('PROVISIONING', 'ACTIVE', 'ERROR', 'SUSPENDED');
CREATE TYPE slot_status AS ENUM ('FREE', 'RESERVED', 'ACTIVE', 'REVOKED');
CREATE TYPE invite_status AS ENUM ('CREATED', 'USED', 'EXPIRED', 'REVOKED', 'FAILED');
CREATE TYPE platform AS ENUM ('apple', 'android', 'windows');

CREATE TABLE customers (
  id text PRIMARY KEY,
  name text NOT NULL,
  contact text NOT NULL DEFAULT '',
  status customer_status NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id text NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  plan text NOT NULL DEFAULT 'family-20',
  paid_until timestamptz,
  grace_until timestamptz,
  status subscription_status NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE servers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id text NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
  provider text NOT NULL DEFAULT 'VDSina',
  region text NOT NULL DEFAULT 'Amsterdam',
  ip inet,
  fqdn text NOT NULL UNIQUE,
  status server_status NOT NULL DEFAULT 'PROVISIONING',
  created_at timestamptz NOT NULL DEFAULT now(),
  provisioned_at timestamptz,
  suspended_at timestamptz
);

CREATE TABLE device_slots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id text NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  server_id uuid NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
  slot_number integer NOT NULL CHECK (slot_number BETWEEN 1 AND 200),
  status slot_status NOT NULL DEFAULT 'FREE',
  platform platform,
  device_name text,
  identity text UNIQUE,
  last_seen_at timestamptz,
  last_ip inet,
  bytes_in bigint NOT NULL DEFAULT 0,
  bytes_out bigint NOT NULL DEFAULT 0,
  duplicate_attempts integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (customer_id, slot_number)
);

CREATE TABLE invite_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id text NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE,
  status invite_status NOT NULL DEFAULT 'CREATED',
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  used_at timestamptz,
  used_by_ip inet,
  slot_id uuid REFERENCES device_slots(id) ON DELETE SET NULL
);

CREATE TABLE certificates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slot_id uuid NOT NULL REFERENCES device_slots(id) ON DELETE CASCADE,
  serial text NOT NULL UNIQUE,
  fingerprint text NOT NULL UNIQUE,
  common_name text NOT NULL,
  issued_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz,
  revoke_reason text
);

CREATE TABLE generated_packages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slot_id uuid NOT NULL REFERENCES device_slots(id) ON DELETE CASCADE,
  package_type platform NOT NULL,
  storage_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  downloaded_at timestamptz
);

CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_type text NOT NULL,
  actor_id text,
  action text NOT NULL,
  target_type text NOT NULL,
  target_id text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_device_slots_customer_status ON device_slots(customer_id, status);
CREATE INDEX idx_invite_tokens_customer_status ON invite_tokens(customer_id, status);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX idx_certificates_slot_id ON certificates(slot_id);

