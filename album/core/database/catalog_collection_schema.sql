CREATE TABLE IF NOT EXISTS catalog_collection
(
    name_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS catalog
(
    catalog_id INTEGER,
    name       TEXT,
    src        TEXT,
    path       TEXT,
    deletable  INTEGER not null
);

CREATE TABLE IF NOT EXISTS collection_tag
(
    collection_tag_id INTEGER PRIMARY KEY,
    catalog_id        INTEGER,
    tag_id            INTEGER,
    name              TEXT not null,
    assignment_type   TEXT,
    hash              TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_cover
(
    collection_cover_id INTEGER PRIMARY KEY,
    collection_id       INTEGER,
    catalog_id          INTEGER,
    cover_id            INTEGER,
    source              TEXT not null,
    description         TEXT not null,
    hash                TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
    FOREIGN KEY (collection_id) REFERENCES catalog (collection_id)
);

CREATE TABLE IF NOT EXISTS collection_author
(
    collection_author_id INTEGER PRIMARY KEY,
    catalog_id           INTEGER,
    author_id            INTEGER,
    text                 TEXT not null,
    hash                 TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_citation
(
    collection_citation_id INTEGER PRIMARY KEY,
    catalog_id             INTEGER,
    citation_id            INTEGER,
    text                   TEXT not null,
    doi                    TEXT,
    hash                   TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_argument
(
    collection_argument_id INTEGER PRIMARY KEY,
    catalog_id             INTEGER,
    argument_id            INTEGER,
    name                   TEXT not null,
    type                   TEXT not null,
    description            TEXT,
    default_value          TEXT,
    hash                   TEXT not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection
(
    collection_id        INTEGER PRIMARY KEY,
    solution_id          INTEGER,
    "group"              TEXT      not null,
    name                 TEXT      not null,
    title                TEXT,
    version              TEXT      not null,
    format_version       TEXT,
    timestamp            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description          TEXT,
    doi                  TEXT,
    git_repo             TEXT,
    license              TEXT,
    documentation        TEXT,
    min_album_version    TEXT,
    tested_album_version TEXT,
    parent               TEXT,
    changelog            TEXT,
    hash                 TEXT,
    install_date         TEXT,
    last_execution       TEXT,
    installed            INTEGER   not null,
    catalog_id           INTEGER   not null,
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_solution_tag
(
    collection_solution_tag_id INTEGER PRIMARY KEY,
    collection_id              INTEGER,
    collection_tag_id          INTEGER,
    solution_tag_id            INTEGER,
    solution_id                INTEGER,
    tag_id                     INTEGER,
    catalog_id                 INTEGER,
    hash                       TEXT not null,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (collection_tag_id) REFERENCES collection_tag (tag_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_solution_author
(
    collection_solution_author_id INTEGER PRIMARY KEY,
    collection_id                 INTEGER,
    collection_author_id          INTEGER,
    solution_author_id            INTEGER,
    solution_id                   INTEGER,
    author_id                     INTEGER,
    catalog_id                    INTEGER,
    hash                          TEXT not null,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (collection_author_id) REFERENCES collection_author (collection_author_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_solution_citation
(
    collection_solution_citation_id INTEGER PRIMARY KEY,
    collection_id                   INTEGER,
    collection_citation_id          INTEGER,
    solution_citation_id            INTEGER,
    solution_id                     INTEGER,
    citation_id                     INTEGER,
    catalog_id                      INTEGER,
    hash                            TEXT not null,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (collection_citation_id) REFERENCES collection_citation (collection_citation_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);

CREATE TABLE IF NOT EXISTS collection_solution_argument
(
    collection_solution_argument_id INTEGER PRIMARY KEY,
    collection_id                   INTEGER,
    collection_argument_id          INTEGER,
    solution_argument_id            INTEGER,
    solution_id                     INTEGER,
    argument_id                     INTEGER,
    catalog_id                      INTEGER,
    hash                            TEXT not null,
    FOREIGN KEY (collection_id) REFERENCES collection (collection_id),
    FOREIGN KEY (collection_argument_id) REFERENCES collection_argument (collection_argument_id),
    FOREIGN KEY (catalog_id) REFERENCES catalog (catalog_id)
);
