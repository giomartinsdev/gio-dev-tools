import sys
from unittest.mock import MagicMock

# Stub production-only packages that are unavailable in the test environment.
# fastapi lives in the Dockerfile base image, not in requirements.txt.
# httpx is in requirements.txt but may be absent in a minimal local env.
for _mod in ("fastapi", "fastapi.requests", "fastapi.responses", "httpx"):
    try:
        __import__(_mod)
    except ImportError:
        sys.modules[_mod] = MagicMock()

import os

_backend_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from shared.behave_setup import configure_function_paths

configure_function_paths(__file__)
