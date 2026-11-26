"""Test isolation helper. Several test files install fake `service_*` / library modules in sys.modules and never remove them,
so a test that runs later in the same `unittest discover` process can pick up a fake instead of the real module.
`fresh()` runs a block on a clean module cache and puts the previous cache back afterwards, so nobody else is affected.
Use `setUpModule = _isolate.set_up` / `tearDownModule = _isolate.tear_down` for a whole test file."""
import contextlib
import importlib.util
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_FAKE_ROOTS = ("pymongo", "motor", "aiogram", "aiohttp", "redis", "bson")
_stack = []


def _real_dep(root):
    try:
        return importlib.util.find_spec(root) is not None
    except (ImportError, ValueError):
        return False


def _enter():
    saved = {}
    for name in list(sys.modules):
        root = name.split(".")[0]
        mod = sys.modules[name]
        is_project = not root.startswith("test_") and root != "_isolate" and os.path.exists(os.path.join(_ROOT, root + ".py"))
        is_fake_dep = root in _FAKE_ROOTS and getattr(mod, "__file__", None) is None and not _real_dep(root)
        if is_project or is_fake_dep:
            saved[name] = sys.modules.pop(name)
    return saved, set(sys.modules)


def _exit(state):
    saved, before = state
    for name in set(sys.modules) - before:
        del sys.modules[name]
    sys.modules.update(saved)


@contextlib.contextmanager
def fresh():
    state = _enter()
    try:
        yield
    finally:
        _exit(state)


def snapshot_fakes():
    """The fake modules a test file installed for itself (no file on disk): put back by set_up(keep=...) after the cache is cleaned."""
    out = {}
    for name, mod in list(sys.modules.items()):
        root = name.split(".")[0]
        if getattr(mod, "__file__", None) is None and (root in _FAKE_ROOTS or os.path.exists(os.path.join(_ROOT, root + ".py"))) \
                and not root.startswith("test_") and root != "_isolate":
            out[name] = mod
    return out


def begin():
    """Start of a test file that builds its own fakes while it is imported: clean cache from here on."""
    return _enter()


def end(state):
    """End of that import phase: returns every module the file loaded (its fakes and the real code built on them) and puts the
    previous cache back, so other test files never see them. Pass the result to set_up(keep=...)."""
    saved, before = state
    keep = {n: sys.modules[n] for n in set(sys.modules) - before}
    _exit(state)
    return keep


def set_up(keep=None):
    _stack.append(_enter())
    if keep:
        sys.modules.update(keep)


def tear_down():
    if _stack:
        _exit(_stack.pop())
