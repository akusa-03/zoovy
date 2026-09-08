# 🚀 Zoovy: Autonomous Local AI Agent Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Engine: Ollama](https://img.shields.io/badge/Engine-Ollama%20Local-purple.svg)](https://ollama.com)
[![Browser: Playwright](https://img.shields.io/badge/Browser-Playwright-red.svg)](https://playwright.dev)
[![Changelog](https://img.shields.io/badge/Changelog-Keep%20a%20Changelog-orange.svg)](CHANGELOG.md)

**Zoovy** is an open-source, fully local AI agent framework designed to automate real-world daily tasks. Its flagship module, **`delivery-agent`**, autonomously navigates delivery platforms (**Zepto**, **Swiggy**, and **Zomato**), searches products, builds carts, resolves item variants, and navigates to the checkout counter—with a built-in **Human-in-the-Loop (HITL) payment firewall**.

---

## 🌟 Key Features

- 🧠 **100% Local Intelligence:** Powered by local open-weights LLMs via [Ollama](https://ollama.com) (no API keys, no subscription fees, complete privacy).
- ⚡ **Dynamic Hardware Detection:** Automatically profiles your GPU, VRAM, and RAM on startup and recommends the optimal model tier.
- 🛒 **Multi-Platform Delivery Support:**
  - **Zepto:** Quick commerce groceries & fresh essentials
  - **Swiggy:** Food delivery & Instamart
  - **Zomato:** Restaurant discovery & food ordering
- 🔑 **Persistent Sessions:** Log in once with your phone number and OTP; session cookies are securely persisted locally.
- 🛡️ **Human-in-the-Loop Payment Guardrail:** The AI handles product discovery, price comparisons, and cart building, but **never** triggers payment. It pauses at checkout, presents an order invoice summary, and asks for your physical confirmation.
- 🧩 **Extensible Agent Architecture:** Designed as an umbrella hub so new agents (travel, finances, calendar) can plug into the shared core.

---

## 📊 VRAM Tier & Model Recommendation Benchmark

Zoovy provides a lightweight default model (**`qwen2.5:1.5b`**) for fast setup and low resource footprints (~986MB), with an interactive option during `zoovy setup` to upgrade to a hardware-optimized enhanced model based on your GPU VRAM:

| Model Role | Model Tag | Required VRAM | BFCL v4 Score | Download Size | Best Suited For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Default Out-of-the-Box** | **`qwen2.5:1.5b`** | **~1.5 GB** | **64.0%** | **~986 MB** | Instant setup, universal compatibility, CPUs, budget laptops |
| **Tier 1: Enhanced** | **`qwen2.5:14b`** | **~9.2 GB** | **88.4%** | **~9.0 GB** | Enthusiast GPUs (>= 16GB VRAM: AMD RX 9070 XT, RTX 4080/4090) |
| **Tier 2: Enhanced** | **`qwen2.5:7b`** | **~5.2 GB** | **83.1%** | **~4.7 GB** | Standard GPUs (8GB - 15GB VRAM: RTX 3060/4060/4070) |
| **Tier 3: Enhanced** | **`qwen2.5:3b`** | **~2.6 GB** | **71.2%** | **~2.0 GB** | Entry-level GPUs (4GB - 7GB VRAM) |

> **Why Qwen 2.5?** In real-world benchmarks, Qwen 2.5 significantly outperforms Llama 3.1 on Indian grocery taxonomy (e.g., *Amul butter*, *paneer*, *atta*, regional vegetable names) and strict JSON schema adherence.

---

## 🛠️ Installation & Quickstart

### 1. Prerequisites
- **Python 3.10+**
- **Git**
- **Ollama:** [Download & Install Ollama](https://ollama.com/download)

### 2. Clone & Install
```bash
git clone https://github.com/akusa-03/zoovy.git
cd zoovy

# Create virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -e .
playwright install chromium
```

### 3. Run Hardware Diagnostic & Setup
```bash
# Check system readiness and get your hardware tier recommendation
zoovy doctor

# Automatically detect VRAM and pull the optimal model from Ollama
zoovy setup
```

### 4. One-Time Account Login (Persistent Session)
Because delivery platforms require phone + OTP verification, log in once via the visible browser:
```bash
# Opens Zepto in a browser window to log in via OTP (session is saved locally)
zoovy login --platform zepto

# Or for Swiggy / Zomato:
zoovy login --platform swiggy
zoovy login --platform zomato
```
*Your session cookies, tokens, and saved delivery addresses are stored locally in `~/.zoovy/sessions/` and reused on all future runs.*

### 5. Place an Order, Inspect Cart & Confirm Address
When you run an order command, the AI:
1. Selects your delivery address from your saved account addresses.
2. Finds products, matches weight/variant descriptions, and adds them to cart.
3. Opens the cart and prints an **itemized invoice** showing exact descriptions, weights, quantities, unit prices, and delivery fees.
4. **Pauses for your confirmation** before opening the final payment view.

```bash
# Order groceries on Zepto (interactive review & address selection)
zoovy order --platform zepto "Get 500g Amul salted butter and 1kg tomatoes"

# Order food on Swiggy
zoovy order --platform swiggy "Order 2 chicken biryanis from the highest rated restaurant nearby"
```

---

## 🏗️ System Architecture

```mermaid
graph TD
    User(["User Terminal"]) <--> CLI["Zoovy CLI (zoovy.cli)"]
    CLI <--> Core["Zoovy Core"]

    subgraph Core ["Shared Core System"]
        HW["Hardware Profiler (hardware.py)"]
        LLM["Ollama Engine (llm.py)"]
        Gate["Payment Gatekeeper (safety.py)"]
    end

    Core <--> Delivery["Delivery Sub-Agent (zoovy.agents.delivery)"]

    subgraph Delivery ["Delivery Agent"]
        Orch["Agent Orchestrator (agent.py)"]
        Browser["Persistent Playwright Browser (browser.py)"]

        subgraph Drivers ["Platform Drivers"]
            Zepto["Zepto Driver"]
            Swiggy["Swiggy Driver"]
            Zomato["Zomato Driver"]
        end
    end

    Orch --> Browser
    Browser --> Drivers
    Gate -.->|"Presents Invoice & Pauses"| User
```

---

## 🛡️ Safety & Payment Guardrails

Autonomous agents should **never** have uncontrolled access to financial accounts. Zoovy implements strict deterministic guardrails:
1. **No Stored Payment Credentials:** Zoovy never asks for or stores UPI PINs, CVVs, or card credentials.
2. **Deterministic Checkout Breakpoint:** Navigation strictly halts at the final checkout view.
3. **Interactive Terminal Invoice:** Zoovy prints the cart breakdown (item count, total INR, delivery fees) and opens the visible browser window for the human user to complete payment.

---

## 🗺️ Roadmap & Future Modules

- [ ] **Voice Control:** Local Whisper speech-to-text input.
- [ ] **Visual UI Fallback:** `qwen2.5-vl:7b` vision engine for complex canvas/SVG UI components.
- [ ] **Travel Agent:** Local flight & train price tracking and reservation assistant.
- [ ] **Android Device Bridge:** Optional ADB bridge for mobile-app-only platforms.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
