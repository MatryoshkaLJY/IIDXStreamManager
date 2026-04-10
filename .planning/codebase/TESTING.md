# Testing Patterns

**Analysis Date:** 2026-04-10

## Overview

This codebase uses a lightweight, manual testing approach without formal test frameworks like pytest or unittest. Tests are implemented as standalone executable scripts that can be run directly.

## Test Framework Status

**No Formal Framework Detected:**
- No pytest configuration (`pytest.ini`, `pyproject.toml`, `setup.cfg`)
- No unittest test cases or test suites
- No test discovery mechanism
- No CI/CD pipeline for automated testing

**Testing Approach:** Manual execution of test scripts

## Test File Organization

**Location Pattern:** Test files are co-located with source code in module directories

| Test File | Module Tested | Purpose |
|-----------|---------------|---------|
| `iidx_score_reco/test.py` | `recognizer.py` | Digit recognition testing |
| `obs_manager/test_obs_manager.py` | `obs_manager.py` | OBS integration and state machine |
| `obs_manager/test_score_reco.py` | `obs_manager.py` | Score ROI recognition |
| `iidx_state_machine/test_state_machine_manager.py` | `state_machine.py` | State machine unit tests |
| `iidx_state_machine/test_client.py` | State machine TCP server | TCP client testing |
| `iidx_bpl_scoreboard/testbench/testbench.py` | WebSocket server | Scoreboard integration testing |
| `iidx_bpl_scoreboard/testbench/test_relay.py` | WebSocket relay | Relay server testing |

## Test Execution

**Run Commands:**
```bash
# Score recognition test
python iidx_score_reco/test.py data/screenshot.png

# OBS manager tests (mock mode)
python obs_manager/test_obs_manager.py

# OBS manager tests (real OBS connection)
python obs_manager/test_obs_manager.py --real --password <password>

# State machine unit tests
python iidx_state_machine/test_state_machine_manager.py

# State machine TCP client test
python iidx_state_machine/test_client.py -i input.txt

# BPL scoreboard testbench
python iidx_bpl_scoreboard/testbench/testbench.py
```

## Test Patterns

### Pattern 1: Standalone Test Script with Main Guard

**File:** `iidx_score_reco/test.py`

```python
#!/usr/bin/env python3
"""IIDX 数字识别测试脚本"""

def test_recognizer():
    recognizer = IIDXDigitRecognizer("font")
    # Test implementation
    results = recognizer.recognize_all_rois(image_path, rois, debug=True)
    # Print results for manual verification
    print("识别结果:", results)

if __name__ == "__main__":
    test_recognizer()
```

**Characteristics:**
- Single test function
- Command-line argument parsing for test configuration
- Manual result verification via console output
- Debug mode support

### Pattern 2: Multiple Test Functions with Aggregation

**File:** `iidx_state_machine/test_state_machine_manager.py`

```python
def test_two_machines_independent():
    """Two machines fed different events must diverge to independent states."""
    mgr = IIDXStateMachineManager(config_path, log_level="ERROR")
    mgr.add_machine("m1")
    mgr.add_machine("m2")
    
    # Test assertions
    assert mgr.list_machines() == ["m1", "m2"]
    assert mgr.get_machine_state("m1")["current_state"] == "IDLE"
    
    print("[✓] test_two_machines_independent passed")

def main():
    print("=" * 50)
    print("IIDXStateMachineManager tests")
    print("=" * 50)
    test_two_machines_independent()
    # ... more tests
    print("All tests passed")

if __name__ == "__main__":
    main()
```

**Characteristics:**
- Multiple test functions
- Assertion-based validation
- Success/failure console output with checkmarks
- Aggregated test runner in `main()`

### Pattern 3: Mock-Based Testing

**File:** `obs_manager/test_obs_manager.py`

```python
from unittest.mock import Mock, patch

def test_capture_source_mock():
    """Test video source capture (mock mode)"""
    # Create test image
    test_img = create_test_image(640, 480, (255, 0, 0))
    mock_response = create_mock_obs_response(test_img)
    
    # Mock OBS WebSocket client
    mock_client = Mock()
    mock_client.get_version.return_value = Mock(
        obs_version="29.0.0",
        obs_web_socket_version="5.0.0"
    )
    mock_client.get_source_screenshot.return_value = Mock(
        image_data=mock_response
    )
    
    # Inject mock and test
    obs = OBSManager(host="localhost", port=4455)
    obs._client = mock_client
    
    img = obs.capture_source("video", target_size=(224, 224))
    assert img.size == (224, 224), f"Expected (224, 224), got {img.size}"
    
    print("[✓] Test passed!")
```

**Characteristics:**
- Uses `unittest.mock` for dependency mocking
- Mock servers for external services (inference server)
- Assertion validation
- No external dependencies required for test execution

### Pattern 4: Integration Testing with Real Services

**File:** `obs_manager/test_obs_manager.py` (real mode)

```python
def test_real_obs(password: str = "1145141919", infer_tcp: int = None):
    """Actual test (requires OBS and inference service running)"""
    from obs_manager import OBSManager
    
    try:
        with OBSManager(host="localhost", port=4455, password=password) as obs:
            sources = obs.get_sources()
            print(f"[✓] Available sources: {sources}")
            
            result = obs.capture_and_recognize(
                source_name=source_name,
                infer_addr=("127.0.0.1", 9876)
            )
            print(f"[✓] Recognition result: {result}")
            
    except ConnectionError as e:
        print(f"[✗] Failed to connect to OBS: {e}")
        return False
```

**Characteristics:**
- Conditional execution based on `--real` flag
- Real service connections (OBS WebSocket, inference servers)
- Error handling for connection failures
- Informative failure messages

### Pattern 5: TCP Client Test Tool

**File:** `iidx_state_machine/test_client.py`

```python
def send_event(sock: socket.socket, event: str) -> Optional[dict]:
    """Send event to server and return response"""
    sock.send(f"{event}\n".encode('utf-8'))
    response_data = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response_data += chunk
        try:
            return json.loads(response_data.decode('utf-8').strip())
        except json.JSONDecodeError:
            continue
    return None

def run_test_client(input_file: str, host: str, port: int):
    """Run TCP client test from input file"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    with open(input_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            response = send_event(sock, line)
            print(f"[{line}] -> {response}")
```

**Characteristics:**
- File-based test input
- Line-by-line event sending
- Comment support in test files
- JSON response parsing

### Pattern 6: Async WebSocket Testing

**File:** `iidx_bpl_scoreboard/testbench/test_relay.py`

```python
async def mock_browser():
    """Simulate browser client"""
    async with websockets.connect("ws://localhost:8080") as ws:
        message_count = 0
        while message_count < 5:
            msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(msg)
            print(f"[Browser] Received: {data}")
            message_count += 1

async def mock_testbench():
    """Simulate testbench client"""
    async with websockets.connect("ws://localhost:8080") as ws:
        init_msg = {"cmd": "init", "data": {...}}
        await ws.send(json.dumps(init_msg))
        
        score_msg = {"cmd": "score", "data": {"round": 1, ...}}
        await ws.send(json.dumps(score_msg))

async def main():
    await asyncio.gather(
        mock_browser(),
        mock_testbench()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

**Characteristics:**
- Async/await pattern
- Multiple concurrent clients
- Timeout handling
- Message sequence validation

## Test Data Management

**No Formal Fixtures:** Test data is created inline or loaded from files

**Inline Test Data:**
```python
def create_test_image(width: int = 224, height: int = 224, color: tuple = (100, 150, 200)):
    """Create test image"""
    img = Image.new('RGB', (width, height), color)
    return img
```

**File-Based Test Data:**
- `iidx_bpl_scoreboard/testbench/data.json` - Team and match templates
- Input text files for state machine events
- Sample images for recognition testing

## Coverage Status

**No Coverage Tooling:** No coverage measurement configured

**Estimated Coverage by Module:**

| Module | Test Coverage | Notes |
|--------|---------------|-------|
| `iidx_state_reco/` | Low | No automated tests; manual training validation |
| `iidx_score_reco/` | Medium | `test.py` covers basic recognition paths |
| `iidx_state_machine/` | High | Comprehensive unit tests in `test_state_machine_manager.py` |
| `obs_manager/` | High | Both mock and integration tests |
| `iidx_bpl_scoreboard/` | Medium | Testbench for WebSocket protocol |
| `tpl_scene_switcher/` | Low | No tests detected |

## Testing Best Practices Observed

1. **Mock External Dependencies:** Tests use mocks for OBS WebSocket, inference servers
2. **Test Both Modes:** Mock mode for CI, real mode for manual integration testing
3. **Clear Test Output:** Visual indicators (✓/✗) and descriptive messages
4. **Argument Parsing:** Tests accept command-line arguments for configuration
5. **Error Context:** Tests provide helpful error messages for setup failures

## Testing Gaps

1. **No Automated CI:** No GitHub Actions, GitLab CI, or similar
2. **No Regression Suite:** No single command to run all tests
3. **No Performance Benchmarks:** Only informal speed testing in `infer.py`
4. **No Property-Based Testing:** All tests use fixed inputs
5. **No Mock for All External Services:** Some services require real connections

## Recommendations for New Tests

**When adding new features:**
1. Create `test_<feature>.py` in the same directory
2. Use `unittest.mock.Mock` for external dependencies
3. Include both success and failure test cases
4. Add command-line interface for configuration
5. Print clear pass/fail indicators

**Example template:**
```python
#!/usr/bin/env python3
"""Test module for new_feature."""

import sys
from unittest.mock import Mock, patch

def test_success_case():
    """Test successful operation."""
    # Setup
    mock_dep = Mock()
    mock_dep.method.return_value = expected_value
    
    # Execute
    result = new_feature.operation(mock_dep)
    
    # Verify
    assert result == expected_value, f"Expected {expected_value}, got {result}"
    print("[✓] test_success_case passed")

def main():
    print("=" * 50)
    print("new_feature tests")
    print("=" * 50)
    test_success_case()
    print("All tests passed")

if __name__ == "__main__":
    main()
```

---

*Testing analysis: 2026-04-10*
