import pytest
from pathlib import Path
import xml.etree.ElementTree as ET

from ccfddl.convert_to_rss import convert_to_rss


class TestConvertToRss:
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

    def test_convert_to_rss_basic(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")
        sub_mapping = {"AI": "人工智能"}

        convert_to_rss([sample_yaml_file], output_path, lang="en", sub_mapping=sub_mapping)

        assert Path(output_path).exists()

        tree = ET.parse(output_path)
        root = tree.getroot()
        assert root.tag == "rss"
        assert root.get("version") == "2.0"

    def test_convert_to_rss_channel_info(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")

        convert_to_rss([sample_yaml_file], output_path, lang="en")

        tree = ET.parse(output_path)
        channel = tree.find("channel")
        assert channel is not None

        title_elem = channel.find("title")
        link_elem = channel.find("link")
        lang_elem = channel.find("language")

        assert title_elem is not None and title_elem.text == "CCF Conference Deadlines"
        assert link_elem is not None and link_elem.text == "https://ccfddl.com"
        assert lang_elem is not None and lang_elem.text == "en"

    def test_convert_to_rss_chinese(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output_zh.xml")

        convert_to_rss([sample_yaml_file], output_path, lang="zh")

        tree = ET.parse(output_path)
        channel = tree.find("channel")
        assert channel is not None

        title_elem = channel.find("title")
        lang_elem = channel.find("language")

        assert title_elem is not None and title_elem.text == "CCF 会议截止日期"
        assert lang_elem is not None and lang_elem.text == "zh-CN"

    def test_convert_to_rss_items(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")

        convert_to_rss([sample_yaml_file], output_path, lang="en")

        tree = ET.parse(output_path)
        items = tree.findall(".//item")

        assert len(items) >= 1

        first_item = items[0]
        assert first_item.find("title") is not None
        assert first_item.find("link") is not None
        assert first_item.find("description") is not None
        assert first_item.find("guid") is not None

    def test_convert_to_rss_contains_cvpr(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")

        convert_to_rss([sample_yaml_file], output_path, lang="en")

        content = Path(output_path).read_text()
        assert "CVPR 2025" in content

    def test_convert_to_rss_skips_tbd(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")

        convert_to_rss([sample_yaml_file], output_path)

        content = Path(output_path).read_text()
        assert "TBD" not in content or "ICML" not in content

    def test_convert_to_rss_with_comment(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")

        convert_to_rss([sample_yaml_file], output_path, lang="en")

        content = Path(output_path).read_text()
        assert "Main Conference" in content

    def test_convert_to_rss_empty_sub_mapping(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output_no_mapping.xml")

        convert_to_rss([sample_yaml_file], output_path, sub_mapping=None)

        assert Path(output_path).exists()

    def test_convert_to_rss_guid_format(self, sample_yaml_file, tmp_path):
        output_path = str(tmp_path / "test_output.xml")

        convert_to_rss([sample_yaml_file], output_path)

        tree = ET.parse(output_path)
        items = tree.findall(".//item")

        for item in items:
            guid = item.find("guid")
            assert guid is not None
            assert guid.get("isPermaLink") == "false"
            guid_text = guid.text
            assert guid_text is not None
            assert "@ccfddl.com" in guid_text
