ALTER TABLE wall_daily_post_counts
  ADD COLUMN last_post_at INTEGER NOT NULL DEFAULT 0;

UPDATE wall_daily_post_counts
SET last_post_at = COALESCE((
  SELECT MAX(created_at) FROM wall_messages
  WHERE wall_messages.github_id = wall_daily_post_counts.github_id
    AND created_at >= day_start AND created_at < day_start + 86400
), 0);

-- A single INSERT is transactional: concurrent posts cannot bypass cooldown or
-- daily limits, deletion cannot reset them, and failed posts consume no quota.
CREATE TRIGGER wall_post_limits BEFORE INSERT ON wall_messages
BEGIN
  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM wall_daily_post_counts
    WHERE github_id = NEW.github_id AND last_post_at > NEW.created_at - 30
  ) THEN RAISE(ABORT, 'wall_post_cooldown') END;

  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM wall_daily_post_counts
    WHERE github_id = NEW.github_id
      AND day_start = NEW.created_at - (NEW.created_at % 86400)
      AND post_count >= 10
  ) THEN RAISE(ABORT, 'wall_daily_limit') END;

  INSERT INTO wall_daily_post_counts (github_id, day_start, post_count, last_post_at)
  VALUES (NEW.github_id, NEW.created_at - (NEW.created_at % 86400), 1, NEW.created_at)
  ON CONFLICT(github_id, day_start) DO UPDATE SET
    post_count = post_count + 1,
    last_post_at = NEW.created_at;
END;
