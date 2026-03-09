# Root conftest: used when pytest is run from repo root (e.g. mutmut).
# Ensures src is on the path and Django uses tests.settings so pytest-django finds the project.
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(_root, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
