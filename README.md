# 🚀 Zoovy: Autonomous Local AI Agent Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Engine: Ollama](https://img.shields.io/badge/Engine-Ollama%20Local-purple.svg)](https://ollama.com)
[![MCP: Model Context Protocol](https://img.shields.io/badge/MCP-Zero--Browser%20Default-blueviolet.svg)](https://modelcontextprotocol.io)
[![Browser: Optional Extra](https://img.shields.io/badge/Browser-Optional%20Fallback-lightgrey.svg)](https://playwright.dev)
[![Changelog](https://img.shields.io/badge/Changelog-Keep%20a%20Changelog-orange.svg)](CHANGELOG.md)

**Zoovy** is an open-source, fully local autonomous AI agent ecosystem designed to automate real-world commerce and delivery tasks (**Zepto**, **Swiggy**, and **Zomato**).

Zoovy is built around a **Zero-Browser Model Context Protocol (MCP) Architecture**:
1. **⚡ Zero-Browser MCP Engine (Default - Chromium Stashed):** Connects directly to **Zepto Dark Stores** (standalone MCP server), **Swiggy Builders Club** (`mcp.swiggy.com`), and **Zomato MCP** over standardized JSON-RPC tools. Instant execution, no heavy browser downloads, and payments returned as native UPI QR codes.
2. **🌐 Resilient Browser Engine (Optional Fallback):** Playwright Chromium automation with cookie persistence, available as an optional extra (`pip install -e ".[browser]"`) when direct MCP accounts are unconfigured.

All orders are governed by a **Goal-Based Evaluator-Optimizer Engine** (Reflexion loop) and a strict **Human-in-the-Loop (HITL) Payment Firewall**.

---

## 🌟 Key Features

- 🧠 **100% Local Intelligence:** Powered by local open-weights LLMs via [Ollama](https://ollama.com) (zero API costs, complete privacy, runs on your GPU).
- ⚡ **Zero-Browser MCP by Default (No Chromium Needed):**
  - **Zepto:** Standalone custom MCP server (`zoovy.mcp.zepto_server`) built on the official MCP 2.x standard with live dark-store catalog search, cart mutations, and checkout intents.
  - **Swiggy:** 49 native tools across Food delivery, Instamart groceries (40,000+ SKUs), and Dineout table reservations.
  - **Zomato:** Zero-browser restaurant menus, dish discovery, item customization, and instant UPI QR payments.
- 🎯 **Goal-Oriented Evaluator-Optimizer Loop:** Deconstructs prompts into formal **Acceptance Criteria** and **Negative Constraints**, evaluates live cart state, and executes self-correcting reflexion cycles before showing the invoice.
- 🔄 **Self-Healing Recovery Recipes (`RecoveryRecipeEngine`):** Autonomous recovery actions for out-of-stock items, catalog mismatches, and budget breaches before escalating to the human user.
- 💰 **Hard Budget Fencing & Resource Scopes:** Deterministic spending caps (`max_budget_inr`) and SKU boundaries (`max_sku_count`) enforced algorithmically in addition to LLM evaluation.
- 🔒 **Cryptographic Approval Audit Ledger (`ApprovalTokenLedger`):** Immutable local audit log (`~/.zoovy/audit_ledger.jsonl`) recording order token IDs, timestamps, and SHA-256 integrity checksums for complete traceability.
- 📍 **Full Address Verification:** Shows the full, unabridged delivery destination (house/flat number, building, street, landmark, and pincode) before authorization.
- 🛒 **Interactive Cart Modification:** Edit your cart live (`[m] Modify`) to add items, delete items, or adjust quantities with automatic invoice recalculation.
- 🛡️ **Human-in-the-Loop Payment Firewall:** AI prepares the cart, resolves variants, and verifies totals, but **never** auto-debits funds. Payment requires your manual confirmation.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    User(["User Terminal"]) <--> CLI["Zoovy CLI (zoovy.cli)"]
    CLI <--> GoalEngine["Goal-Based Evaluator-Optimizer (goal_engine.py)"]

    subgraph Core ["Shared Core System"]
        HW["Hardware Profiler (hardware.py)"]
        LLM["Ollama Local LLM (llm.py)"]
        Recovery["Self-Healing Recovery Engine (RecoveryRecipeEngine)"]
        Gate["Payment Gatekeeper & Invoice (safety.py)"]
        Ledger[("Immutable Audit Ledger (audit_ledger.jsonl)")]
    end

    GoalEngine <--> Core
    GoalEngine <--> Recovery

    subgraph ExecutionEngines ["Execution Engines"]
        subgraph MCPEngine ["⚡ Zero-Browser MCP Engine (Default / Stashed Chromium)"]
            ZeptoMCP["Custom Zepto MCP Server (zoovy.mcp.zepto_server)"]
            SwiggyMCP["Swiggy Builders Club MCP (mcp.swiggy.com)"]
            ZomatoMCP["Zomato MCP Server"]
        end

        subgraph BrowserEngine ["🌐 Resilient Browser Engine (Optional Fallback)"]
            Playwright["Persistent Browser Context (browser.py)"]
            ZeptoDriver["Zepto Driver"]
            SwiggyDriver["Swiggy Driver"]
            ZomatoDriver["Zomato Driver"]
        end
    end

    GoalEngine -->|"Default: Zero-Browser MCP"| MCPEngine
    GoalEngine -.->|"Optional: --browser fallback"| BrowserEngine

    MCPEngine -->|"Cart State & Bill"| GoalEngine
    BrowserEngine -.->|"Scraped Cart"| GoalEngine

    GoalEngine -->|"Verified Contract & Budget Fence"| Gate
    Gate -->|"SHA-256 Approval Token"| Ledger
    Gate -.->|"Presents Invoice, Full Address & UPI QR"| User
```

---

## 📊 VRAM Tier & Model Recommendation

Zoovy defaults out-of-the-box to **`qwen2.5:1.5b`** (~986MB, fast, universal compatibility), with hardware-matched enhanced tiers available during setup:

| Model Role | Model Tag | Required VRAM | BFCL v4 Score | Download Size | Best Suited For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Default Out-of-the-Box** | **`qwen2.5:1.5b`** | **~1.5 GB** | **64.0%** | **~986 MB** | Instant setup, universal compatibility, CPUs, laptops |
| **Tier 1: Enhanced** | **`qwen2.5:14b`** | **~9.2 GB** | **88.4%** | **~9.0 GB** | Enthusiast GPUs (>= 16GB VRAM: AMD RX 9070 XT, RTX 4080/4090) |
| **Tier 2: Enhanced** | **`qwen2.5:7b`** | **~5.2 GB** | **83.1%** | **~4.7 GB** | Standard GPUs (8GB - 15GB VRAM: RTX 3060/4060/4070) |
| **Tier 3: Enhanced** | **`qwen2.5:3b`** | **~2.6 GB** | **71.2%** | **~2.0 GB** | Entry-level GPUs (4GB - 7GB VRAM) |

---

## 🛠️ Lightweight 2-Step Setup (No Chromium Download)

Setup is ultra-lightweight because Playwright Chromium (~350MB) is completely stashed by default.

### 1. Prerequisites
- **Python 3.10+**
- **Git**
- **Ollama:** [Download & Install Ollama](https://ollama.com/download)

### 2. Clone & Run Setup (2 Quick Steps)
```bash
git clone https://github.com/akusa-03/zoovy.git
cd zoovy
```

- **Windows (PowerShell):**
  ```powershell
  .\setup.ps1
  ```
  *(Or double-click `setup.bat`)*
- **Linux / macOS:**
  ```bash
  chmod +x setup.sh && ./setup.sh
  ```

### 3. Run Hardware Diagnostic
```bash
zoovy doctor
zoovy setup
```

*(Optional: If you ever need the browser fallback engine, run `pip install -e ".[browser]" && playwright install chromium`)*

---

## 🚀 Usage Guide

### A. Zero-Browser Orders (Default)
Operates directly over fast JSON-RPC tools without opening any browser:
```bash
# Order groceries on Zepto (Default)
zoovy order "Get 4 cans of diet coke to my home"

# Order groceries on Swiggy Instamart
zoovy order "Get 1kg tomatoes and Amul butter" --platform swiggy

# Order food on Zomato
zoovy order "Order 2 chicken biryanis" --platform zomato
```

### B. Interactive Platform Prompt
If you don't mention a platform in your prompt, Zoovy interactively asks:
```bash
zoovy order "Get 4 cans of diet coke to my home"
```
```text
📍 Platform Selection:
No delivery platform was specified in your prompt.
  [1] Zepto (Groceries & Dark Store - Fast MCP Mode) (Default)
  [2] Swiggy (Instamart Groceries & Food - Official MCP)
  [3] Zomato (Restaurant Food Delivery - MCP Mode)

Select platform [1-3, Default: 1 (Zepto)]:
```

### C. Standalone Zepto MCP Server
Run our built-in custom Zepto MCP server for Claude Desktop, Cursor, or Zoovy:
```powershell
python -m zoovy.mcp.zepto_server
```
*Exposes `zepto_search_products`, `zepto_add_to_cart`, `zepto_get_cart`, `zepto_get_saved_addresses`, and `zepto_checkout` over standard I/O (stdio).*

### D. Interactive Cart Modification Loop
Whenever Zoovy displays the invoice table, you can interactively inspect or change your items:
```text
Order Actions:
  [y] Confirm & proceed to payment
  [m] Modify cart (add/remove items or adjust quantities)
  [n] Abort order

Select action [y/m/N]:
```
Pressing **`m`** pauses the agent, lets you add items or adjust quantities live, and re-evaluates the acceptance criteria and invoice automatically.

### E. Optional Browser Fallback Mode
If you prefer running a visual browser session with persistent cookies:
```bash
zoovy order "Get 4 cans of diet coke" --browser
```

---

## 🛡️ Safety & Payment Guardrails

1. **Zero Financial Auto-Debit:** Zoovy never asks for or stores UPI PINs, CVVs, or card credentials.
2. **Verified Destination Display:** The complete address (flat, building, street, landmark, pincode) is printed before payment.
3. **Deterministic Payment Pause:** Navigation halts at payment; an interactive invoice and payment QR are displayed for human authorization.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
\n