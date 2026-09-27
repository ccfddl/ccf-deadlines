PRAGMA foreign_keys = ON;

ALTER TABLE wall_messages
  ADD COLUMN parent_id INTEGER REFERENCES wall_messages(id) ON DELETE CASCADE;

CREATE INDEX wall_messages_parent_idx
  ON wall_messages(parent_id, id ASC);
