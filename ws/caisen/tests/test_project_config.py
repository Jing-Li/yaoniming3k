"""测试 ProjectConfig 全局配置加载"""

from pathlib import Path

from caisen.config.project_config import ProjectConfig


def test_defaults_when_no_config_file(tmp_path):
    """无 project.yaml 时返回内嵌默认值，不报错"""
    config = ProjectConfig.load(project_root=tmp_path)

    assert config.data_dir == "/home/user/data"
    assert config.output_dir == "./runs"
    assert config.api_port == 8001


def test_reads_all_fields_from_project_yaml(tmp_path):
    """完整 project.yaml 时三个字段均被正确读取"""
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "project.yaml").write_text(
        "data_dir: /mnt/data\noutput_dir: /tmp/runs\napi_port: 9000\n",
        encoding="utf-8",
    )

    config = ProjectConfig.load(project_root=tmp_path)

    assert config.data_dir == "/mnt/data"
    assert config.output_dir == "/tmp/runs"
    assert config.api_port == 9000


def test_partial_yaml_uses_defaults_for_missing_fields(tmp_path):
    """project.yaml 部分字段缺失时，缺失字段使用默认值"""
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "project.yaml").write_text(
        "data_dir: /custom/data\n",
        encoding="utf-8",
    )

    config = ProjectConfig.load(project_root=tmp_path)

    assert config.data_dir == "/custom/data"
    assert config.output_dir == "./runs"   # 默认值
    assert config.api_port == 8001          # 默认值
