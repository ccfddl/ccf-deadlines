PRAGMA foreign_keys = ON;

CREATE TABLE wall_message_likes (
  message_id INTEGER NOT NULL,
  github_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  PRIMARY KEY (message_id, github_id),
  FOREIGN KEY (message_id) REFERENCES wall_messages(id) ON DELETE CASCADE,
  FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
);

CREATE INDEX wall_message_likes_user_idx
  ON wall_message_likes(github_id, created_at DESC);
