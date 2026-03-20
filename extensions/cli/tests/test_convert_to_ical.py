import pytest
from datetime import datetime, timezone
from pathlib import Path

from ccfddl.convert_to_ical import create_vtimezone, convert_to_ical


class TestCreateVtimezone:
    def test_utc_plus_8(self):
        from datetime import timedelta
        tz = timezone(timedelta(hours=8))
        vtz = create_vtimezone(tz)

        assert vtz is not None
        assert vtz.get("TZID") is not None

    def test_utc_minus_5(self):
        from datetime import timedelta
        tz = timezone(timedelta(hours=-5))
        vtz = create_vtimezone(tz)

        tzid = vtz.get("TZID")
        assert tzid is not None
        assert "-05" in str(tzid)


class TestConvertToIcal:
    @pytest.fixture
    def sample_yaml_file(self, tmp_path):
        yaml_content = """
- title: CVPR
  description: IEEE Conference on Computer Vision and Pattern Recognition
  sub: AI
  rank:
    ccf: A
    core: A*
    thcpl: A
  dblp: cvpr
  confs:
    - year: 2025
      id: cvpr25
      link: https://cvpr2025.thecvf.com/
      timeline:
        - deadline: '2025-01-15 23:59:59'
          comment: Main Conference
        - abstract_deadline: '2025-01-08 23:59:59'
      timezone: UTC-8
      date: June 10-14, 2025
      place: Seattle, WA, USA
- title: ICML
  description: International Conference on Machine Learning
  sub: AI
  rank:
    ccf: A
    core: A*
  dblp: icml
  confs:
    - year: 2025
      id: icml25
      link: https://icml.cc/
      timeline:
        - deadline: TBD
      timezone: UTC-8
      date: July 2025
      place: Vienna, Austria
"""
        yaml_file = tmp_path / "test_conf.yml"
        yaml_file.write_text(yaml_content)
        return str(yaml_file)

    def test_convert_to_ical_basic(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.ics")
        sub_mapping = {"AI": "人工智能"}

        convert_to_ical([sample_yaml_file], output_path, lang="en", sub_mapping=sub_mapping)

        assert Path(output_path).exists()

        content = Path(output_path).read_text()
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "CVPR 2025" in content
        assert "CVPR 2025 Deadline" in content or "CVPR 2025 Abstract Deadline" in content

    def test_convert_to_ical_chinese(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output_zh.ics")
        sub_mapping = {"AI": "人工智能"}

        convert_to_ical([sample_yaml_file], output_path, lang="zh", sub_mapping=sub_mapping)

        content = Path(output_path).read_text()
        assert "截稿日期" in content or "摘要截稿" in content

    def test_convert_to_ical_empty_sub_mapping(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output_no_mapping.ics")

        convert_to_ical([sample_yaml_file], output_path, lang="en", sub_mapping=None)

        assert Path(output_path).exists()

    def test_convert_to_ical_multiple_files(self, tmp_path):
        yaml_content1 = """
- title: CVPR
  description: IEEE Conference on Computer Vision and Pattern Recognition
  sub: AI
  rank:
    ccf: A
  dblp: cvpr
  confs:
    - year: 2025
      id: cvpr25
      link: https://example.com
      timeline:
        - deadline: '2025-06-01 12:00:00'
      timezone: UTC+0
      date: June 2025
      place: Test
"""
        yaml_content2 = """
- title: SIGMOD
  description: ACM Conference on Management of Data
  sub: DB
  rank:
    ccf: A
  dblp: sigmod
  confs:
    - year: 2025
      id: sigmod25
      link: https://example.com
      timeline:
        - deadline: '2025-07-01 12:00:00'
      timezone: UTC+0
      date: July 2025
      place: Test
"""
        file1 = tmp_path / "conf1.yml"
        file2 = tmp_path / "conf2.yml"
        file1.write_text(yaml_content1)
        file2.write_text(yaml_content2)

        output_path = str(tmp_path / "multi_output.ics")
        convert_to_ical([str(file1), str(file2)], output_path)

        content = Path(output_path).read_text()
        assert "CVPR 2025" in content
        assert "SIGMOD 2025" in content

    def test_convert_to_ical_skips_tbd(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.ics")

        convert_to_ical([sample_yaml_file], output_path)

        content = Path(output_path).read_text()
        assert "ICML" not in content or "TBD" not in content
