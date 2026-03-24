# Music AI Toolshop Core Design Spec

## 1. Core Mission
The `music-ai-toolshop` is a strict CLI-based adapter layer orchestrating music AI primitives. It adheres perfectly to Single Responsibility Principle - it provides composable, reliable Python APIs and CLI commands for audio analysis, metadata extraction, and workflow orchestration.

## 2. Dev Framework Alignment Principles
- **No Web UI** in this repository. All UI must be built in a separate repo that imports this package.
- **TDD Requirement**: Every adapter must have comprehensive pytest coverage before modification.
- **Zero Hardcoding**: Paths, configurations, and API keys must be injected via CLI args or environment variables.
- **Pure Adapters**: Adapters do not coordinate with each other; `cli.py` or consumer scripts coordinate adapters.

## 3. Architecture

### 3.1. Directory Structure
```
music-ai-toolshop/
├── toolshop/                  # Core package
│   ├── cli.py                 # Thin orchestration layer
│   ├── suno_adapter.py        # Suno API/library interactions
│   ├── bpm_adapter.py         # librosa-based BPM/key
│   └── voice_effects_adapter.py # librosa/crepe based effects
├── tests/                     # TDD requirement
│   ├── conftest.py
│   ├── test_cli.py
│   ├── test_bpm_adapter.py
│   └── ...
├── docs/                      # Systematic planning
│   └── superpowers/
└── pyproject.toml
```

### 3.2. Test-Driven Implementation Plan
1. **Infrastructure**: Setup `pytest` and `pytest-mock`
2. **Adapter Refactor**: Re-write `bpm_adapter.py` fully test-driven
3. **Continuous Integration**: Implement pre-commit hooks for black/flake8

## 4. Dependencies
- `librosa` (core analysis)
- `pytest` (TDD testing)
- `yt-dlp` (YouTube scraping)
