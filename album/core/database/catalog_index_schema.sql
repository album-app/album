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
    assignment_type TEXT,
    hash            TEXT not null
);

CREATE TABLE IF NOT EXISTS cover
(
    cover_id        INTEGER PRIMARY KEY,
    solution_id     INTEGER not null,
    source          TEXT not null,
    description     TEXT,
    hash            TEXT not null,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id)
);

CREATE TABLE IF NOT EXISTS citation
(
    citation_id     INTEGER PRIMARY KEY,
    text            TEXT not null,
    doi             TEXT,
    hash            TEXT not null
);

CREATE TABLE IF NOT EXISTS author
(
    author_id     INTEGER PRIMARY KEY,
    text            TEXT not null,
    hash            TEXT not null
);

CREATE TABLE IF NOT EXISTS argument
(
    argument_id     INTEGER PRIMARY KEY,
    name            TEXT not null,
    type            TEXT not null,
    description     TEXT,
    default_value   TEXT,
    hash            TEXT not null
);

CREATE TABLE IF NOT EXISTS solution
(
    solution_id          INTEGER PRIMARY KEY,
    "group"              TEXT      not null,
    name                 TEXT      not null,
    title                TEXT      not null,
    version              TEXT      not null,
    format_version       TEXT,
    timestamp            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description          TEXT,
    doi                  TEXT,
    git_repo             TEXT,
    license              TEXT,
    documentation        TEXT,
    min_album_version    TEXT,
    tested_album_version TEXT,
    parent               TEXT,
    changelog            TEXT,
    hash                 TEXT not null
);

CREATE TABLE IF NOT EXISTS solution_tag
(
    solution_tag_id INTEGER PRIMARY KEY,
    solution_id     INTEGER,
    tag_id          INTEGER,
    hash            TEXT not null,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (tag_id) REFERENCES tag (tag_id)
);

CREATE TABLE IF NOT EXISTS solution_author
(
    solution_author_id INTEGER PRIMARY KEY,
    solution_id        INTEGER,
    author_id          INTEGER,
    hash               TEXT not null,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (author_id) REFERENCES author (author_id)
);

CREATE TABLE IF NOT EXISTS solution_citation
(
    solution_citation_id INTEGER PRIMARY KEY,
    solution_id          INTEGER,
    citation_id          INTEGER,
    hash                 TEXT not null,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (citation_id) REFERENCES citation (citation_id)
);

CREATE TABLE IF NOT EXISTS solution_argument
(
    solution_argument_id INTEGER PRIMARY KEY,
    solution_id          INTEGER,
    argument_id          INTEGER,
    hash                 TEXT not null,
    FOREIGN KEY (solution_id) REFERENCES solution (solution_id),
    FOREIGN KEY (argument_id) REFERENCES argument (argument_id)
);
