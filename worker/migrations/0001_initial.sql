PRAGMA foreign_keys = ON;

CREATE TABLE users (
  github_id INTEGER PRIMARY KEY,
  login TEXT NOT NULL,
  avatar_url TEXT NOT NULL,
  profile_url TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  github_id INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
);

CREATE INDEX sessions_expiration_idx ON sessions(expires_at);
CREATE INDEX sessions_user_idx ON sessions(github_id);

CREATE TABLE conference_stars (
  conference_key TEXT NOT NULL,
  github_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (conference_key, github_id),
  FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
);

CREATE INDEX conference_stars_user_idx ON conference_stars(github_id);
