"""Configuration loader for SQL Sentinel."""

from pathlib import Path
from typing import Any

import yaml

from ..models.errors import ConfigurationError


class ConfigLoader:
    """Loads and parses YAML configuration files."""

    def __init__(self, config_path: str | Path):
        """Initialize the config loader.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)

    def load(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Parsed configuration as a dictionary

        Raises:
            ConfigurationError: If file not found or YAML parsing fails
        """
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")

        if not self.config_path.is_file():
            raise ConfigurationError(f"Configuration path is not a file: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}") from e

        if config is None:
            raise ConfigurationError("Configuration file is empty")

        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a YAML dictionary")

        return config

    def load_from_string(self, yaml_content: str) -> dict[str, Any]:
        """Load configuration from a YAML string.

        Args:
            yaml_content: YAML configuration as a string

        Returns:
            Parsed configuration as a dictionary

        Raises:
            ConfigurationError: If YAML parsing fails
        """
        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}") from e

        if config is None:
            raise ConfigurationError("Configuration content is empty")

        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a YAML dictionary")

        return config
