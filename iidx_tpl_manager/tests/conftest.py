import sys
from pathlib import Path

# obs_manager is a sibling directory to the project root.
# Add the parent of the project root so obs_manager imports work during tests.
project_root = Path(__file__).resolve().parents[1]
parent_dir = str(project_root.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
