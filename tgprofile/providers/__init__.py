"""Provider registry. Each provider is an async fn(ctx) -> str (the new name)."""

REGISTRY = {}


def provider(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


# Importing builtin populates REGISTRY via the @provider decorator.
from . import builtin  # noqa: E402,F401
