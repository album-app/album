CREATE TABLE IF NOT EXISTS test_table (
    spalte_1 INTEGER DEFAULT 0,
    spalte_2 TEXT DEFAULT "default"
);
UPDATE catalog_collection
SET version = '0.0.1'
WHERE name = 'album_collection'