PRAGMA foreign_keys = ON;

CREATE TABLE wall_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  github_id INTEGER NOT NULL,
  body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
  created_at INTEGER NOT NULL,
  FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
);

CREATE INDEX wall_messages_created_idx
  ON wall_messages(created_at DESC, id DESC);

CREATE INDEX wall_messages_user_created_idx
  ON wall_messages(github_id, created_at DESC);
