"""Re-export do catálogo desde instruments.py para uso conciso."""
from .instruments import (  # noqa
    CATALOG, CATALOG_BY_ID, Instrument, assign_unique_id, base_id_of,
)
