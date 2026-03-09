import os
import sys

_src = os.path.dirname(os.path.abspath(__file__))
if _src not in sys.path:
    sys.path.insert(0, _src)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
