from typing import Any, Callable, Dict, Generator, List, Optional

def paginate(
    fetch_page: Callable[[Optional[str]], Dict[str, Any]],
    max_items: Optional[int] = None,
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Generic cursor-based pagination helper.

    :param fetch_page: Function that accepts an optional cursor string and returns a
                       Twitch-style response with "data" and optional "pagination.cursor".
    :param max_items: Optional maximum number of items to return across all pages.
    :yield: Lists of items from each page.
    """
    cursor: Optional[str] = None
    total_returned = 0

    while True:
        response = fetch_page(cursor)
        data = response.get("data") or []
        if not isinstance(data, list):
            data = []

        if not data:
            break

        if max_items is not None:
            remaining = max_items - total_returned
            if remaining <= 0:
                break
            data = data[:remaining]

        yield data
        total_returned += len(data)

        if max_items is not None and total_returned >= max_items:
            break

        pagination = response.get("pagination") or {}
        cursor = pagination.get("cursor")
        if not cursor:
            break