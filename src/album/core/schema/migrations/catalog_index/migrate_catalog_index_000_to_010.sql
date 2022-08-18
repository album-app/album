CREATE TABLE IF NOT EXISTS test_table (
    spalte_1 INTEGER DEFAULT 0,
    spalte_2 TEXT DEFAULT "default"
);

UPDATE catalog_index
SET version = '0.1.0'
WHERE version = '0.0.0'