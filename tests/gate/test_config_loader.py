from pathlib import Path
import pytest
from pydantic import ValidationError

from src.gate.config import load_config


FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_valid_yaml():
    cfg = load_config(FIXTURES / "minimal.yaml")
    assert "greeting" in cfg.categories


def test_malformed_yaml_raises():
    bad = FIXTURES / "not_a_file.yaml"
    with pytest.raises(FileNotFoundError):
        load_config(bad)
