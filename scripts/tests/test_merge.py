import pytest
from pathlib import Path

from scripts.merge import find_yml_files, load_yaml_file, merge_yaml_files


class TestFindYmlFiles:
    def test_find_yml_files_basic(self, tmp_path):
        (tmp_path / "file1.yml").write_text("test: 1")
        (tmp_path / "file2.yml").write_text("test: 2")
        (tmp_path / "file3.txt").write_text("test: 3")
        
        files = find_yml_files(tmp_path)
        assert len(files) == 2
        assert all(f.suffix == ".yml" for f in files)

    def test_find_yml_files_exclude(self, tmp_path):
        (tmp_path / "file1.yml").write_text("test: 1")
        (tmp_path / "types.yml").write_text("test: types")
        
        files = find_yml_files(tmp_path, exclude_patterns=["types.yml"])
        assert len(files) == 1
        assert files[0].name == "file1.yml"

    def test_find_yml_files_nested(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.yml").write_text("test: 1")
        (subdir / "file2.yml").write_text("test: 2")
        
        files = find_yml_files(tmp_path)
        assert len(files) == 2

    def test_find_yml_files_empty_directory(self, tmp_path):
        files = find_yml_files(tmp_path)
        assert len(files) == 0

    def test_find_yml_files_multiple_excludes(self, tmp_path):
        (tmp_path / "file1.yml").write_text("test: 1")
        (tmp_path / "types.yml").write_text("test: types")
        (tmp_path / "ignore.yml").write_text("test: ignore")
        
        files = find_yml_files(tmp_path, exclude_patterns=["types.yml", "ignore.yml"])
        assert len(files) == 1
        assert files[0].name == "file1.yml"


class TestLoadYamlFile:
    def test_load_list_yaml(self, tmp_path):
        yaml_file = tmp_path / "list.yml"
        yaml_file.write_text("""
- item1: value1
- item2: value2
""")
        
        data = load_yaml_file(yaml_file)
        assert data is not None
        assert isinstance(data, list)
        assert len(data) == 2

    def test_load_dict_yaml(self, tmp_path):
        yaml_file = tmp_path / "dict.yml"
        yaml_file.write_text("""
key1: value1
key2: value2
""")
        
        data = load_yaml_file(yaml_file)
        assert data is not None
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["key1"] == "value1"

    def test_load_empty_yaml(self, tmp_path):
        yaml_file = tmp_path / "empty.yml"
        yaml_file.write_text("")
        
        data = load_yaml_file(yaml_file)
        assert data == []

    def test_load_invalid_yaml(self, tmp_path, capsys):
        yaml_file = tmp_path / "invalid.yml"
        yaml_file.write_text("invalid: yaml: [")
        
        data = load_yaml_file(yaml_file)
        assert data is None
        
        captured = capsys.readouterr()
        assert "YAML parsing error" in captured.err

    def test_load_nonexistent_file(self, tmp_path, capsys):
        yaml_file = tmp_path / "nonexistent.yml"
        
        data = load_yaml_file(yaml_file)
        assert data is None
        
        captured = capsys.readouterr()
        assert "Error reading" in captured.err


class TestMergeYamlFiles:
    def test_merge_single_file(self, tmp_path):
        yaml_file = tmp_path / "single.yml"
        yaml_file.write_text("""
- name: item1
- name: item2
""")
        
        merged = merge_yaml_files([yaml_file], verbose=False)
        assert len(merged) == 2

    def test_merge_multiple_files(self, tmp_path):
        file1 = tmp_path / "file1.yml"
        file1.write_text("- name: item1")
        
        file2 = tmp_path / "file2.yml"
        file2.write_text("- name: item2")
        
        merged = merge_yaml_files([file1, file2], verbose=False)
        assert len(merged) == 2

    def test_merge_empty_files(self, tmp_path):
        file1 = tmp_path / "empty.yml"
        file1.write_text("")
        
        merged = merge_yaml_files([file1], verbose=False)
        assert len(merged) == 0

    def test_merge_verbose_output(self, tmp_path, capsys):
        yaml_file = tmp_path / "test.yml"
        yaml_file.write_text("- name: test")
        
        merge_yaml_files([yaml_file], verbose=True)
        
        captured = capsys.readouterr()
        assert "Processing" in captured.err