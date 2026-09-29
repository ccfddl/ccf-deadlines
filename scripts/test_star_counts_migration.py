import sqlite3
import unittest
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[1] / "worker" / "migrations"


class StarCountsMigrationTests(unittest.TestCase):
    def test_backfill_and_triggers_track_insert_delete_and_user_cascade(self):
        db = sqlite3.connect(":memory:")
        db.executescript((MIGRATIONS / "0001_initial.sql").read_text())
        db.executemany(
            "INSERT INTO users VALUES (?, ?, '', '', 0, 0)",
            [(1, "one"), (2, "two")],
        )
        db.execute("INSERT INTO conference_stars VALUES ('iclr27', 1, 0)")
        db.executescript((MIGRATIONS / "0009_star_counts.sql").read_text())

        def counts():
            return dict(db.execute("SELECT conference_key, star_count FROM conference_star_counts"))

        self.assertEqual(counts(), {"iclr27": 1})
        db.execute("INSERT OR IGNORE INTO conference_stars VALUES ('iclr27', 1, 0)")
        db.execute("INSERT INTO conference_stars VALUES ('iclr27', 2, 0)")
        db.execute("INSERT INTO conference_stars VALUES ('cvpr27', 2, 0)")
        self.assertEqual(counts(), {"iclr27": 2, "cvpr27": 1})

        db.execute("DELETE FROM conference_stars WHERE conference_key = 'iclr27' AND github_id = 1")
        self.assertEqual(counts(), {"iclr27": 1, "cvpr27": 1})
        db.execute("DELETE FROM users WHERE github_id = 2")
        self.assertEqual(counts(), {})


if __name__ == "__main__":
    unittest.main()
