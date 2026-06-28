import os
import sys

# Bootstrap: add src/backend (3 levels up from features/) so shared is importable
_backend_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from shared.behave_setup import configure_function_paths

configure_function_paths(__file__)
