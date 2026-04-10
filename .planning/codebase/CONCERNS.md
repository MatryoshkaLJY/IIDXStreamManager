# Codebase Concerns

**Analysis Date:** 2026-04-10

## Summary

This document identifies technical debt, security concerns, and potential issues in the IIDX Stream Manager codebase. The project is a comprehensive toolset for beatmania IIDX arcade game streaming, consisting of multiple Python modules for state recognition, score recognition, OBS integration, and broadcasting overlays.

---

## Security Concerns

### Hardcoded Credentials

**Issue:** Default passwords are hardcoded in source files.

- **File:** `obs_manager/test_obs_manager.py` (line 296, 449)
  - Default password: `"1145141919"` in `test_real_obs()` function and argument parser
  - Impact: Test code contains a hardcoded password that could be used in production
  - Fix: Remove hardcoded defaults, require explicit password input

- **File:** `obs_manager/obs_manager.py` (line 17)
  - Default password in docstring example: `password="1145141919"`
  - Impact: Documentation suggests using a weak default password
  - Fix: Update docstring to use placeholder like `"your_password"`

- **File:** `tpl_scene_switcher/streamlit_app.py` (line 19)
  - Default password: `value="123456"` in Streamlit UI
  - Impact: UI suggests weak default password
  - Fix: Use empty string default with validation

- **File:** `tpl_scene_switcher/switcher.py` (line 7)
  - Default password in constructor: `password="123456"`
  - Impact: Class instantiation uses weak default
  - Fix: Require explicit password parameter

### Configuration File Storage

**Issue:** Sensitive configuration stored in JSON files without encryption.

- **File:** `obs_manager/monitor_config.json`
  - Contains `obs_password` field (currently empty in committed version)
  - Risk: Users may accidentally commit passwords to version control
  - Fix: Use environment variables or separate secrets file with `.gitignore`

### Path Traversal Risk

**Issue:** Insufficient path validation in file serving endpoints.

- **File:** `iidx_state_reco/webapp.py` (line 127-132)
  ```python
  @app.route("/img/<path:session>/<filename>")
  def serve_image(session, filename):
      path = os.path.join(BASE, session, filename)
      if not os.path.abspath(path).startswith(BASE):
          return "Forbidden", 403
      return send_file(path)
  ```
  - Risk: Path traversal via `session` parameter with `../` sequences
  - Current mitigation only checks after `os.path.abspath()`
  - Fix: Validate session and filename components separately before joining

- **File:** `iidx_state_reco/webapp.py` (line 261-273)
  ```python
  @app.route("/browse_img")
  def browse_img():
      path = request.args.get("path", "")
      path = os.path.normpath(path)
      if not os.path.isabs(path):
          return "Forbidden", 403
  ```
  - Risk: Accepts any absolute path on the filesystem
  - Fix: Implement allowlist of accessible directories

---

## Technical Debt

### Code Duplication

**Issue:** Model loading and inference code duplicated across files.

- **Files:**
  - `iidx_state_reco/webapp.py` (lines 195-213, 302-317): Duplicate model loading in `api_infer()` and `api_browse_infer()`
  - Both functions load the same model with identical code
  - Fix: Extract to shared function `_load_model(model_path, labels_path)`

- **Files:**
  - `iidx_state_reco/infer.py` (lines 42-50): `build_model()` uses EfficientNet-B3
  - `iidx_state_reco/train.py` (lines 114-119): `build_model()` uses MobileNetV3-Small
  - Inconsistency: Training and inference use different architectures
  - Fix: Standardize on single architecture or make configurable

### Large Files Exceeding Recommended Size

**Issue:** Several files exceed the 400-line recommended limit.

| File | Lines | Concern |
|------|-------|---------|
| `iidx_state_machine/state_machine.py` | 755 | Multiple responsibilities: state machine, logging, TCP server, multi-machine manager |
| `obs_manager/web_monitor.py` | 683 | Flask app, data models, monitoring logic, API routes all in one file |
| `obs_manager/obs_manager.py` | 639 | OBS integration, inference clients, state machine integration, multi-machine support |
| `iidx_state_reco/annotate.py` | 509 | GUI tool with mixed UI and business logic |

**Recommendations:**
- Split `state_machine.py` into: `state_machine.py`, `state_machine_manager.py`, `tcp_server.py`
- Split `web_monitor.py` into: `app.py`, `models.py`, `monitor_service.py`, `routes/`
- Split `obs_manager.py` into: `obs_client.py`, `inference_client.py`, `machine_manager.py`

### Model Architecture Inconsistency

**Issue:** Training and inference use different model architectures.

- **Training** (`train.py`, `export_onnx.py`): Uses MobileNetV3-Small
- **Inference** (`infer.py`): Uses EfficientNet-B3
- Impact: Exported ONNX model may not work with inference script expecting different architecture
- Fix: Standardize architecture selection via configuration

### Empty Return Statements

**Issue:** Functions return empty collections without clear semantics.

- **File:** `iidx_state_reco/webapp.py` (lines 82, 149)
  ```python
  return {}
  ```
  - Context: Error handling in annotation loading
  - Risk: Caller may not distinguish between "no data" and "error occurred"
  - Fix: Return explicit error responses or raise exceptions

- **File:** `iidx_bpl_scoreboard/testbench/testbench.py` (lines 95, 131)
  ```python
  return []
  ```
  - Context: Player selection failure cases
  - Risk: Silent failures in match generation
  - Fix: Log warnings or raise exceptions for empty selections

---

## Error Handling Issues

### Bare Exception Handling

**Issue:** Generic exception catching masks errors.

- **File:** `obs_manager/web_monitor.py` (lines 275-279)
  ```python
  except Exception as e:
      error_msg = str(e)
      if machine_id in _machine_statuses:
          _machine_statuses[machine_id].error_message = error_msg
      add_log("error", f"[{machine_id}] 处理帧失败: {error_msg}")
  ```
  - Catches all exceptions without differentiation
  - May hide programming errors that should crash the application
  - Fix: Catch specific exceptions, allow unexpected errors to propagate

### Silent Failures

**Issue:** Errors are logged but not propagated.

- **File:** `iidx_state_reco/annotate.py` (lines 268-269)
  ```python
  except Exception:
      pass
  ```
  - Thumbnail loading failures are silently ignored
  - Users see blank thumbnails without knowing why
  - Fix: Log error details or show user notification

- **File:** `obs_manager/obs_manager.py` (lines 290-293)
  ```python
  try:
      _obs_manager.disconnect()
  except:
      pass
  ```
  - Cleanup failures ignored
  - Fix: Log disconnection errors for debugging

### Missing Input Validation

**Issue:** User inputs not validated before use.

- **File:** `iidx_state_reco/webapp.py` (line 186)
  ```python
  model_path = raw_model if os.path.isabs(raw_model) else os.path.join(BASE, raw_model)
  ```
  - No validation of `raw_model` for path traversal attempts
  - Fix: Validate model path is within allowed directories

---

## Performance Concerns

### Threading Without Pool

**Issue:** New thread created per client connection without limits.

- **File:** `iidx_state_reco/serve.py` (lines 147-152)
  ```python
  while True:
      conn, addr = server.accept()
      t = threading.Thread(target=handle_client, ...)
      t.start()
  ```
  - Risk: Unbounded thread creation under high load
  - Fix: Use ThreadPoolExecutor with max_workers limit

- **File:** `iidx_score_reco/serve.py` (lines 260-269)
  - Same pattern in score recognition service

### No Request Timeouts

**Issue:** Socket operations lack timeouts.

- **File:** `obs_manager/obs_manager.py` (lines 233-240)
  ```python
  sock.sendall(data)
  response = sock.recv(256).decode().strip()
  ```
  - `recv()` may block indefinitely if server hangs
  - Fix: Set socket timeout before operations

### Memory Leaks in Caching

**Issue:** Model cache grows without bounds.

- **File:** `iidx_state_reco/webapp.py` (lines 14, 195-213)
  ```python
  _infer_cache = {}
  ```
  - Models loaded into cache are never evicted
  - Loading many different models could exhaust memory
  - Fix: Implement LRU cache with size limit

---

## Documentation Gaps

### Missing API Documentation

**Issue:** No formal API documentation for services.

- TCP protocol for state recognition (`serve.py`) is documented in docstrings only
- Score recognition protocol lacks formal specification
- WebSocket protocol for BPL scoreboard partially documented in `app.js` comments
- Fix: Create `API.md` with complete protocol specifications

### Missing Setup Documentation

**Issue:** No comprehensive setup guide.

- No root-level `requirements.txt` for all dependencies
- No Docker configuration for easy deployment
- No environment variable documentation
- Fix: Create setup documentation and dependency management

### Incomplete Type Hints

**Issue:** Inconsistent type annotation coverage.

- **File:** `iidx_state_reco/webapp.py`
  - Missing return type annotations for route handlers
  - Missing type hints for global variables

- **File:** `obs_manager/obs_manager.py`
  - `MachineConfig` dataclass lacks type hints for some fields

---

## Dependency Risks

### Outdated Dependencies

**Issue:** Dependency versions not pinned.

- **File:** `tpl_scene_switcher/requirements.txt`
  ```
  streamlit>=1.28.0
  obs-websocket-py>=0.5.3
  pyserial>=3.5
  ```
  - Uses `>=` which may pull incompatible major versions
  - Fix: Use `~=` for compatible version ranges or exact pins

### Missing Dependency Files

**Issue:** No centralized dependency management.

- No root `requirements.txt` or `pyproject.toml`
- Each module has separate (or missing) dependency documentation
- No lock files for reproducible builds
- Fix: Create centralized dependency management with Poetry or pip-tools

### Optional Dependencies Not Declared

**Issue:** Optional features import without checking.

- **File:** `iidx_state_reco/serve.py` (lines 117, 71)
  ```python
  import onnxruntime as ort
  ```
  - Required for serving but not listed in any requirements file
  - Fix: Create `requirements-serve.txt` or extras in setup.py

---

## Testing Gaps

### Missing Unit Tests

**Issue:** No comprehensive test suite.

- Only `test_obs_manager.py`, `test_score_reco.py`, `test_state_machine_manager.py` exist
- No tests for `webapp.py`, `serve.py`, `recognizer.py`
- No integration tests between modules
- Fix: Implement pytest-based test suite with coverage reporting

### Test Files Contain Production Code

**Issue:** Test files mix testing and utility functionality.

- **File:** `obs_manager/test_obs_manager.py` (465 lines)
  - Contains interactive test runner with argparse
  - Should be split into actual tests and a utility script

---

## Configuration Issues

### Hardcoded Configuration Values

**Issue:** Magic numbers and strings scattered throughout code.

- **File:** `iidx_score_reco/serve.py` (lines 37-42)
  ```python
  DEFAULT_ROIS = [
      ((1547, 488), (1700, 517)),
      ((1547, 549), (1700, 581)),
      ((1400, 488), (1547, 517)),
      ((1400, 549), (1547, 581)),
  ]
  ```
  - ROI coordinates hardcoded for specific resolution
  - Fix: Move to configuration file with resolution profiles

- **File:** `iidx_state_reco/serve.py` (lines 47-48)
  ```python
  MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
  STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
  ```
  - Image normalization constants hardcoded
  - Fix: Make configurable or document source (ImageNet)

### Missing Configuration Validation

**Issue:** Configuration files not validated at load time.

- **File:** `obs_manager/web_monitor.py` (lines 602-660)
  - `load_config_on_startup()` loads JSON without schema validation
  - Invalid config values may cause runtime errors later
  - Fix: Add configuration schema validation with pydantic or similar

---

## Files Referenced

| File | Purpose | Concerns |
|------|---------|----------|
| `obs_manager/obs_manager.py` | OBS WebSocket integration | Hardcoded password, large file size, missing timeouts |
| `obs_manager/web_monitor.py` | Web-based monitoring | Large file, generic exception handling, no config validation |
| `obs_manager/test_obs_manager.py` | Test utilities | Hardcoded password, mixes test and utility code |
| `obs_manager/monitor_config.json` | Configuration storage | Plaintext password field |
| `iidx_state_reco/webapp.py` | Flask annotation webapp | Path traversal risk, code duplication, unbounded cache |
| `iidx_state_reco/serve.py` | TCP inference server | Unbounded threading, no timeouts |
| `iidx_state_reco/infer.py` | Inference script | Wrong model architecture vs training |
| `iidx_state_reco/train.py` | Training script | Architecture mismatch with inference |
| `iidx_state_reco/annotate.py` | Desktop annotation tool | Large file, silent failures |
| `iidx_score_reco/serve.py` | Score recognition service | Unbounded threading |
| `iidx_score_reco/recognizer.py` | Template matching | Hardcoded thresholds and sizes |
| `iidx_state_machine/state_machine.py` | State machine | Very large file, multiple responsibilities |
| `tpl_scene_switcher/switcher.py` | Scene switching | Hardcoded password |
| `tpl_scene_switcher/streamlit_app.py` | Streamlit UI | Hardcoded password |
| `iidx_bpl_scoreboard/testbench/testbench.py` | Testbench | Empty return fallbacks |

---

## Priority Recommendations

### High Priority (Security)
1. Remove all hardcoded passwords from source code
2. Implement proper path validation in file serving endpoints
3. Move sensitive configuration to environment variables
4. Add authentication to web interfaces

### Medium Priority (Stability)
1. Fix model architecture inconsistency between training and inference
2. Add bounded thread pools to servers
3. Implement proper exception handling with specific exception types
4. Add configuration schema validation

### Low Priority (Maintainability)
1. Split large files into modules
2. Create centralized dependency management
3. Add comprehensive test suite
4. Create formal API documentation

---

*Concerns audit: 2026-04-10*
