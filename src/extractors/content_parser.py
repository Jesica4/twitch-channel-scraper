from typing import Any, Dict, Optional

def parse_video(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize Twitch video data into the expected latestVideo schema.
    """
    if not raw:
        return None

    try:
        # Twitch videos: id, title, duration, thumbnail_url, url, created_at
        video_id = str(raw.get("id") or "")
        title = raw.get("title") or ""
        thumbnail_url = raw.get("thumbnail_url") or ""
        url = raw.get("url") or ""
        created_at = raw.get("created_at") or raw.get("published_at") or ""
        length_seconds = 0

        # Duration often comes as "3h5m10s" or "59s"
        duration = raw.get("duration") or ""
        if isinstance(duration, str) and duration:
            total = 0
            num = ""
            for ch in duration:
                if ch.isdigit():
                    num += ch
                else:
                    if num:
                        value = int(num)
                        if ch == "h":
                            total += value * 3600
                        elif ch == "m":
                            total += value * 60
                        elif ch == "s":
                            total += value
                        num = ""
            length_seconds = total or length_seconds

        return {
            "id": video_id,
            "title": title,
            "lengthSeconds": length_seconds,
            "thumbnailURL": thumbnail_url,
            "url": url,
            "publishedAt": created_at,
        }
    except Exception:
        return None

def parse_clip(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize Twitch clip data into the expected topClip schema.
    """
    if not raw:
        return None

    try:
        clip_id = str(raw.get("id") or "")
        title = raw.get("title") or ""
        thumbnail_url = raw.get("thumbnail_url") or ""
        url = raw.get("url") or ""
        created_at = raw.get("created_at") or ""
        duration_seconds = 0

        dur = raw.get("duration")
        try:
            if dur is not None:
                duration_seconds = int(float(dur))
        except (TypeError, ValueError):
            duration_seconds = 0

        return {
            "id": clip_id,
            "title": title,
            "durationSeconds": duration_seconds,
            "thumbnailURL": thumbnail_url,
            "url": url,
            "createdAt": created_at,
        }
    except Exception:
        return None

def parse_schedule(raw: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Extract the next upcoming scheduled stream, if available.
    Twitch schedule responses contain segments with start_time/end_time.
    """
    if not raw:
        return None

    # Try to support both {"segments": [...]} and {"data": {"segments": [...]}} shapes.
    segments = None
    if isinstance(raw, dict):
        if "segments" in raw:
            segments = raw.get("segments")
        elif "data" in raw and isinstance(raw["data"], dict):
            segments = raw["data"].get("segments")

    if not segments or not isinstance(segments, list):
        return None

    # Pick the earliest upcoming segment
    segment = segments[0]
    try:
        return {
            "id": str(segment.get("id") or ""),
            "title": segment.get("title") or "",
            "startTime": segment.get("start_time") or "",
            "endTime": segment.get("end_time") or "",
            "category": (segment.get("category") or {}).get("name", ""),
            "cancelledUntil": segment.get("canceled_until") or "",
        }
    except Exception:
        return None