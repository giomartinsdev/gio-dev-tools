import os
import sys


def configure_function_paths(env_file):
    """Set up sys.path for a function's BDD tests.

    env_file must be the environment.py inside features/ — this function
    resolves function_root (features/../) and backend_root (features/../../../).
    """
    features_dir = os.path.dirname(os.path.abspath(env_file))
    function_root = os.path.normpath(os.path.join(features_dir, '..'))
    backend_root = os.path.normpath(os.path.join(features_dir, '..', '..', '..'))
    for path in [function_root, backend_root]:
        if path not in sys.path:
            sys.path.insert(0, path)
