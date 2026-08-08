# AI provider interface

PaperForge's generation pipeline (`paperforge generate`) works with
**zero** AI providers configured. Only two providers ship, and neither
makes a network call, reads an API key, or transmits any project content
anywhere:

| Provider | `--provider` value | What it does |
|---|---|---|
| No-AI (default) | `no_ai` | Deterministic, template-only. Wraps each claim's own text in a neutral, evidence-class-aware sentence. See [GENERATION.md](GENERATION.md). |
| Fixture | `fixture` | Returns canned, hardcoded strings. Exists purely so tests can exercise the provider *interface* without depending on `no_ai`'s specific templates. Never used by default. |

No test in this repository requires a real API key, and none is needed to
use any shipped PaperForge command.

## The interface

`paperforge.generation.providers.GenerationProvider` is an abstract base
class documenting the extension point for a future real AI integration:

```python
class GenerationProvider(ABC):
    config: ProviderConfig  # name, model_identifier, timeout_seconds,
                             # max_retries, supports_structured_output,
                             # max_input_chars, privacy_class,
                             # redaction_enabled, offline_supported

    @abstractmethod
    def render_claim_sentence(self, ctx: ClaimContext) -> str: ...
```

`ClaimContext` is deliberately minimal: a provider only ever receives one
claim's id, author-written text, evidence class, evidence refs, and
citation keys — never the full manifest, never raw evidence file
contents, never other authors' unpublished text.

`ProviderConfig.validate()` enforces that any provider declaring
`privacy_class="external"` must also set `redaction_enabled=True` before
it can even be constructed — the config raises `ValueError` otherwise.
This is a structural guard, not a policy statement about any specific
external provider, since **no external provider is implemented in this
repository**. Implementing one (with real redaction, consent handling,
and network calls) is out of scope for this pass; see "Remaining
limitations" in the release notes.

## Do not transmit project content externally

Nothing in the current codebase transmits manifest data, evidence, or
generated text to an external service as part of generation. If you build
a custom `GenerationProvider` that does, you are responsible for: explicit
user consent, redaction of secrets/personal data/proprietary evidence
before transmission, and honoring `offline_supported`/`privacy_class` in
your own provider configuration.
