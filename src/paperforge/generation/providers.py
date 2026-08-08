"""Provider-neutral generation interface.

PaperForge's core generation pipeline works with **zero** AI providers
configured. :class:`NoAIProvider` is the default and only provider used by
`paperforge generate` today; :class:`FixtureProvider` exists purely so
tests can exercise the provider *interface* deterministically without
touching :class:`NoAIProvider` directly. Neither provider makes a network
call, reads an API key, or transmits any project content anywhere -- both
run entirely in-process.

:class:`GenerationProvider` is the extension point for a future real AI
integration. Implementing one is intentionally out of scope for this
package: no such provider ships here, and nothing in the test suite
requires one or a real API key to pass.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model_identifier: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 0
    supports_structured_output: bool = True
    max_input_chars: int = 0  # 0 == unlimited
    privacy_class: str = "local"  # "local" (never leaves the machine) | "external"
    redaction_enabled: bool = False
    offline_supported: bool = True

    def validate(self) -> list[str]:
        problems = []
        if self.timeout_seconds <= 0:
            problems.append("timeout_seconds must be positive")
        if self.max_retries < 0:
            problems.append("max_retries must be non-negative")
        if self.privacy_class not in {"local", "external"}:
            problems.append("privacy_class must be 'local' or 'external'")
        if self.privacy_class == "external" and not self.redaction_enabled:
            problems.append(
                "external providers must have redaction_enabled=True before any "
                "project content may be sent to them"
            )
        return problems


@dataclass(frozen=True)
class ClaimContext:
    """The minimal, already-approved data a provider is given for one claim.
    Providers never receive the full manifest or raw evidence file
    contents -- only what the plan has already scoped for this claim."""

    claim_id: str
    text: str
    evidence_class: str
    evidence_refs: tuple[str, ...] = ()
    citation_keys: tuple[str, ...] = ()


class GenerationProvider(ABC):
    """Base interface every generation provider implements."""

    config: ProviderConfig

    def __init__(self, config: ProviderConfig) -> None:
        problems = config.validate()
        if problems:
            raise ValueError(
                f"Invalid provider configuration for '{config.name}': {'; '.join(problems)}"
            )
        self.config = config

    @abstractmethod
    def render_claim_sentence(self, ctx: ClaimContext) -> str:
        """Render exactly one neutral sentence for a single claim. Must
        never introduce facts, numbers, or citations not already present
        in ``ctx``."""

    def validate_config(self) -> list[str]:
        return self.config.validate()


_TEMPLATES: dict[str, str] = {
    "AUTHOR_ASSERTED": "As asserted by the authors: {text} [{claim_id}].",
    "SOURCE_SUPPORTED": "Prior work indicates the following: {text} [{claim_id}]{citations}.",
    "DIRECT_RESULT": "A direct result ({claim_id}) indicates: {text}{evidence}.",
    "DERIVED_RESULT": "A derived result ({claim_id}), computed from linked evidence, indicates: {text}{evidence}.",
    "STATISTICAL_RESULT": "A statistical result ({claim_id}), per the documented statistical plan, indicates: {text}{evidence}.",
    "INTERPRETATION": "One interpretation of the results is: {text} [{claim_id}].",
    "HYPOTHESIS": "It is hypothesized that: {text} [{claim_id}].",
    "LIMITATION": "A limitation of this study: {text} [{claim_id}].",
    "FUTURE_WORK": "Future work may address: {text} [{claim_id}].",
    "PLACEHOLDER": "[PLACEHOLDER {claim_id}: {text} -- TODO: replace with real evidence before submission.]",
}
_DEFAULT_TEMPLATE = "{text} [{claim_id}]."


class NoAIProvider(GenerationProvider):
    """Deterministic, template-only provider. The default and only provider
    `paperforge generate` uses unless `--provider fixture` is explicitly
    requested for testing."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(
            config
            or ProviderConfig(
                name="no_ai",
                model_identifier="deterministic-template-v1",
                privacy_class="local",
                offline_supported=True,
            )
        )

    def render_claim_sentence(self, ctx: ClaimContext) -> str:
        template = _TEMPLATES.get(ctx.evidence_class, _DEFAULT_TEMPLATE)
        citations = (
            f" (see {', '.join(ctx.citation_keys)})" if ctx.citation_keys else ""
        )
        evidence = (
            f" (evidence: {', '.join(ctx.evidence_refs)})" if ctx.evidence_refs else ""
        )
        return template.format(
            text=ctx.text, claim_id=ctx.claim_id, citations=citations, evidence=evidence
        )


class FixtureProvider(GenerationProvider):
    """Canned, fully deterministic provider used only by tests. Never used
    by default in `paperforge generate`."""

    def __init__(self, canned: dict[str, str] | None = None) -> None:
        GenerationProvider.__init__(
            self,
            ProviderConfig(
                name="fixture", model_identifier="fixture-v1", privacy_class="local"
            ),
        )
        self.canned = canned or {}

    def render_claim_sentence(self, ctx: ClaimContext) -> str:
        return self.canned.get(ctx.claim_id, f"[fixture:{ctx.claim_id}] {ctx.text}")


_PROVIDERS: dict[str, type[GenerationProvider]] = {
    "no_ai": NoAIProvider,
    "fixture": FixtureProvider,
}


def get_provider(name: str) -> GenerationProvider:
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Available: {sorted(_PROVIDERS)}")
    return cls()  # type: ignore[call-arg]


__all__ = [
    "ClaimContext",
    "FixtureProvider",
    "GenerationProvider",
    "NoAIProvider",
    "ProviderConfig",
    "get_provider",
]
