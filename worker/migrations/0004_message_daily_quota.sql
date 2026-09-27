PRAGMA foreign_keys = ON;

CREATE TABLE wall_daily_post_counts (
  github_id INTEGER NOT NULL,
  day_start INTEGER NOT NULL,
  post_count INTEGER NOT NULL CHECK(post_count BETWEEN 1 AND 10),
  PRIMARY KEY (github_id, day_start),
  FOREIGN KEY (github_id) REFERENCES users(github_id) ON DELETE CASCADE
);

INSERT INTO wall_daily_post_counts (github_id, day_start, post_count)
SELECT
  github_id,
  created_at - (created_at % 86400),
  CASE WHEN COUNT(*) > 10 THEN 10 ELSE COUNT(*) END
FROM wall_messages
GROUP BY github_id, created_at - (created_at % 86400);
