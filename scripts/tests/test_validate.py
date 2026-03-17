import pytest
from pathlib import Path
import yaml

from scripts.validate import (
    load_conference_yaml_schema,
    validate_single_conference,
    validate_all_conferences,
)


class TestLoadConferenceYamlSchema:
    def test_load_schema_success(self):
        schema = load_conference_yaml_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "items" in schema

    def test_load_schema_not_found(self, tmp_path):
        non_existent = tmp_path / "non_existent.yml"
        with pytest.raises(FileNotFoundError):
            load_conference_yaml_schema(non_existent)


class TestValidateSingleConference:
    @pytest.fixture
    def valid_schema(self):
        return load_conference_yaml_schema()

    @pytest.fixture
    def valid_yaml_content(self):
        return """
- title: CVPR
  description: IEEE Conference on Computer Vision and Pattern Recognition
  sub: AI
  rank:
    ccf: A
  dblp: cvpr
  confs:
    - year: 2025
      id: cvpr25
      link: https://cvpr2025.thecvf.com/
      timeline:
        - deadline: '2025-01-15 23:59:59'
      timezone: UTC-8
      date: June 2025
      place: Seattle, USA
"""

    def test_valid_yaml_file(self, tmp_path, valid_schema, valid_yaml_content):
        yaml_file = tmp_path / "cvpr.yml"
        yaml_file.write_text(valid_yaml_content)
        
        errors = validate_single_conference(yaml_file, valid_schema)
        assert len(errors) == 0

    def test_invalid_yaml_extension(self, tmp_path, valid_schema):
        yaml_file = tmp_path / "cvpr.yaml"
        yaml_file.write_text("test: value")
        
        errors = validate_single_conference(yaml_file, valid_schema)
        assert len(errors) == 1
        assert "should be renamed" in errors[0]

    def test_non_yml_file(self, tmp_path, valid_schema):
        txt_file = tmp_path / "cvpr.txt"
        txt_file.write_text("some content")
        
        errors = validate_single_conference(txt_file, valid_schema)
        assert len(errors) == 0

    def test_invalid_yaml_syntax(self, tmp_path, valid_schema):
        yaml_file = tmp_path / "invalid.yml"
        yaml_file.write_text("invalid: yaml: content: [")
        
        errors = validate_single_conference(yaml_file, valid_schema)
        assert len(errors) == 1
        assert "Invalid YAML" in errors[0]

    def test_schema_validation_failure(self, tmp_path, valid_schema):
        yaml_file = tmp_path / "invalid_schema.yml"
        yaml_file.write_text("""
- title: Test
  sub: INVALID_SUB
  rank:
    ccf: X
  dblp: test
  confs:
    - year: 2025
      id: test25
      link: https://test.com
      timeline:
        - deadline: '2025-01-15 23:59:59'
      timezone: UTC-8
      date: Jan 2025
      place: Test
""")
        
        errors = validate_single_conference(yaml_file, valid_schema)
        assert len(errors) >= 1

    def test_missing_required_field(self, tmp_path, valid_schema):
        yaml_file = tmp_path / "missing_field.yml"
        yaml_file.write_text("""
- title: Test
  sub: AI
  rank:
    ccf: A
  dblp: test
""")
        
        errors = validate_single_conference(yaml_file, valid_schema)
        assert len(errors) >= 1


class TestValidateAllConferences:
    def test_empty_directory(self, tmp_path):
        schema = {"type": "array", "items": {}}
        errors = validate_all_conferences(tmp_path, schema)
        assert len(errors) == 0

    def test_nonexistent_directory(self):
        errors = validate_all_conferences(Path("/nonexistent/path"))
        assert len(errors) == 1
        assert "not found" in errors[0]