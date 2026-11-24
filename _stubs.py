"""Test helper: import a service module without MongoDB / Telegram libraries installed.
Only modules that really cannot be imported are replaced, and the replacements are removed again right after the
import, so other test files are never affected. Tests patch the names they need on the returned module."""
import importlib
import sys
import types


async def _noop(*a, **k):
    return None


_STUBS = {
    "pymongo": {"ReturnDocument": types.SimpleNamespace(AFTER=1, BEFORE=0)},
    "database": {"col": lambda n: None, "game_settings": _noop, "try_cooldown": _noop, "bump_counter": _noop, "counter_get": _noop},
    "service_log": {"log_event": _noop},
    "service_player": {"add_coins": _noop, "add_xp": _noop, "bump_quest": _noop, "get_char": _noop,
                       "max_hp": lambda *a, **k: 1, "max_reiatsu": lambda *a, **k: 1},
    "service_worldcore": {"mods_for": _noop},
}


def import_with_stubs(name: str):
    if name in sys.modules:
        return sys.modules[name]
    added = []
    for mod_name, attrs in _STUBS.items():
        if mod_name in sys.modules:
            continue
        try:
            importlib.import_module(mod_name)
        except ImportError:
            m = types.ModuleType(mod_name)
            m.__dict__.update(attrs)
            sys.modules[mod_name] = m
            added.append(mod_name)
    try:
        return importlib.import_module(name)
    finally:
        for mod_name in added:
            sys.modules.pop(mod_name, None)
