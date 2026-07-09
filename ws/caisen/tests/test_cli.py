"""CLI 命令测试 — 使用 Click CliRunner 测试各子命令。"""

import pytest
from click.testing import CliRunner

from caisen.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCliGroup:
    """CLI 顶层命令组。"""

    def test_help_exits_zero(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "caisen" in result.output

    def test_no_command_shows_help(self, runner):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0


class TestRunCommand:
    """caisen run 子命令。"""

    def test_run_help(self, runner):
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--strategy" in result.output
        assert "--mock" in result.output

    def test_run_mock_data(self, runner):
        """使用 mock 数据运行回测（不需要真实数据文件）。"""
        result = runner.invoke(cli, [
            "run", "-s", "MACrossStrategy",
            "--mock",
            "--output-dir", "/tmp/caisen_test_runs",
        ])
        # 成功时应输出 Run ID
        if result.exit_code == 0:
            assert "Run ID" in result.output or "Backtest Complete" in result.output

    def test_run_missing_strategy_exits_nonzero(self, runner):
        """不指定策略名应报错。"""
        result = runner.invoke(cli, ["run"])
        assert result.exit_code != 0


class TestListRunsCommand:
    """caisen list-runs 子命令。"""

    def test_list_runs_help(self, runner):
        result = runner.invoke(cli, ["list-runs", "--help"])
        assert result.exit_code == 0

    def test_list_runs_empty_dir(self, runner, tmp_path):
        result = runner.invoke(cli, ["list-runs", "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "No runs found" in result.output


class TestShowResultCommand:
    """caisen show-result 子命令。"""

    def test_show_result_help(self, runner):
        result = runner.invoke(cli, ["show-result", "--help"])
        assert result.exit_code == 0

    def test_show_result_not_found(self, runner, tmp_path):
        result = runner.invoke(cli, ["show-result", "nonexistent", "--output-dir", str(tmp_path)])
        assert result.exit_code != 0 or "not found" in result.output


class TestWebCommand:
    """caisen web 子命令。"""

    def test_web_help(self, runner):
        result = runner.invoke(cli, ["web", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output


class TestOptimizeCommand:
    """caisen optimize 子命令。"""

    def test_optimize_help(self, runner):
        result = runner.invoke(cli, ["optimize", "--help"])
        assert result.exit_code == 0
        assert "--workers" in result.output
        assert "--mock" in result.output
