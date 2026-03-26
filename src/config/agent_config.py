"""Pydantic models for YAML-based agent configuration.

These models define the schema for agent configuration files. Each agent type
(employment verification, education verification, etc.) is defined as a YAML
file that is validated against these models at load time.

The config-driven approach means new agent types require zero code changes —
only a new YAML file.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class PIILevel(str, Enum):
    """Classification of PII sensitivity for encryption decisions.

    Fields marked MEDIUM or HIGH are encrypted at rest using Fernet symmetric
    encryption. This ensures compliance with data protection requirements.
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataPointType(str, Enum):
    """Supported data types for collected verification fields."""

    STRING = "string"
    DATE = "date"
    BOOLEAN = "boolean"
    ENUM = "enum"


class FailureAction(str, Enum):
    """Action to take when a compliance checkpoint fails.

    BLOCK: Prevent state transition entirely (e.g., missing recorded line disclosure).
    WARN: Allow transition but flag for review.
    LOG: Record the violation but do not impede flow.
    """

    BLOCK = "block"
    WARN = "warn"
    LOG = "log"


class ComplianceCheckpoint(BaseModel):
    """A compliance rule that must be evaluated during the call.

    Compliance checkpoints can be attached to specific states (evaluated on
    exit) or globally (evaluated throughout the call). The state machine
    enforces BLOCK-level checkpoints — the agent cannot proceed until they pass.
    """

    name: str = Field(..., description="Unique identifier for this checkpoint")
    description: str = Field(..., description="Human-readable description of the rule")
    validation_rule: str = Field(
        ...,
        description="Rule identifier used by the compliance validator engine",
    )
    failure_action: FailureAction = Field(
        default=FailureAction.BLOCK,
        description="What to do if this checkpoint fails",
    )
    error_message: str = Field(
        default="Compliance checkpoint failed",
        description="Message to log/display on failure",
    )


class DataPointSchema(BaseModel):
    """Schema for a single data field collected during verification.

    Each field defines its type, whether it's required, and its PII sensitivity
    level. The PII level determines whether the value is encrypted at rest.
    """

    field_name: str = Field(..., description="Unique field identifier")
    display_name: str = Field(default="", description="Human-readable label for UI display")
    type: DataPointType = Field(..., description="Data type for validation")
    required: bool = Field(default=False, description="Whether this field must be collected")
    enum_values: list[str] | None = Field(
        default=None,
        description="Valid values if type is ENUM",
    )
    description: str = Field(default="", description="Human-readable field description")
    question: str = Field(
        default="",
        description="Question the AI agent asks to verify this field. "
        "Supports {{field_name}} template variables for candidate claim values.",
    )
    pii_level: PIILevel = Field(
        default=PIILevel.NONE,
        description="PII classification — MEDIUM and HIGH are encrypted at rest",
    )
    is_candidate_input: bool = Field(
        default=False,
        description="Whether this field is provided as input by the candidate (shown in the call form)",
    )


class AgentTransition(BaseModel):
    """Defines a valid transition between states in the conversation flow.

    Transitions are triggered by events (e.g., employer confirms company name)
    and can have optional conditions and actions.
    """

    trigger: str = Field(..., description="Event that triggers this transition")
    target_state: str = Field(..., description="State to transition to")
    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that must be true for this transition",
    )
    actions: list[str] = Field(
        default_factory=list,
        description="Actions to execute during this transition",
    )


class AgentState(BaseModel):
    """A single state in the conversation state machine.

    Each state represents a phase of the verification call (e.g., GREETING,
    VERIFY_TITLE). States define what data to collect, what transitions are
    valid, and what compliance rules must pass before the agent can move on.
    """

    name: str = Field(..., description="Unique state identifier")
    description: str = Field(default="", description="What happens in this state")
    system_prompt_section: str = Field(
        default="",
        description="Additional prompt guidance specific to this state",
    )
    transitions: list[AgentTransition] = Field(
        default_factory=list,
        description="Valid transitions from this state",
    )
    data_points_to_collect: list[str] = Field(
        default_factory=list,
        description="Field names to collect in this state (references data_schema)",
    )
    compliance_checkpoints: list[ComplianceCheckpoint] = Field(
        default_factory=list,
        description="Compliance rules checked before leaving this state",
    )
    is_terminal: bool = Field(
        default=False,
        description="Whether this state ends the conversation",
    )


class VoiceConfig(BaseModel):
    """Configuration for the voice synthesis provider."""

    provider: str = Field(default="vapi", description="Voice provider (vapi, elevenlabs, etc.)")
    voice_id: str = Field(default="", description="Provider-specific voice identifier")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="LLM temperature — lower = more deterministic, critical for compliance",
    )


class AgentConfig(BaseModel):
    """Root configuration model for an AI voice agent.

    This is the top-level model that a YAML agent config file is validated
    against. It defines everything the platform needs to run an agent:
    states, transitions, data schema, compliance rules, and voice settings.
    """

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    version: str = Field(..., description="Semantic version of this config")
    description: str = Field(default="", description="What this agent does")
    voice_config: VoiceConfig = Field(default_factory=VoiceConfig)
    states: dict[str, AgentState] = Field(
        ...,
        description="All states in the conversation flow, keyed by state name",
    )
    initial_state: str = Field(..., description="State the conversation starts in")
    data_schema: list[DataPointSchema] = Field(
        default_factory=list,
        description="All data fields this agent can collect",
    )
    system_prompt_template: str = Field(
        ...,
        description="Path to the system prompt template file",
    )
    compliance_checkpoints: list[ComplianceCheckpoint] = Field(
        default_factory=list,
        description="Global compliance rules enforced throughout the call",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata for this agent config",
    )

    @model_validator(mode="after")
    def validate_state_references(self) -> AgentConfig:
        """Ensure all state references are valid.

        Validates:
        1. initial_state exists in states
        2. All transition targets reference existing states
        3. At least one terminal state exists
        4. All data_points_to_collect reference fields in data_schema
        """
        # Validate initial state exists
        if self.initial_state not in self.states:
            raise ValueError(
                f"initial_state '{self.initial_state}' not found in states: "
                f"{list(self.states.keys())}"
            )

        # Validate all transition targets reference existing states
        valid_field_names = {dp.field_name for dp in self.data_schema}
        has_terminal = False

        for state_name, state in self.states.items():
            if state.is_terminal:
                has_terminal = True

            for transition in state.transitions:
                if transition.target_state not in self.states:
                    raise ValueError(
                        f"State '{state_name}' has transition to unknown state "
                        f"'{transition.target_state}'"
                    )

            # Validate data point references
            for field_name in state.data_points_to_collect:
                if field_name not in valid_field_names:
                    raise ValueError(
                        f"State '{state_name}' references unknown data field "
                        f"'{field_name}'. Valid fields: {valid_field_names}"
                    )

        if not has_terminal:
            raise ValueError("Agent config must have at least one terminal state")

        return self
