import importlib.util
import sys

def load_plugin(path, api):
    spec = importlib.util.spec_from_file_location("user_plugin", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["user_plugin"] = mod
    spec.loader.exec_module(mod)
    # Optionally, call a register(api) function if present
    if hasattr(mod, "register"):
        mod.register(api)
    return mod 