"""
Prompt Shield substitution engine, surrogate generation, and session vault.
"""

from prompt_shield.engine.generator import SurrogateGenerator
from prompt_shield.engine.vault import SessionVault, VaultEntry
from prompt_shield.engine.mask import (
    MaskingEngine,
    UnmaskingEngine,
    mask_text,
    unmask_text,
)

__all__ = [
    "SurrogateGenerator",
    "SessionVault",
    "VaultEntry",
    "MaskingEngine",
    "UnmaskingEngine",
    "mask_text",
    "unmask_text",
]
