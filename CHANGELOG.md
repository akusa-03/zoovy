# Changelog

All notable changes to the **Zoovy** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Planned: Voice control via local Whisper speech-to-text input.
- Planned: Vision-augmented UI navigation using `qwen2.5-vl:7b` for canvas and complex graphic delivery menus.
- Planned: Android Device Bridge (ADB / UIAutomator) for mobile-only platforms.
- Planned: Multi-store price comparison across Zepto, Swiggy Instamart, and Blinkit for identical grocery carts.

### Changed
- None yet.

### Fixed
- None yet.

---

## [0.1.0] - 2026-09-08

### Added
- **Core Architecture & Framework:**
  - Umbrella project scaffolding for `zoovy` autonomous local AI agent ecosystem.
  - Modular agent interface (`BaseAgent`) enabling pluggable sub-agents.
  - Full CLI entry point with subcommands: `doctor`, `setup`, `login`, and `order`.
- **Dynamic Hardware Profiler (`zoovy/core/hardware.py`):**
  - Automatic probing of GPU device, dedicated VRAM, system RAM, and CPU threads.
  - Hardware classification into 4 performance tiers with tailored model recommendations:
    - *Tier 1 (>=16GB VRAM):* `qwen2.5:14b` (BFCL v4 88.4%)
    - *Tier 2 (8GB-15GB VRAM):* `qwen2.5:7b` (BFCL v4 83.1%)
    - *Tier 3 (4GB-7GB VRAM):* `qwen2.5:3b` (BFCL v4 71.2%)
    - *Tier 4 (CPU Fallback):* `qwen2.5:3b` / `1.5b`
- **LLM Engine (`zoovy/core/llm.py`):**
  - 100% local inference client communicating with Ollama REST API.
  - Strict JSON tool-calling and structured schema enforcement.
  - Streaming model pull with live download progress bars.
- **Safety & Payment Gatekeeper (`zoovy/core/safety.py`):**
  - Deterministic Human-in-the-Loop (HITL) payment firewall.
  - Real-time cart inspection rendering exact item titles, variant descriptions, quantities, unit prices, and delivery fees.
  - Account address selection prompt allowing users to choose or verify delivery destinations before checkout.
  - Physical pause at final payment view; zero automated storage of payment credentials, cards, or UPI PINs.
- **Delivery Agent Module (`zoovy/agents/delivery/`):**
  - Autonomous natural language order parser translating user requests into structured `OrderIntent`.
  - Platform drivers for **Zepto** (`zeptonow.com`), **Swiggy** (`swiggy.com`), and **Zomato** (`zomato.com`).
  - Persistent Playwright browser session manager storing user profiles, tokens, and cookies in `~/.zoovy/sessions/`.
  - Account login command (`zoovy login --platform <name>`) for one-time mobile OTP authorization.
- **Diagnostic Tools:**
  - `zoovy doctor` command providing formatted terminal tables of system specs, Ollama daemon status, model readiness, and Git availability.
- **Packaging & Documentation:**
  - `pyproject.toml` and `requirements.txt` configurations.
  - Comprehensive `README.md` with system architecture diagrams, quickstart guide, and safety principles.
  - MIT Open Source License.

---

### Format Reference for Future Contributors

When adding new changes to this repository, categorize them under `[Unreleased]` using the following standard headings:
- `Added`: for new features.
- `Changed`: for changes in existing functionality.
- `Deprecated`: for soon-to-be removed features.
- `Removed`: for now removed features.
- `Fixed`: for any bug fixes.
- `Security`: in case of vulnerabilities.
