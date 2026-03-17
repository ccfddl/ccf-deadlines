import pytest
from datetime import datetime, timedelta, timezone

from ccfddl.utils import get_timezone, load_mapping, reverse_index


class TestGetTimezone:
    def test_aoe(self):
        tz = get_timezone("AoE")
        expected = timezone(timedelta(hours=-12))
        assert tz == expected

    def test_utc(self):
        tz = get_timezone("UTC")
        assert tz == timezone.utc

    def test_utc_positive(self):
        tz = get_timezone("UTC+8")
        expected = timezone(timedelta(hours=8))
        assert tz == expected

    def test_utc_negative(self):
        tz = get_timezone("UTC-5")
        expected = timezone(timedelta(hours=-5))
        assert tz == expected

    def test_utc_plus_zero(self):
        tz = get_timezone("UTC+0")
        expected = timezone(timedelta(hours=0))
        assert tz == expected

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid timezone format"):
            get_timezone("INVALID")

    def test_invalid_format_no_sign(self):
        with pytest.raises(ValueError, match="Invalid timezone format"):
            get_timezone("UTC8")


class TestLoadMapping:
    def test_load_mapping_file_not_found(self, tmp_path):
        non_existent = tmp_path / "non_existent.yml"
        with pytest.raises(FileNotFoundError):
            load_mapping(str(non_existent))


class TestReverseIndex:
    @pytest.fixture
    def sample_yaml_files(self, tmp_path):
        conf1 = tmp_path / "conf1.yml"
        conf1.write_text("""
- title: CVPR
  sub: AI
  rank:
    ccf: A
    core: A*
    thcpl: A
  dblp: cvpr
  confs:
    - year: 2025
      id: cvpr25
      link: https://cvpr2025.org
      timeline:
        - deadline: '2025-01-15 23:59:59'
      timezone: UTC-8
      date: June 2025
      place: Seattle, USA
""")
        conf2 = tmp_path / "conf2.yml"
        conf2.write_text("""
- title: ICML
  sub: AI
  rank:
    ccf: A
    core: A*
    thcpl: N
  dblp: icml
  confs:
    - year: 2025
      id: icml25
      link: https://icml2025.org
      timeline:
        - deadline: '2025-02-01 23:59:59'
      timezone: UTC-8
      date: July 2025
      place: Vienna, Austria
""")
        return [str(conf1), str(conf2)]

    def test_reverse_index_basic(self, sample_yaml_files):
        index = reverse_index(sample_yaml_files, ["AI"])
        
        assert "AI" in index
        assert len(index["AI"]) == 2
        
        assert "ccf_A" in index
        assert len(index["ccf_A"]) == 2
        
        assert "ccf_A_AI" in index
        
        assert "core_A*" in index
        assert "thcpl_A" in index

    def test_reverse_index_empty_files(self, tmp_path):
        empty_yaml = tmp_path / "empty.yml"
        empty_yaml.write_text("[]")
        index = reverse_index([str(empty_yaml)], ["AI"])
        assert index == {}