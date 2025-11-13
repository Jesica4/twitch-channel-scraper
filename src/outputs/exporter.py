import json
import logging
from pathlib import Path
from typing import Any, Iterable, List, Dict

logger = logging.getLogger(__name__)

def export_to_json(records: Iterable[Dict[str, Any]], path: Path) -> None:
    """
    Export records to a pretty-printed JSON file.
    """
    data: List[Dict[str, Any]] = list(records)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("Wrote %d records to JSON file %s", len(data), path)