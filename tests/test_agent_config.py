"""Tests for agent config models and YAML loader.

Covers:
- Pydantic model validation (AgentConfig, AgentState, DataPointSchema)
- Config loading from YAML files
- Validation errors for bad configs (missing states, broken references)
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from src.config.agent_config import (
    AgentConfig,
    AgentState,
    AgentTransition,
    ComplianceCheckpoint,
    DataPointSchema,
    DataPointType,
    FailureAction,
    PIILevel,
    VoiceConfig,
)
from src.config.loader import load_agent_config, load_all_agent_configs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_config(**overrides: object) -> dict:
    """Build a minimal valid config dict."""
    base = {
        "agent_id": "test_agent_v1",
        "agent_name": "Test Agent",
        "version": "1.0",
        "initial_state": "GREETING",
        "system_prompt_template": "prompts/test.md",
        "states": {
            "GREETING": {"name": "GREETING", "is_terminal": True},
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# AgentConfig model validation
# ---------------------------------------------------------------------------

class TestAgentConfigValidation:
    """Tests for AgentConfig Pydantic validation."""

    def test_minimal_valid_config(self) -> None:
        config = AgentConfig(**_minimal_config())
        assert config.agent_id == "test_agent_v1"
        assert config.initial_state == "GREETING"
        assert "GREETING" in config.states

    def test_defaults_populated(self) -> None:
        config = AgentConfig(**_minimal_config())
        assert config.description == ""
        assert config.data_schema == []
        assert config.compliance_checkpoints == []
        assert config.metadata == {}
        assert isinstance(config.voice_config, VoiceConfig)

    def test_invalid_initial_state_raises(self) -> None:
        with pytest.raises(ValueError, match="initial_state.*not found"):
            AgentConfig(**_minimal_config(initial_state="NONEXISTENT"))

    def test_no_terminal_state_raises(self) -> None:
        with pytest.raises(ValueError, match="terminal state"):
            AgentConfig(**_minimal_config(
                states={"GREETING": {"name": "GREETING", "is_terminal": False}},
            ))

    def test_transition_to_unknown_state_raises(self) -> None:
        states = {
            "GREETING": {
                "name": "GREETING",
                "is_terminal": False,
                "transitions": [{"trigger": "next", "target_state": "MISSING_STATE"}],
            },
            "END": {"name": "END", "is_terminal": True},
        }
        with pytest.raises(ValueError, match="unknown state.*MISSING_STATE"):
            AgentConfig(**_minimal_config(states=states))

    def test_data_points_to_collect_validates_against_schema(self) -> None:
        states = {
            "GREETING": {
                "name": "GREETING",
                "is_terminal": True,
                "data_points_to_collect": ["nonexistent_field"],
            },
        }
        with pytest.raises(ValueError, match="unknown data field.*nonexistent_field"):
            AgentConfig(**_minimal_config(states=states))

    def test_data_points_to_collect_valid(self) -> None:
        states = {
            "GREETING": {
                "name": "GREETING",
                "is_terminal": True,
                "data_points_to_collect": ["name"],
            },
        }
        schema = [{"field_name": "name", "type": "string"}]
        config = AgentConfig(**_minimal_config(states=states, data_schema=schema))
        assert config.states["GREETING"].data_points_to_collect == ["name"]

    def test_multiple_states_with_transitions(self) -> None:
        states = {
            "GREETING": {
                "name": "GREETING",
                "is_terminal": False,
                "transitions": [{"trigger": "identified", "target_state": "VERIFY"}],
            },
            "VERIFY": {
                "name": "VERIFY",
                "is_terminal": False,
                "transitions": [{"trigger": "done", "target_state": "END"}],
            },
            "END": {"name": "END", "is_terminal": True},
        }
        config = AgentConfig(**_minimal_config(states=states))
        assert len(config.states) == 3
        assert config.states["GREETING"].transitions[0].target_state == "VERIFY"


# ---------------------------------------------------------------------------
# DataPointSchema
# ---------------------------------------------------------------------------

class TestDataPointSchema:
    """Tests for DataPointSchema model."""

    def test_defaults(self) -> None:
        dp = DataPointSchema(field_name="test_field", type=DataPointType.STRING)
        assert dp.display_name == ""
        assert dp.required is False
        assert dp.pii_level == PIILevel.NONE
        assert dp.is_candidate_input is False
        assert dp.question == ""

    def test_enum_type_with_values(self) -> None:
        dp = DataPointSchema(
            field_name="status",
            type=DataPointType.ENUM,
            enum_values=["full-time", "part-time", "contract"],
        )
        assert dp.enum_values == ["full-time", "part-time", "contract"]

    def test_pii_level_high(self) -> None:
        dp = DataPointSchema(
            field_name="ssn",
            type=DataPointType.STRING,
            pii_level=PIILevel.HIGH,
        )
        assert dp.pii_level == PIILevel.HIGH


# ---------------------------------------------------------------------------
# VoiceConfig
# ---------------------------------------------------------------------------

class TestVoiceConfig:
    """Tests for VoiceConfig model."""

    def test_defaults(self) -> None:
        vc = VoiceConfig()
        assert vc.provider == "vapi"
        assert vc.speed == 1.0
        assert vc.temperature == 0.3

    def test_speed_bounds(self) -> None:
        with pytest.raises(Exception):
            VoiceConfig(speed=0.1)
        with pytest.raises(Exception):
            VoiceConfig(speed=3.0)

    def test_temperature_bounds(self) -> None:
        with pytest.raises(Exception):
            VoiceConfig(temperature=-0.1)
        with pytest.raises(Exception):
            VoiceConfig(temperature=1.5)


# ---------------------------------------------------------------------------
# ComplianceCheckpoint
# ---------------------------------------------------------------------------

class TestComplianceCheckpoint:
    """Tests for ComplianceCheckpoint model."""

    def test_defaults(self) -> None:
        cp = ComplianceCheckpoint(
            name="test", description="A test", validation_rule="test_rule",
        )
        assert cp.failure_action == FailureAction.BLOCK
        assert cp.error_message == "Compliance checkpoint failed"


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

class TestYAMLLoader:
    """Tests for loading agent configs from YAML files."""

    def test_load_employment_config(self) -> None:
        config = load_agent_config("agents/employment_verification_call.yaml")
        assert config.agent_id == "employment_verification_v1"
        assert "GREETING" in config.states
        assert len(config.data_schema) > 0

    def test_load_education_config(self) -> None:
        config = load_agent_config("agents/education_verification_call.yaml")
        assert config.agent_id == "education_verification_v1"
        assert "GREETING" in config.states

    def test_load_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_agent_config("agents/nonexistent.yaml")

    def test_load_all_agent_configs(self) -> None:
        configs = load_all_agent_configs("agents")
        assert len(configs) >= 2
        assert "employment_verification_v1" in configs
        assert "education_verification_v1" in configs

    def test_load_all_from_nonexistent_dir_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_all_agent_configs("nonexistent_dir")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("just a string, not a mapping")
        with pytest.raises(ValueError, match="YAML mapping"):
            load_agent_config(str(bad_file))

    def test_load_yaml_with_missing_required_fields(self, tmp_path: Path) -> None:
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text(yaml.dump({"agent_id": "test"}))
        with pytest.raises(Exception):  # pydantic ValidationError
            load_agent_config(str(incomplete))
