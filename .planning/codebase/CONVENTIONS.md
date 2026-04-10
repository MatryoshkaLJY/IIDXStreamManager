# Coding Conventions

**Analysis Date:** 2026-04-10

## Overview

This codebase follows a pragmatic Python-first convention set with mixed-language components (Python, JavaScript). The project is a beatmania IIDX streaming assistant toolset with multiple modules for state recognition, score tracking, and broadcast overlays.

## Languages

**Primary:**
- Python 3.8+ - All core logic, ML inference, and backend services
- JavaScript (ES6+) - Frontend UI for BPL scoreboard (`iidx_bpl_scoreboard/app.js`)

**Configuration:**
- YAML - State machine definitions (`iidx_state_machine/state_machine.yaml`)
- JSON - Data files, team configurations, WebSocket protocols
- CSV - ROI configurations, annotations

## Python Code Style

### Naming Conventions

**Files:**
- snake_case for all Python files: `obs_manager.py`, `state_machine.py`, `train.py`
- Descriptive names indicating purpose: `recognizer.py`, `serve.py`, `test_client.py`

**Classes:**
- PascalCase: `IIDXDigitRecognizer`, `OBSManager`, `IIDXStateMachineManager`
- Descriptive class names with domain prefix: `IIDXStateMachine`, `FrameDataset`

**Functions/Methods:**
- snake_case: `capture_and_recognize()`, `process_event()`, `load_rois_from_csv()`
- Private methods use underscore prefix: `_crop_to_content()`, `_send_to_inference()`
- Action verbs preferred: `capture`, `recognize`, `process`, `validate`

**Variables:**
- snake_case: `machine_id`, `source_name`, `infer_addr`
- Constants use UPPER_SNAKE_CASE: `MEAN`, `STD`, `DEFAULT_ROIS`
- Type hints widely used: `Optional[Tuple[int, int]]`, `Dict[str, Any]`

### Code Organization

**Import Order (observed pattern):**
```python
# 1. Standard library
import argparse
import io
import json
import socket
import struct
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 2. Third-party libraries
import numpy as np
from PIL import Image

# 3. Local modules
from recognizer import IIDXDigitRecognizer
```

**Module Structure:**
- Shebang line for executable scripts: `#!/usr/bin/env python3`
- Module docstring with description and usage examples
- Constants at module level
- Classes grouped by functionality
- Main entry point guarded: `if __name__ == "__main__":`

### Type Hints

**Required pattern:** All functions include type hints
```python
def capture_and_recognize(
    self,
    source_name: str,
    infer_addr: Union[str, Tuple[str, int]] = ("127.0.0.1", 9876),
    target_size: Tuple[int, int] = (224, 224),
    image_format: str = "jpeg"
) -> str:
```

**Common type patterns:**
- `Optional[T]` for nullable values
- `Union[str, Tuple[str, int]]` for multiple acceptable types
- `Dict[str, Any]` for flexible JSON-like data
- `List[Tuple[str, int, int, int, int]]` for structured lists

### Docstrings

**Style:** Google-style docstrings with Args/Returns sections
```python
def process_event(self, event: str) -> Dict[str, Any]:
    """Process a single event.

    Args:
        event: Input event string

    Returns:
        Result dictionary with transition details
    """
```

### Error Handling

**Pattern:** Try/except with specific exceptions and informative messages
```python
try:
    self._client = obsws.ReqClient(...)
except Exception as e:
    raise ConnectionError(f"无法连接到 OBS WebSocket ({self.host}:{self.port}): {e}")
```

**Validation pattern:**
```python
def _ensure_connected(self) -> None:
    """Ensure connected, otherwise raise RuntimeError"""
    if not self.is_connected():
        raise RuntimeError("未连接到 OBS，请先调用 connect()")
```

### Dataclasses

**Preferred for configuration objects:**
```python
@dataclass
class MachineConfig:
    """Configuration for a single game cabinet."""
    machine_id: str
    source_name: str
    state_infer_addr: Union[str, Tuple[str, int]] = ("127.0.0.1", 9876)
    score_infer_addr: Tuple[str, int] = ("127.0.0.1", 9877)
```

## JavaScript Conventions

**Style:** ES6+ class-based with modern JavaScript features

**Naming:**
- Classes: PascalCase (`ScoreboardApp`)
- Methods: camelCase (`handleCommand()`, `connectWebSocket()`)
- Constants: UPPER_SNAKE_CASE for true constants

**Structure:**
- Single class per file
- Constructor initializes state
- Method organization by functionality (commented sections)
- Event handlers prefixed with `handle`

## Configuration Files

**YAML (State Machine):**
```yaml
states:
  - id: IDLE
    description: "Cabinet is idle"
    is_initial: true

transitions:
  - from: IDLE
    to: ENTRY
    event: entry
    actions: []
```

**CSV Format:**
- ROI configs: `name,x1,y1,x2,y2`
- Annotations: `filename,label`

## Comments and Documentation

**Chinese Comments:** Primary documentation language is Chinese (Simplified) with English technical terms preserved

**Code Comments:**
- Section dividers: `# ========== Section Name ==========`
- Inline comments explain "why" not "what"
- ASCII diagrams for protocols

**Example:**
```python
# 协议（每次请求）:
#   发送: [4字节大端无符号整数 = 图片长度] [图片字节 (JPEG/PNG/...)]
#   接收: [JSON字符串\n]  例如 {"ROI_1": "1234", ...}
```

## Protocol Conventions

**Binary Protocol Pattern:**
- 4-byte big-endian length header
- Followed by payload data
- Used across: `serve.py`, `obs_manager.py`, score recognition service

**WebSocket Protocol:**
- JSON messages with `cmd` and `data` fields
- Commands: `init`, `score`, `reset`

## Testing Conventions

**Test File Naming:**
- `test_<module>.py` for module tests
- `test_<feature>.py` for feature tests
- Standalone `test.py` for simple modules

**Test Structure:**
- Functions prefixed with `test_`
- Assertion-based validation
- Manual test execution (no pytest framework detected)

## Linting and Formatting

**Status:** No formal linting configuration detected
- No `.pylintrc`, `setup.cfg`, `pyproject.toml`, or `.flake8` files
- No pre-commit hooks
- No CI/CD configuration files

**Observed Patterns (de facto standards):**
- 4-space indentation
- 100-120 character line length (inferred from code)
- Double quotes for strings (mixed usage observed)
- Trailing commas in multi-line collections

## Dependencies

**Core ML Stack:**
- PyTorch / torchvision (MobileNetV3)
- ONNX Runtime for inference
- OpenCV for image processing
- NumPy for numerical operations
- Pillow for image I/O

**Web/Network:**
- Flask for web annotation tool
- websockets for async WebSocket clients
- obsws-python for OBS Studio integration

**UI:**
- Streamlit for TPL scene switcher
- Vanilla JavaScript for BPL scoreboard frontend

## File Organization

**Module Structure:**
```
module_name/
├── __init__.py           # Package initialization (minimal)
├── main_module.py        # Core functionality
├── serve.py              # Network service entry point
├── test_*.py             # Test files
└── CLAUDE.md             # Module documentation
```

**Executable Scripts:**
- Include shebang: `#!/usr/bin/env python3`
- Include `if __name__ == "__main__":` guard
- Provide argparse CLI interface

---

*Convention analysis: 2026-04-10*
