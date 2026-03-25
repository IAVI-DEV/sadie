"""Pandas version detection and compatibility utilities.

Provides version-aware helpers so the rest of the codebase can support
pandas 1.5 through pandas 3.x without scattering version checks everywhere.

Exports
-------
PANDAS_VERSION : tuple[int, ...]
    Parsed ``pd.__version__`` as a tuple of ints, e.g. ``(2, 3, 3)``.
_is_internal_manager : Callable[[Any], bool]
    Returns ``True`` when *data* is a pandas internal manager object
    (``BlockManager``, ``SingleBlockManager``, or their pandas 3 replacements).
NAType : type
    The type of ``pd.NA``.  Works on pandas ≥ 1.5.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# PANDAS_VERSION
# ---------------------------------------------------------------------------
PANDAS_VERSION: tuple[int, ...] = tuple(int(x) for x in pd.__version__.split(".")[:3])

# ---------------------------------------------------------------------------
# _is_internal_manager
# ---------------------------------------------------------------------------
# pandas 2.x uses BlockManager / SingleBlockManager.
# pandas 3.x may rename or replace them.  We keep a version-appropriate set
# of class names so that DataFrame / Series subclass constructors can detect
# when pandas passes an internal manager instead of user data.
if PANDAS_VERSION >= (3,):
    _INTERNAL_MANAGER_NAMES: frozenset[str] = frozenset(
        {
            "BlockManager",
            "SingleBlockManager",
            # pandas 3 potential replacements
            "BlockManagerLike",
            "SingleBlockManagerLike",
        }
    )
else:
    _INTERNAL_MANAGER_NAMES = frozenset({"BlockManager", "SingleBlockManager"})


def _is_internal_manager(data: Any) -> bool:
    """Return ``True`` if *data* is a pandas internal manager object.

    Parameters
    ----------
    data : Any
        The value to check — typically the first positional argument
        passed to a ``DataFrame`` or ``Series`` subclass ``__init__``.

    Returns
    -------
    bool
    """
    if data is None:
        return False
    return data.__class__.__name__ in _INTERNAL_MANAGER_NAMES


# ---------------------------------------------------------------------------
# NAType
# ---------------------------------------------------------------------------
try:
    from pandas._libs.missing import NAType as NAType  # pandas ≥ 1.0
except ImportError:
    NAType: type = type(pd.NA)  # type: ignore[no-redef]
