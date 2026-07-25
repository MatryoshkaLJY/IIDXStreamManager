import sys
from pathlib import Path

IIDX_DIRECTOR_ROOT = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = IIDX_DIRECTOR_ROOT.parent

# 供 `import src.*`（本模块）与 `import obs_manager.*`（兄弟模块，供 obs/monitor 复用）
for path in (str(IIDX_DIRECTOR_ROOT), str(MONOREPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
