"""Agent configuration loader.

Loads YAML agent configuration files and validates them against Pydantic
models. The loader ensures that any configuration error is caught at startup,
not during a live call.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.config.agent_config import AgentConfig


def load_agent_config(config_path: str | Path) -> AgentConfig:
    """Load and validate an agent configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Validated AgentConfig instance.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the file contains invalid YAML.
        pydantic.ValidationError: If the config doesn't match the schema.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Agent config not found: {path}")

    with open(path) as f:
        raw_config = yaml.safe_load(f)

    if not isinstance(raw_config, dict):
        raise ValueError(f"Agent config must be a YAML mapping, got {type(raw_config)}")

    return AgentConfig.model_validate(raw_config)


def load_all_agent_configs(agents_dir: str | Path) -> dict[str, AgentConfig]:
    """Load all agent configurations from a directory.

    Args:
        agents_dir: Path to directory containing YAML agent config files.

    Returns:
        Dictionary mapping agent_id to validated AgentConfig.

    Raises:
        FileNotFoundError: If the directory doesn't exist.
    """
    directory = Path(agents_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Agents directory not found: {directory}")

    configs: dict[str, AgentConfig] = {}
    for yaml_file in sorted(directory.glob("*.yaml")):
        config = load_agent_config(yaml_file)
        configs[config.agent_id] = config

    return configs
