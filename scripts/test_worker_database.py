import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "worker" / "migrations"


def migrate(db, include_limits=True):
    db.execute("PRAGMA foreign_keys = ON")
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if not include_limits and path.name.startswith("0006"):
            continue
        db.executescript(path.read_text())
    db.execute("INSERT INTO users VALUES (1, 'user', '', '', 0, 0)")
    db.commit()


def post(db, timestamp):
    db.execute("INSERT INTO wall_messages (github_id, body, created_at) VALUES (1, 'hello', ?)", (timestamp,))
    db.commit()


class MessageLimitTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        migrate(self.db)

    def tearDown(self):
        self.db.close()

    def test_delete_does_not_reset_cooldown(self):
        post(self.db, 1000)
        self.db.execute("DELETE FROM wall_messages")
        self.db.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "wall_post_cooldown"):
            post(self.db, 1001)
        post(self.db, 1030)

    def test_cooldown_spans_midnight(self):
        post(self.db, 86399)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "wall_post_cooldown"):
            post(self.db, 86400)
        post(self.db, 86429)

    def test_daily_limit_survives_deletion_and_resets_on_next_day(self):
        for index in range(10):
            post(self.db, 1000 + index * 30)
        self.db.execute("DELETE FROM wall_messages")
        self.db.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "wall_daily_limit"):
            post(self.db, 1300)
        post(self.db, 86400)

    def test_failed_insert_does_not_consume_quota(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO wall_messages (github_id, body, created_at, parent_id) VALUES (1, 'reply', 1000, 999)")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM wall_post_quotas").fetchone()[0], 0)
        post(self.db, 1000)

    def test_parallel_posts_allow_only_one_message(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "limits.sqlite"
            with sqlite3.connect(path) as db:
                migrate(db)

            def attempt(_):
                with sqlite3.connect(path, timeout=10) as db:
                    db.execute("PRAGMA foreign_keys = ON")
                    try:
                        post(db, 1000)
                        return True
                    except sqlite3.IntegrityError as error:
                        self.assertIn("wall_post_cooldown", str(error))
                        return False

            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(sum(pool.map(attempt, range(20))), 1)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM wall_messages").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT post_count FROM wall_post_quotas").fetchone()[0], 1)

    def test_upgrade_preserves_quota_even_after_messages_were_deleted(self):
        with sqlite3.connect(":memory:") as db:
            migrate(db, include_limits=False)
            db.execute("INSERT INTO wall_daily_post_counts VALUES (1, 0, 9)")
            db.executescript((MIGRATIONS / "0006_atomic_message_limits.sql").read_text())
            post(db, 1000)
            self.assertEqual(db.execute("SELECT post_count FROM wall_post_quotas").fetchone()[0], 10)
            with self.assertRaisesRegex(sqlite3.IntegrityError, "wall_daily_limit"):
                post(db, 1030)

    def test_previous_worker_does_not_double_count_after_migration(self):
        # The previous Worker reserves in wall_daily_post_counts before INSERT.
        # Each subsequent post increments the new atomic counter only once.
        for index in range(10):
            self.db.execute("""INSERT INTO wall_daily_post_counts VALUES (1, 0, 1)
                ON CONFLICT(github_id, day_start) DO UPDATE SET post_count = post_count + 1""")
            post(self.db, 1000 + index * 30)
            self.assertEqual(self.db.execute("SELECT post_count FROM wall_post_quotas").fetchone()[0], index + 1)


if __name__ == "__main__":
    unittest.main()
