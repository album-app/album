CREATE TABLE IF NOT EXISTS catalog_index
(
    name_id INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tag
(
    tag_id          INTEGER PRIMARY KEY,
    name            TEXT not null,
    assignment_type TEXT
);

CREATE TABLE IF NOT EXISTS cover
(
    cover_id    INTEGER PRIMARY KEY,
    solution_id INTEGER not null,
    source      TEXT    not null,
    description TEXT,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id)
);

CREATE TABLE IF NOT EXISTS documentation
(
    documentation_id INTEGER PRIMARY KEY,
    solution_id      INTEGER not null,
    documentation    TEXT,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id)
);

CREATE TABLE IF NOT EXISTS citation
(
    citation_id INTEGER PRIMARY KEY,
    text        TEXT not null,
    doi         TEXT,
    url         TEXT
);

CREATE TABLE IF NOT EXISTS author
(
    author_id INTEGER PRIMARY KEY,
    name      TEXT not null
);

CREATE TABLE IF NOT EXISTS argument
(
    argument_id   INTEGER PRIMARY KEY,
    name          TEXT not null,
    type          TEXT,
    description   TEXT not null,
    default_value TEXT,
    required      INTEGER
);

CREATE TABLE IF NOT EXISTS custom
(
    custom_id         INTEGER PRIMARY KEY,
    custom_key        TEXT not null,
    custom_value      TEXT
);

CREATE TABLE IF NOT EXISTS solution
(
    solution_id       INTEGER PRIMARY KEY,
    "group"           TEXT      not null,
    name              TEXT      not null,
    title             TEXT,
    version           TEXT      not null,
    timestamp         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description       TEXT,
    doi               TEXT,
    license           TEXT,
    album_version     TEXT,
    album_api_version TEXT,
    changelog         TEXT,
    acknowledgement   TEXT,
    hash              TEXT      not null
);

CREATE TABLE IF NOT EXISTS solution_tag
(
    solution_tag_id INTEGER PRIMARY KEY,
    solution_id     INTEGER,
    tag_id          INTEGER,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (tag_id) REFERENCES tag (tag_id)
);

CREATE TABLE IF NOT EXISTS solution_author
(
    solution_author_id INTEGER PRIMARY KEY,
    solution_id        INTEGER,
    author_id          INTEGER,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (author_id) REFERENCES author (author_id)
);

CREATE TABLE IF NOT EXISTS solution_citation
(
    solution_citation_id INTEGER PRIMARY KEY,
    solution_id          INTEGER,
    citation_id          INTEGER,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (citation_id) REFERENCES citation (citation_id)
);

CREATE TABLE IF NOT EXISTS solution_argument
(
    solution_argument_id INTEGER PRIMARY KEY,
    solution_id          INTEGER,
    argument_id          INTEGER,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (argument_id) REFERENCES argument (argument_id)
);


CREATE TABLE IF NOT EXISTS solution_custom
(
    solution_custom_id INTEGER PRIMARY KEY,
    solution_id          INTEGER,
    custom_id          INTEGER,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (custom_id) REFERENCES custom (custom_id)
);
