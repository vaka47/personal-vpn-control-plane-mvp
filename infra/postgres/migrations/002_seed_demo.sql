INSERT INTO customers (id, name, contact)
VALUES ('demo-customer', 'Demo Customer', '@demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO subscriptions (customer_id, plan, paid_until, grace_until, status)
VALUES (
  'demo-customer',
  'family-20',
  now() + interval '30 days',
  now() + interval '33 days',
  'ACTIVE'
);

INSERT INTO servers (customer_id, provider, region, ip, fqdn, status, provisioned_at)
VALUES (
  'demo-customer',
  'VDSina',
  'Amsterdam',
  '203.0.113.10',
  'vpn-demo.example.com',
  'ACTIVE',
  now()
)
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO device_slots (customer_id, server_id, slot_number)
SELECT 'demo-customer', servers.id, slot_number
FROM servers
CROSS JOIN generate_series(1, 20) AS slot_number
WHERE servers.customer_id = 'demo-customer'
ON CONFLICT (customer_id, slot_number) DO NOTHING;

