CREATE TABLE email_reminders (
  github_id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  timezone TEXT NOT NULL,
  language TEXT NOT NULL CHECK (language IN ('en', 'zh')),
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
);

CREATE TABLE email_digest_sends (
  github_id INTEGER NOT NULL,
  local_date TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'sent')),
  provider_id TEXT,
  created_at INTEGER NOT NULL,
  sent_at INTEGER,
  PRIMARY KEY (github_id, local_date),
  FOREIGN KEY (github_id) REFERENCES email_reminders(github_id) ON DELETE CASCADE
);
