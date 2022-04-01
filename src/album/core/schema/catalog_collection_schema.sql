CREATE TABLE IF NOT EXISTS catalog_collection
(
    name_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog
(
    catalog_id   INTEGER,
    name         TEXT,
    src          TEXT,
    path         TEXT,
    branch_name  TEXT,
    type         TEXT,
    deletable    INTEGER not null
);

CREATE TABLE IF NOT EXISTS tag
(
    tag_id          INTEGER PRIMARY KEY,
    catalog_id      INTEGER,
    name            TEXT not null,
    assignment_type TEXT,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS cover
(
    cover_id      INTEGER PRIMARY KEY,
    collection_id INTEGER,
    catalog_id    INTEGER,
    source        TEXT not null,
    description   TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id),
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id)
);

CREATE TABLE IF NOT EXISTS documentation
(
    documentation_id INTEGER PRIMARY KEY,
    collection_id    INTEGER,
    catalog_id       INTEGER,
    documentation    TEXT,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id),
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id)
);

CREATE TABLE IF NOT EXISTS author
(
    author_id  INTEGER PRIMARY KEY,
    catalog_id INTEGER,
    name       TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS citation
(
    citation_id INTEGER PRIMARY KEY,
    catalog_id  INTEGER,
    text        TEXT not null,
    doi         TEXT,
    url         TEXT,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS argument
(
    argument_id   INTEGER PRIMARY KEY,
    catalog_id    INTEGER,
    name          TEXT not null,
    type          TEXT,
    description   TEXT,
    default_value TEXT,
    required      INTEGER,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS custom
(
    custom_id       INTEGER PRIMARY KEY,
    catalog_id      INTEGER,
    custom_key      TEXT not null,
    custom_value    TEXT,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection
(
    collection_id            INTEGER PRIMARY KEY,
    solution_id              INTEGER,
    "group"                  TEXT    not null,
    name                     TEXT    not null,
    title                    TEXT,
    version                  TEXT    not null,
    timestamp                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description              TEXT,
    doi                      TEXT,
    license                  TEXT,
    album_version            TEXT,
    album_api_version        TEXT,
    changelog                TEXT,
    acknowledgement          TEXT,
    hash                     TEXT    not null,
    install_date             TEXT,
    last_execution           TEXT,
    installation_unfinished  INTEGER not null,
    installed                INTEGER not null,
    catalog_id               INTEGER not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_collection
(
    collection_collection_id INTEGER PRIMARY KEY,
    collection_id_parent     INTEGER,
    collection_id_child      INTEGER,
    catalog_id_parent        INTEGER,
    catalog_id_child         INTEGER,
    FOREIGN KEY (collection_id_parent) REFERENCES collection (collection_id),
    FOREIGN KEY (collection_id_child) REFERENCES collection (collection_id),
    FOREIGN KEY (catalog_id_parent) REFERENCES catalog (catalog_id),
    FOREIGN KEY (catalog_id_child) REFERENCES catalog (catalog_id)

);

CREATE TABLE IF NOT EXISTS collection_tag
(
    collection_tag_id INTEGER PRIMARY KEY,
    collection_id     INTEGER,
    tag_id            INTEGER,
    catalog_id        INTEGER,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (tag_id) REFERENCES tag (tag_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_author
(
    collection_author_id INTEGER PRIMARY KEY,
    collection_id        INTEGER,
    author_id            INTEGER,
    catalog_id           INTEGER,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (author_id) REFERENCES author (author_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_citation
(
    collection_citation_id INTEGER PRIMARY KEY,
    collection_id          INTEGER,
    citation_id            INTEGER,
    catalog_id             INTEGER,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (citation_id) REFERENCES citation (citation_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_argument
(
    collection_argument_id INTEGER PRIMARY KEY,
    collection_id          INTEGER,
    argument_id            INTEGER,
    catalog_id             INTEGER,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (argument_id) REFERENCES argument (argument_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_custom
(
    collection_custom_id INTEGER PRIMARY KEY,
    collection_id          INTEGER,
    custom_id            INTEGER,
    catalog_id             INTEGER,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (custom_id) REFERENCES custom (custom_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

