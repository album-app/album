CREATE TABLE IF NOT EXISTS test_table2 (
    spalte_1 INTEGER DEFAULT 0,
    spalte_2 TEXT DEFAULT "default"
);
UPDATE catalog_collection
SET version = '0.1.0'
WHERE name = 'album_collection'