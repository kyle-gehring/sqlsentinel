"""Tests for ConfigLoader."""

import os
import tempfile
from pathlib import Path

import pytest
from sqlsentinel.config.loader import ConfigLoader
from sqlsentinel.models.errors import ConfigurationError


class TestConfigLoader:
    """Test suite for ConfigLoader."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_path = Path(__file__).parent / "fixtures" / "valid_config.yaml"
        loader = ConfigLoader(config_path)
        config = loader.load()

        assert "alerts" in config
        assert isinstance(config["alerts"], list)
        assert len(config["alerts"]) == 1
        assert config["alerts"][0]["name"] == "Low Daily Revenue"

    def test_load_multi_alert_config(self):
        """Test loading a configuration with multiple alerts."""
        config_path = Path(__file__).parent / "fixtures" / "multi_alert_config.yaml"
        loader = ConfigLoader(config_path)
        config = loader.load()

        assert "alerts" in config
        assert len(config["alerts"]) == 2
        assert config["alerts"][0]["name"] == "Revenue Alert"
        assert config["alerts"][1]["name"] == "Data Quality Check"

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file raises error."""
        loader = ConfigLoader("/nonexistent/path/config.yaml")
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            loader.load()

    def test_load_directory_instead_of_file(self):
        """Test loading a directory raises error."""
        config_path = Path(__file__).parent / "fixtures"
        loader = ConfigLoader(config_path)
        with pytest.raises(ConfigurationError, match="not a file"):
            loader.load()

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:\n  - bad indentation")
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            with pytest.raises(ConfigurationError, match="Failed to parse YAML"):
                loader.load()
        finally:
            Path(temp_path).unlink()

    def test_load_empty_file(self):
        """Test loading an empty file raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            with pytest.raises(ConfigurationError, match="Configuration file is empty"):
                loader.load()
        finally:
            Path(temp_path).unlink()

    def test_load_non_dict_yaml(self):
        """Test loading YAML that's not a dictionary raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("- just\n- a\n- list")
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            with pytest.raises(ConfigurationError, match="must be a YAML dictionary"):
                loader.load()
        finally:
            Path(temp_path).unlink()

    def test_load_from_string_valid(self):
        """Test loading valid YAML from string."""
        yaml_content = """
alerts:
  - name: "Test Alert"
    query: "SELECT 'OK' as status"
    schedule: "0 * * * *"
"""
        loader = ConfigLoader("/dummy/path")
        config = loader.load_from_string(yaml_content)

        assert "alerts" in config
        assert config["alerts"][0]["name"] == "Test Alert"

    def test_load_from_string_invalid_yaml(self):
        """Test loading invalid YAML from string raises error."""
        yaml_content = "invalid: yaml: content:\n  - bad"
        loader = ConfigLoader("/dummy/path")
        with pytest.raises(ConfigurationError, match="Failed to parse YAML"):
            loader.load_from_string(yaml_content)

    def test_load_from_string_empty(self):
        """Test loading empty string raises error."""
        loader = ConfigLoader("/dummy/path")
        with pytest.raises(ConfigurationError, match="Configuration content is empty"):
            loader.load_from_string("")

    def test_load_from_string_non_dict(self):
        """Test loading non-dict YAML from string raises error."""
        yaml_content = "- just a list"
        loader = ConfigLoader("/dummy/path")
        with pytest.raises(ConfigurationError, match="must be a YAML dictionary"):
            loader.load_from_string(yaml_content)

    def test_env_var_substitution_in_file(self, monkeypatch):
        """Test that ${VAR} placeholders are expanded from environment variables."""
        monkeypatch.setenv("TEST_RECIPIENT", "test@example.com")
        yaml_content = """
alerts:
  - name: "Env Var Alert"
    query: "SELECT 'OK' as status"
    schedule: "0 * * * *"
    notify:
      - channel: email
        recipients: ["${TEST_RECIPIENT}"]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()
            assert config["alerts"][0]["notify"][0]["recipients"] == ["test@example.com"]
        finally:
            Path(temp_path).unlink()

    def test_env_var_substitution_in_string(self, monkeypatch):
        """Test that ${VAR} placeholders are expanded in load_from_string."""
        monkeypatch.setenv("TEST_WEBHOOK", "https://hooks.slack.com/test")
        yaml_content = """
alerts:
  - name: "Env Var Alert"
    query: "SELECT 'OK' as status"
    schedule: "0 * * * *"
    notify:
      - channel: slack
        webhook_url: "${TEST_WEBHOOK}"
"""
        loader = ConfigLoader("/dummy/path")
        config = loader.load_from_string(yaml_content)
        assert config["alerts"][0]["notify"][0]["webhook_url"] == "https://hooks.slack.com/test"
