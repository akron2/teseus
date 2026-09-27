CREATE TABLE personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    principles_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    created_at TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX messages_conversation_time ON messages(conversation_id, id);

CREATE TABLE memory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL DEFAULT 'owner' CHECK (scope = 'owner'),
    body TEXT NOT NULL CHECK (length(trim(body)) > 0),
    salience INTEGER NOT NULL CHECK (salience BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'forgotten')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    forgotten_at TEXT
);
CREATE INDEX memory_status_salience ON memory_items(status, salience DESC, id);

CREATE TABLE memory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL REFERENCES memory_items(id),
    action TEXT NOT NULL CHECK (action IN ('proposed', 'kept', 'forgotten', 'restored')),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
