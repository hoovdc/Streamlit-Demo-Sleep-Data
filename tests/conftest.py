import sys, pathlib
# Ensure project root is in sys.path so that `src` package can be imported during tests
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR)) 