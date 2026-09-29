"""License-tiered lyric-source adapters (SPEC: ORCHESTRATION/lyrics_sources/SPEC.md).

Intentionally empty: no eager imports here — adapter modules pull their own
deps lazily. NEVER ``import toolshop`` from this package (eager toolshop
__init__ costs ~70 s; see megaplan F-B1). Shared helpers live in
``sources._common``; source metadata in ``sources/registry.json``.
"""
