"""Tests for the labpipe command-line interface."""

import pytest

from labpipe import __version__
from labpipe.cli import main


def test_version_subcommand_prints_version(capsys):
    exit_code = main(["version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == f"labpipe {__version__}"


def test_version_flag_prints_version_and_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_command_prints_help_and_returns_1(capsys):
    exit_code = main([])
    assert exit_code == 1
    assert "usage: labpipe" in capsys.readouterr().out


def test_unknown_command_is_rejected(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["not-a-command"])
    assert exc_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
