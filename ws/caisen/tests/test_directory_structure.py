"""目录结构测试"""

import sys
from pathlib import Path

import pytest


class TestDirectoryStructure:
    """ADR-0009 目录结构测试"""

    @pytest.fixture
    def base_path(self):
        """获取项目根目录"""
        # 从 tests/ 目录向上找到项目根目录
        return Path(__file__).parent.parent

    @pytest.fixture
    def caisen_dir(self, base_path):
        """获取 caisen 源码目录"""
        return base_path / "src" / "caisen"

    def test_no_forbidden_directories(self, caisen_dir):
        """禁止的目录不存在"""
        forbidden = {"server"}  # 应使用 web/
        existing = [d for d in forbidden if (caisen_dir / d).exists()]
        assert not existing, f"禁止的目录存在: {existing}"

    def test_allowed_top_directories(self, caisen_dir):
        """顶层目录符合规范"""
        # 允许的顶层目录（参考 ADR-0009）
        allowed = {"core", "strategy", "data", "result", "cli", "llm",
                   "frontend", "web"}  # frontend 和 web 是 visualization 的子目录
        actual = {d.name for d in caisen_dir.iterdir() if d.is_dir() and not d.name.startswith("__")}

        unknown = actual - allowed
        assert not unknown, f"未知目录: {unknown}"

    def test_required_directories_exist(self, caisen_dir):
        """必需目录存在"""
        required = {"core", "strategy", "data", "result", "cli"}
        missing = [d for d in required if not (caisen_dir / d).is_dir()]
        assert not missing, f"缺少目录: {missing}"

    def test_python_files_snake_case(self, caisen_dir):
        """Python 文件使用 snake_case 命名"""
        errors = []
        for py_file in caisen_dir.rglob("*.py"):
            if py_file.name == "__init__.py" or "__pycache__" in str(py_file):
                continue

            name = py_file.stem
            # 允许 _ 前缀（私有模块）和 PascalCase 类文件
            if not name.islower() and not name.startswith("_") and "test_" not in name:
                rel = py_file.relative_to(caisen_dir)
                errors.append(str(rel))

        assert not errors, f"非 snake_case 文件: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])