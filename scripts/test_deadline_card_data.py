import unittest
from pathlib import Path

import yaml

from conference_share_image import DEADLINE_FIELDS, KNOWN_DATE, deadline_card_data


class DeadlineCardDataTests(unittest.TestCase):
    def test_preserves_all_types_rounds_timestamps_and_source_zone(self):
        edition = {'timezone': 'PT', 'timeline': [
            {'abstract_deadline': '2026-03-25 17:00:00', 'deadline': '2026-04-01 17:00:00'},
            {'deadline': 'TBD'},
            {'deadline': '2027-03-01 17:00:00', 'rebuttal_deadline': '2027-04-01 17:00:00', 'decision_deadline': '2027-05-01 17:00:00'}]}
        data = deadline_card_data(edition)
        self.assertEqual(data['timezone'], 'PT')
        self.assertEqual(data['round_count'], 3)
        self.assertEqual([d['round'] for d in data['deadlines']], [1, 1, 3, 3, 3])
        self.assertEqual([d['raw'] for d in data['deadlines']], [
            '2026-03-25 17:00:00', '2026-04-01 17:00:00', '2027-03-01 17:00:00',
            '2027-04-01 17:00:00', '2027-05-01 17:00:00'])

    def test_unknown_dates_are_not_invented(self):
        self.assertEqual(deadline_card_data({'timeline': [{'deadline': 'TBD', 'abstract_deadline': ''}]})['deadlines'], [])
        self.assertEqual(deadline_card_data({})['timezone'], 'Timezone not listed')

    def test_entire_repository_deadline_completeness(self):
        root = Path(__file__).resolve().parent.parent / 'conference'
        maximum = 0
        for path in root.rglob('*.yml'):
            if path.name == 'types.yml':
                continue
            for conference in yaml.safe_load(path.read_text()) or []:
                for edition in conference.get('confs', []):
                    expected = [(i, field, str(point[field]).strip())
                                for i, point in enumerate(edition.get('timeline') or [], 1)
                                for field, _ in DEADLINE_FIELDS
                                if KNOWN_DATE.fullmatch(str(point.get(field) or '').strip())]
                    actual = deadline_card_data(edition)['deadlines']
                    self.assertEqual([(d['round'], d['field'], d['raw']) for d in actual], expected)
                    self.assertLessEqual(len({d['round'] for d in actual}), 12, (conference['title'], edition['year']))
                    maximum = max(maximum, len(actual))
        self.assertGreaterEqual(maximum, 24)


if __name__ == '__main__':
    unittest.main()
