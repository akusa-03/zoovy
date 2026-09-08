import os
import platform
import subprocess
import shutil
import psutil
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class HardwareProfile:
    gpu_name: str
    vram_gb: float
    system_ram_gb: float
    cpu_cores: int
    tier: str
    recommended_model: str
    context_window: int
    rationale: str


def detect_vram_windows() -> Tuple[str, float]:
    """Query Windows WMI and PowerShell for GPU Name and dedicated VRAM."""
    gpu_name = "Generic GPU"
    vram_gb = 0.0

    # 1. Try PowerShell CimInstance for Win32_VideoController
    ps_cmd = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name, AdapterRAM | "
        "ConvertTo-Json"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            import json
            data = json.loads(res.stdout)
            if isinstance(data, list):
                # Pick dedicated GPU (highest RAM or recognized brand)
                for item in data:
                    name = item.get("Name", "")
                    # Prefer dedicated Radeon / GeForce
                    if any(brand in name.lower() for brand in ["radeon rx", "geforce", "rtx", "nvidia"]):
                        gpu_name = name
                        # AdapterRAM may cap at 4GB in 32-bit WMI; check known GPUs
                        adapter_ram = item.get("AdapterRAM", 0) or 0
                        vram_gb = max(vram_gb, adapter_ram / (1024 ** 3))
                        break
                    elif item.get("AdapterRAM"):
                        gpu_name = name
                        vram_gb = max(vram_gb, item.get("AdapterRAM") / (1024 ** 3))
            elif isinstance(data, dict):
                gpu_name = data.get("Name", gpu_name)
                vram_gb = (data.get("AdapterRAM", 0) or 0) / (1024 ** 3)
    except Exception:
        pass

    # 2. Heuristic check for modern flagship GPUs where 32-bit WMI truncates AdapterRAM
    gpu_lower = gpu_name.lower()
    if "9070" in gpu_lower:
        vram_gb = 16.0
    elif "4090" in gpu_lower:
        vram_gb = 24.0
    elif "4080" in gpu_lower:
        vram_gb = 16.0
    elif "4070" in gpu_lower:
        vram_gb = 12.0
    elif "4060" in gpu_lower:
        vram_gb = 8.0
    elif "3060" in gpu_lower:
        vram_gb = 12.0

    return gpu_name, vram_gb


def detect_vram_nvidia() -> Optional[float]:
    """Query nvidia-smi if available."""
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0:
                mb = float(res.stdout.strip().splitlines()[0])
                return mb / 1024.0
        except Exception:
            pass
    return None


def get_hardware_profile() -> HardwareProfile:
    """
    Detects hardware capabilities and assigns the machine to an LLM performance tier.
    """
    cpu_cores = os.cpu_count() or 4
    system_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)

    gpu_name = "Integrated / Software"
    vram_gb = 0.0

    # Try NVIDIA SMI
    nvidia_vram = detect_vram_nvidia()
    if nvidia_vram:
        gpu_name = "NVIDIA Dedicated GPU"
        vram_gb = nvidia_vram
    elif platform.system() == "Windows":
        gpu_name, vram_gb = detect_vram_windows()

    # Determine Tier & Recommendation
    if vram_gb >= 14.0:
        tier = "Tier 1: High VRAM (Enthusiast)"
        recommended_model = "qwen2.5:14b"
        context_window = 32768
        rationale = (
            f"Detected {vram_gb:.1f}GB VRAM on {gpu_name}. Qwen 2.5 14B fits comfortably "
            "with full 32k context and delivers state-of-the-art agentic tool calling (88.4% BFCL v4)."
        )
    elif vram_gb >= 7.0:
        tier = "Tier 2: Standard VRAM"
        recommended_model = "qwen2.5:7b"
        context_window = 16384
        rationale = (
            f"Detected {vram_gb:.1f}GB VRAM on {gpu_name}. Qwen 2.5 7B provides lightning-fast "
            "inference (~85 t/s) with robust structured JSON adherence."
        )
    elif vram_gb >= 3.0:
        tier = "Tier 3: Low VRAM"
        recommended_model = "qwen2.5:3b"
        context_window = 8192
        rationale = (
            f"Detected {vram_gb:.1f}GB VRAM. Qwen 2.5 3B is ultra-lightweight (~2.6GB) and "
            "runs smoothly with low resource overhead."
        )
    else:
        tier = "Tier 4: CPU Fallback"
        recommended_model = "qwen2.5:3b"
        context_window = 4096
        rationale = (
            f"No dedicated high-memory GPU found. Utilizing {system_ram_gb}GB system RAM and "
            f"{cpu_cores} CPU cores with Qwen 2.5 3B."
        )

    return HardwareProfile(
        gpu_name=gpu_name,
        vram_gb=round(vram_gb, 1),
        system_ram_gb=system_ram_gb,
        cpu_cores=cpu_cores,
        tier=tier,
        recommended_model=recommended_model,
        context_window=context_window,
        rationale=rationale
    )
