"""pytest configuration — adds tests dir to sys.path and loads .env."""
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
ROOT      = TESTS_DIR.parent.parent  # cds/

# Allow test files to `from helpers import ...`
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

# Allow test files to `import rag`, `import ingest`, etc.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "phase5") not in sys.path:
    sys.path.insert(0, str(ROOT / "phase5"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
