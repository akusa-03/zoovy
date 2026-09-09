# Changelog

All notable changes to the **Zoovy** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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