"""LeanCapsule：可复现、可回放的 Lean 失败工件工具。"""

from .diagnostics_key import diagnostic_key
from .feedback import CapsuleFeedback, normalized_feedback_text
from .ax_integration import (
    CapsuleFeedbackSessions,
    FirstRoundCandidateCache,
    enforce_ax_part2_config,
    install_axproverbase_capsule_feedback,
    validate_ax_proposal_safety,
)
from .pairing import validate_paired_runs

__all__ = [
    "CapsuleFeedback",
    "CapsuleFeedbackSessions",
    "FirstRoundCandidateCache",
    "diagnostic_key",
    "enforce_ax_part2_config",
    "install_axproverbase_capsule_feedback",
    "normalized_feedback_text",
    "validate_ax_proposal_safety",
    "validate_paired_runs",
]
