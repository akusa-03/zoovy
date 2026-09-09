# Changelog

All notable changes to the **Zoovy** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-09-09

### Added
- **Real User Address Book Manager (`AddressBook` in `zoovy/core/address_book.py`):**
  - Persistent local delivery address storage at `~/.zoovy/addresses.yaml`.
  - Automatic interactive address setup on initial execution if no saved locations are found.
  - On-the-fly address addition during checkout (`[+] Add a new delivery address`).
- **CLI Address Management Subcommand (`zoovy address`):**
  - Added commands: `zoovy address list`, `zoovy address add "<address>" --label <Label>`, and `zoovy address remove <label>`.
- **MCP Token Authentication & Cloud Address Syncing (`zoovy login`):**
  - Added Zero-Browser MCP account login via session tokens / JWTs (`zoovy login --platform swiggy --token "..."`).
  - Automatic cloud address retrieval (`get_user_addresses` tool) pulling saved delivery addresses from authenticated Swiggy / Zepto / Zomato cloud accounts into local `AddressBook`.
  - Browser login session (`zoovy login --browser`) now also automatically captures and syncs account addresses into `~/.zoovy/addresses.yaml`.
- **AddressBook Integration Test (TEST 6 in `tests/test_local.py`):**
  - Subsystem test verifying local address creation, formatted listing, and clean removal.

### Changed
- **Eliminated All Hardcoded Dummy Addresses:**
  - Removed all placeholder addresses (`"Home - Flat 402, Sunshine Heights, Indiranagar, Bengaluru - 560038"`) from `zoovy/agents/delivery/agent.py`, `zoovy/core/safety.py`, `zoovy/core/mcp_client.py`, and `zoovy/mcp/zepto_server.py`.
  - All platforms (Zepto, Swiggy, Zomato) now strictly query real user addresses from `AddressBook` or authenticated MCP sessions.

---

## [0.4.0] - 2026-09-09

### Added
- **Self-Healing Recovery Recipes (`RecoveryRecipeEngine` in `zoovy/core/goal_engine.py`):**
  - Encoded structured failure recovery state machine (`FailureScenario.OUT_OF_STOCK`, `BUDGET_EXCEEDED`, `UNREQUESTED_ITEMS_PRESENT`).
  - Automatic catalog variant and brand substitution when items are unavailable.
  - Automatic cart optimization and quantity adjustment suggestions when budgets are breached.
  - Enforced a 2-attempt recovery limit before escalating to human review.
- **Hard Budget Fencing & Resource Boundary Scopes (`GoalContract`):**
  - Added deterministic algorithmic budget cap enforcement (`max_budget_inr`) in addition to LLM reflection.
  - Extracted budget limits via both LLM structured output and regex heuristics (e.g. "under 200 rs", "within 500").
  - Enforced max SKU constraints (`max_sku_count = 15`) to prevent hallucinated runaway additions.
- **Cryptographic Approval Audit Ledger (`ApprovalTokenLedger` in `zoovy/core/safety.py`):**
  - Immutable local audit trail (`~/.zoovy/audit_ledger.jsonl`) recording order token IDs, ISO timestamps, and SHA-256 integrity checksums.
  - Records user decision status (`APPROVED`, `MODIFIED`, `ABORTED`) at every HITL payment checkpoint.

---

## [0.3.0] - 2026-09-09

### Added
- **Default Zero-Browser MCP Architecture Across All Platforms:**
  - Integrated `ZeptoMCPClient` wired to the standalone Zepto MCP server (`zoovy.mcp.zepto_server.py`), completing out-of-the-box zero-browser execution for Zepto, Swiggy, and Zomato.
  - Interactive in-terminal cart modification for MCP mode (`[1] Add item`, `[2] Change quantity`, `[3] Finish`).
  - Added `--browser` flag to `zoovy order` as an explicit fallback instead of requiring `--mcp` for zero-browser operations.
  - Added MCP and browser engine status indicators to `zoovy doctor`.
  - Updated subsystem test suite (`tests/test_local.py`) to validate all 3 MCP clients independently of Playwright.

### Changed
- **Complete Stashing of Chromium / Playwright from Default Setup:**
  - Removed mandatory `playwright>=1.49.0` dependency from `pyproject.toml` and `requirements.txt`.
  - Made Playwright an optional extra (`[project.optional-dependencies] browser = ["playwright>=1.49.0"]`), saving ~350MB download on initial setup.
  - Streamlined `setup.ps1`, `setup.bat`, and `setup.sh` from 3 steps down to 2 clean steps, completely eliminating the `playwright install chromium` step during default setup.
  - Converted all Playwright and browser driver imports in `DeliveryAgent` and `cmd_login` to lazy imports protected by graceful `ImportError` handling.

---

## [0.2.0] - 2026-09-09

### Added
- **Official Model Context Protocol (MCP) Client (`zoovy/core/mcp_client.py`):**
  - Integrated official **Swiggy Builders Club MCP** (`mcp.swiggy.com`) supporting 49 native tools across Food, Instamart, and Dineout.
  - Integrated **Zomato MCP Client** (`mcp.zomato.com`) for zero-browser dish discovery, cart mutations, and instant UPI QR code generation.
  - Added `--mcp` CLI flag to `zoovy order` to stash Chromium and execute orders purely over JSON-RPC tools.
- **Standalone Custom Zepto MCP Server (`zoovy/mcp/zepto_server.py`):**
  - Built a standalone Zepto MCP server adhering to the official Model Context Protocol 2.x standard (`MCPServer`).
  - Exposes 5 standard quick-commerce tools: `zepto_search_products`, `zepto_add_to_cart`, `zepto_get_cart`, `zepto_get_saved_addresses`, and `zepto_checkout`.
  - Compatible with Claude Desktop, Cursor, VS Code, and Zoovy over standard I/O (`stdio`).
- **Goal-Oriented Evaluator-Optimizer Engine (`zoovy/core/goal_engine.py`):**
  - Implemented an open academic agent architecture based on the **Reflexion** (Shinn et al.) and **ReAct** (Yao et al.) paradigms.
  - Formulates explicit verifiable **GoalContracts** with target items, acceptance criteria, and negative constraints (e.g. banning unrequested sponsored products).
  - Employs an independent Evaluator loop that verifies live cart state against acceptance criteria, diagnosing discrepancies and triggering self-correcting reflexion cycles.
- **Interactive Cart Modification Workflow:**
  - Added an interactive action loop in `PaymentGatekeeper`: `[y]` Confirm & pay, `[m]` Modify cart live, `[n]` Abort.
  - Pressing `[m]` keeps the session open for live item adjustments and re-scrapes/re-calculates the invoice upon pressing Enter.
- **Platform Prompt Disambiguation:**
  - Added interactive platform selection prompt when the user prompt does not specify a platform keyword and no `--platform` flag is provided.
- **Full Address Verification:**
  - Updated the Safety Gatekeeper panel and address selector to render the complete, unabridged delivery address (flat/house number, building, street, landmark, pincode) before payment.

### Fixed
- **Zepto Scraper Calibration:**
  - Fixed Zepto search URL query parameter from `?q=` to `?query=`, preventing fallback to unrelated homepage sponsored carousels (e.g., Red Bull).
  - Sanitized product title extraction to skip action button labels (`ADD`, `OFF`, `BESTSELLER`), prices, and ratings, preventing items from being titled `"ADD"`.
  - Calibrated quantity stepper selector to target Zepto's SVG accessible button (`button[aria-label="Increase quantity"]`), resolving stuck quantity increments.
  - Replaced hardcoded fallback dummy items in `inspect_cart()` with live drawer scraping.
- **Navigation Timeout Fix:**
  - Replaced `wait_until="networkidle"` with `wait_until="domcontentloaded"` with safe timeouts across all browser drivers, eliminating 30-second timeout freezes caused by continuous analytics/telemetry streams.

### Changed
- Configured **`qwen2.5:1.5b`** as the out-of-the-box default LLM (~986MB, fast, universal compatibility) with hardware-matched enhanced tiers (`qwen2.5:14b` / `7b` / `3b`) selectable during setup.
- Stashed the browser requirement when running in `--mcp` mode in favor of zero-browser JSON-RPC tools.
- Updated `zoovy doctor` to report both Default and Enhanced model readiness statuses.
- Added `--model` flag to `zoovy setup` for direct non-interactive model downloading.

---

## [0.1.0] - 2026-09-08

### Added
- **Core Architecture & Scaffolding:**
  - Scaffolding for the `zoovy` autonomous local AI agent ecosystem.
  - CLI entry point with subcommands: `doctor`, `setup`, `login`, and `order`.
- **Dynamic Hardware Profiler (`zoovy/core/hardware.py`):**
  - Probes GPU device, dedicated VRAM, system RAM, and CPU threads with 4 performance tiers.
- **LLM Engine (`zoovy/core/llm.py`):**
  - Local inference client communicating with Ollama REST API with auto-daemon launch.
- **Safety & Payment Gatekeeper (`zoovy/core/safety.py`):**
  - Deterministic Human-in-the-Loop (HITL) payment firewall.
  - Interactive terminal invoice presentation and address selection.
- **Initial Browser Delivery Drivers:**
  - Browser automation drivers for Zepto, Swiggy, and Zomato using Playwright persistent contexts.\n