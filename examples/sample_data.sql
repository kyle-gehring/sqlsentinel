-- Sample data for SQL Sentinel demonstration
-- Run this to create test data: sqlite3 examples/sample_data.db < examples/sample_data.sql

-- Orders table for revenue monitoring
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    customer_id INTEGER NOT NULL
);

-- Sample orders data
INSERT INTO orders (date, amount, customer_id) VALUES
    (date('now', '-1 day'), 1250.00, 1),
    (date('now', '-1 day'), 890.50, 2),
    (date('now', '-1 day'), 2100.00, 3),
    (date('now', '-1 day'), 750.25, 4),
    (date('now', '-1 day'), 3200.00, 5),
    (date('now', '-1 day'), 1500.00, 6),
    (date('now', '-1 day'), 425.75, 7),
    (date('now', '-1 day'), 980.00, 8);
-- Total: $11,096.50 (above $10k threshold - should be OK)

-- API logs table for error rate monitoring
CREATE TABLE IF NOT EXISTS api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms INTEGER
);

-- Sample API logs (low error rate)
INSERT INTO api_logs (timestamp, endpoint, status, duration_ms) VALUES
    (datetime('now', '-30 minutes'), '/api/users', 'success', 45),
    (datetime('now', '-29 minutes'), '/api/orders', 'success', 120),
    (datetime('now', '-28 minutes'), '/api/products', 'success', 65),
    (datetime('now', '-27 minutes'), '/api/users', 'error', 5000),
    (datetime('now', '-26 minutes'), '/api/orders', 'success', 98),
    (datetime('now', '-25 minutes'), '/api/products', 'success', 72),
    (datetime('now', '-24 minutes'), '/api/users', 'success', 52),
    (datetime('now', '-23 minutes'), '/api/orders', 'success', 115),
    (datetime('now', '-22 minutes'), '/api/products', 'success', 68),
    (datetime('now', '-21 minutes'), '/api/users', 'success', 48);
-- Error rate: 1/10 = 10% (above 5% threshold - should ALERT)

-- Data pipeline table for freshness monitoring
CREATE TABLE IF NOT EXISTS data_pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    records_processed INTEGER
);

-- Sample pipeline data (fresh data)
INSERT INTO data_pipeline (pipeline_name, updated_at, records_processed) VALUES
    ('customer_sync', datetime('now', '-2 hours'), 1523),
    ('order_sync', datetime('now', '-1 hour'), 892),
    ('product_sync', datetime('now', '-30 minutes'), 456);
-- Last update: 30 minutes ago (under 24 hours - should be OK)
