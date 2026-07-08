import importlib
import os

SERVICES_DIR = os.path.dirname(__file__)


def get_service(module_path):
    """Import and return a scenario service module by dotted path."""
    return importlib.import_module(module_path)


def list_services():
    """Return all discoverable service modules (files in this dir excluding base/init)."""
    services = {}
    for f in sorted(os.listdir(SERVICES_DIR)):
        if f.endswith(".py") and not f.startswith("_"):
            mod_name = f"scenario_services.{f[:-3]}"
            try:
                mod = importlib.import_module(mod_name)
                services[mod.SERVICE_SLUG] = {
                    "name": mod.SERVICE_NAME,
                    "slug": mod.SERVICE_SLUG,
                    "description": mod.DESCRIPTION,
                    "module_path": mod_name,
                    "flag": getattr(mod, "FLAG", ""),
                }
            except (ImportError, AttributeError):
                pass
    return services
