CREATE TABLE conference_star_counts (
  conference_key TEXT PRIMARY KEY,
  star_count INTEGER NOT NULL CHECK (star_count >= 0)
);

INSERT INTO conference_star_counts (conference_key, star_count)
SELECT conference_key, COUNT(*)
FROM conference_stars
GROUP BY conference_key;

CREATE TRIGGER conference_star_counts_after_insert
AFTER INSERT ON conference_stars
BEGIN
  INSERT INTO conference_star_counts (conference_key, star_count)
  VALUES (NEW.conference_key, 1)
  ON CONFLICT(conference_key) DO UPDATE SET star_count = star_count + 1;
END;

CREATE TRIGGER conference_star_counts_after_delete
AFTER DELETE ON conference_stars
BEGIN
  UPDATE conference_star_counts
  SET star_count = star_count - 1
  WHERE conference_key = OLD.conference_key;
  DELETE FROM conference_star_counts
  WHERE conference_key = OLD.conference_key AND star_count = 0;
END;
