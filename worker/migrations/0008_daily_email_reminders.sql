ALTER TABLE email_reminders
  ADD COLUMN daily_enabled INTEGER NOT NULL DEFAULT 0 CHECK (daily_enabled IN (0, 1));
