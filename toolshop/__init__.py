"""Music AI toolshop package."""

import importlib

__all__ = [
    "cli",
    "voice_effects_adapter",
    "cleaning_stages",
    "cleaning_pipeline_adapter",
    "reverse_engineering_adapter",
    "genius_adapter",
    "genius_parser",
    "lyrics_analyzer",
    "remix_adapter",
    "melody_carrier",
]


def __getattr__(name):
    # Lazy (PEP 562): `import toolshop.syllables` must not pull numpy/librosa.
    if name in __all__:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
