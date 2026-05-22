"""目录结构检查脚本

检查 src/caisen/ 下的目录结构是否符合 ADR-0009 标准。

用法:
    python -m caisen.lint_structure
    或
    pytest tests/test_directory_structure.py
"""

import sys
from pathlib import Path


# 允许的顶层目录
ALLOWED_TOP_DIRS = {
    "core", "strategy", "data", "result", "cli", "llm",
    "frontend", "web",  # visualization 的子目录放在顶层
}

# 禁止的目录名（已废弃或非标准）
FORBIDDEN_DIRS = {
    "server",  # 改为 web/
}


def check_directory_structure(base_path: Path) -> list[str]:
    """检查目录结构，返回错误列表"""
    errors = []

    caisen_dir = base_path / "src" / "caisen"
    if not caisen_dir.exists():
        return ["错误: src/caisen/ 目录不存在"]

    # 检查禁止的目录
    for forbidden in FORBIDDEN_DIRS:
        if (caisen_dir / forbidden).exists():
            errors.append(f"禁止的目录: {forbidden}/ (使用 'web/' 替代)")

    # 检查顶层目录
    actual_dirs = [d.name for d in caisen_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]

    for actual_dir in actual_dirs:
        if actual_dir not in ALLOWED_TOP_DIRS:
            errors.append(f"未知目录: {actual_dir}/ (期望: {', '.join(sorted(ALLOWED_TOP_DIRS))})")

    # 检查必须存在的目录
    required_dirs = {"core", "strategy", "data", "result", "cli"}
    missing_dirs = required_dirs - set(actual_dirs)
    if missing_dirs:
        errors.append(f"缺少必需目录: {', '.join(missing_dirs)}")

    return errors


def check_naming_conventions(base_path: Path) -> list[str]:
    """检查命名规范，返回错误列表"""
    errors = []

    caisen_dir = base_path / "src" / "caisen"

    for py_file in caisen_dir.rglob("*.py"):
        # 跳过 __init__.py 和 __pycache__
        if py_file.name == "__init__.py" or "__pycache__" in str(py_file):
            continue

        # 检查文件名是否符合 snake_case
        name_without_ext = py_file.stem
        if not name_without_ext.islower() and not name_without_ext.startswith("_"):
            rel_path = py_file.relative_to(base_path)
            errors.append(f"文件命名错误: {rel_path} (应使用 snake_case)")

    return errors


def run_checks(base_path: Path = None) -> bool:
    """运行所有检查，返回是否全部通过"""
    if base_path is None:
        base_path = Path(__file__).parent.parent.parent

    print("=" * 60)
    print("目录结构检查 (ADR-0009)")
    print("=" * 60)

    all_errors = []

    # 检查目录结构
    print("\n[1/2] 检查目录结构...")
    dir_errors = check_directory_structure(base_path)
    if dir_errors:
        all_errors.extend(dir_errors)
        for err in dir_errors:
            print(f"  ✗ {err}")
    else:
        print("  ✓ 目录结构正常")

    # 检查命名规范
    print("\n[2/2] 检查命名规范...")
    name_errors = check_naming_conventions(base_path)
    if name_errors:
        all_errors.extend(name_errors)
        for err in name_errors[:5]:  # 只显示前5个
            print(f"  ✗ {err}")
        if len(name_errors) > 5:
            print(f"  ... 还有 {len(name_errors) - 5} 个错误")
    else:
        print("  ✓ 命名规范正常")

    print("\n" + "=" * 60)
    if all_errors:
        print(f"检查失败: {len(all_errors)} 个错误")
        return False
    else:
        print("检查通过 ✓")
        return True


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)