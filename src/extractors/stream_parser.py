from typing import Any, Dict, List, Optional

def _extract_tags(raw: Dict[str, Any]) -> List[str]:
    tags = raw.get("tag_ids") or raw.get("tags") or []
    if isinstance(tags, list):
        return [str(t) for t in tags]
    return []

def parse_stream(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize Twitch stream data if the channel is currently live.
    """
    if not raw:
        return None

    try:
        stream_id = str(raw.get("id") or "")
        title = raw.get("title") or ""
        game_name = raw.get("game_name") or raw.get("game") or ""
        viewer_count = int(raw.get("viewer_count") or 0)
        started_at = raw.get("started_at") or ""
        language = raw.get("language") or ""
        thumbnail_url = raw.get("thumbnail_url") or ""

        return {
            "id": stream_id,
            "title": title,
            "gameName": game_name,
            "viewerCount": viewer_count,
            "startedAt": started_at,
            "language": language,
            "tags": _extract_tags(raw),
            "thumbnailURL": thumbnail_url,
        }
    except Exception:
        # If anything goes wrong, treat as no live stream instead of breaking the scraper
        return None