from typing import Any, Dict, Optional

def _extract_channel_id(raw: Dict[str, Any]) -> str:
    return str(
        raw.get("id")
        or raw.get("channelId")
        or raw.get("broadcaster_id")
        or raw.get("_id", "")
    )

def _extract_display_name(raw: Dict[str, Any]) -> str:
    return (
        raw.get("display_name")
        or raw.get("displayName")
        or raw.get("broadcaster_name")
        or raw.get("user_name")
        or raw.get("login")
        or ""
    )

def _extract_login(raw: Dict[str, Any]) -> str:
    return (
        raw.get("broadcaster_login")
        or raw.get("login")
        or raw.get("name")
        or _extract_display_name(raw).lower()
    )

def _extract_description(raw: Dict[str, Any]) -> str:
    return raw.get("description") or raw.get("bio") or ""

def _extract_profile_image_url(raw: Dict[str, Any]) -> str:
    return (
        raw.get("profile_image_url")
        or raw.get("profileImageURL")
        or raw.get("thumbnail_url")
        or ""
    )

def _extract_followers_count(raw: Dict[str, Any]) -> int:
    count = raw.get("followersCount") or raw.get("followers") or raw.get("follower_count")
    try:
        return int(count) if count is not None else 0
    except (TypeError, ValueError):
        return 0

def _extract_is_partner(raw: Dict[str, Any]) -> bool:
    if "isPartner" in raw:
        return bool(raw["isPartner"])
    if "broadcaster_type" in raw:
        return raw["broadcaster_type"] == "partner"
    return bool(raw.get("partner") or raw.get("is_partner"))

def build_channel_record(
    channel_raw: Dict[str, Any],
    stream: Optional[Dict[str, Any]],
    latest_video: Optional[Dict[str, Any]],
    top_clip: Optional[Dict[str, Any]],
    next_schedule: Optional[Dict[str, Any]],
    keyword: str,
) -> Dict[str, Any]:
    """
    Build a normalized channel record that matches the schema described in the README.
    """
    channel_id = _extract_channel_id(channel_raw)
    display_name = _extract_display_name(channel_raw)
    login = _extract_login(channel_raw)
    description = _extract_description(channel_raw)
    profile_image_url = _extract_profile_image_url(channel_raw)
    followers_count = _extract_followers_count(channel_raw)
    is_partner = _extract_is_partner(channel_raw)

    record: Dict[str, Any] = {
        "channelId": channel_id,
        "displayName": display_name,
        "login": login,
        "description": description,
        "profileImageURL": profile_image_url,
        "followersCount": followers_count,
        "isPartner": is_partner,
        "stream": stream,
        "latestVideo": latest_video,
        "topClip": top_clip,
        "nextSchedule": next_schedule,
        "keyword": keyword,
    }

    return record