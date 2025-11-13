import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure src directory is on sys.path so we can import sibling packages
CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent
REPO_ROOT = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.request_handler import RequestHandler  # type: ignore
from utils.pagination import paginate  # type: ignore
from extractors.channel_parser import build_channel_record  # type: ignore
from extractors.stream_parser import parse_stream  # type: ignore
from extractors.content_parser import parse_video, parse_clip, parse_schedule  # type: ignore
from outputs.exporter import export_to_json  # type: ignore

def setup_logger(level: str) -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def load_settings() -> Dict[str, Any]:
    """
    Load settings from settings.json if present, otherwise from settings.example.json.
    """
    config_dir = SRC_DIR / "config"
    primary = config_dir / "settings.json"
    fallback = config_dir / "settings.example.json"

    if primary.exists():
        path = primary
    else:
        path = fallback

    with path.open("r", encoding="utf-8") as f:
        settings = json.load(f)

    # Allow overriding via environment variables if present
    settings["clientId"] = os.getenv("TWITCH_CLIENT_ID", settings.get("clientId", ""))
    settings["accessToken"] = os.getenv("TWITCH_ACCESS_TOKEN", settings.get("accessToken", ""))

    return settings

def load_keywords(path: Path) -> List[str]:
    if not path.exists():
        logging.warning("Keywords file %s not found, using default ['warframe']", path)
        return ["warframe"]

    keywords: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            keywords.append(line)

    if not keywords:
        logging.warning("No keywords found in %s, using default ['warframe']", path)
        return ["warframe"]

    return keywords

def fetch_stream_for_user(handler: RequestHandler, user_id: str) -> Optional[Dict[str, Any]]:
    response = handler.get("/streams", params={"user_id": user_id, "first": 1})
    data = response.get("data") or []
    return data[0] if data else None

def fetch_latest_video_for_user(handler: RequestHandler, user_id: str) -> Optional[Dict[str, Any]]:
    response = handler.get("/videos", params={"user_id": user_id, "sort": "time", "first": 1})
    data = response.get("data") or []
    return data[0] if data else None

def fetch_top_clip_for_user(handler: RequestHandler, user_id: str) -> Optional[Dict[str, Any]]:
    response = handler.get("/clips", params={"broadcaster_id": user_id, "first": 1})
    data = response.get("data") or []
    return data[0] if data else None

def fetch_schedule_for_user(handler: RequestHandler, user_id: str) -> Optional[Dict[str, Any]]:
    response = handler.get("/schedule", params={"broadcaster_id": user_id, "first": 1})
    # Twitch schedule API structure is slightly different; we handle it defensively.
    schedule = response.get("data") or response.get("schedule") or {}
    if not schedule:
        return None
    return schedule

def search_channels_for_keyword(
    handler: RequestHandler,
    keyword: str,
    max_channels: int,
) -> List[Dict[str, Any]]:
    """
    Search Twitch channels by keyword and enrich them with stream, video, clip, and schedule data.
    """
    logging.info("Searching channels for keyword '%s'", keyword)

    def fetch_page(cursor: Optional[str]) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "query": keyword,
            "first": 100,
            "live_only": False,
        }
        if cursor:
            params["after"] = cursor
        return handler.get("/search/channels", params=params)

    all_channels_raw: List[Dict[str, Any]] = []
    for page in paginate(fetch_page, max_items=max_channels):
        all_channels_raw.extend(page)
        if len(all_channels_raw) >= max_channels:
            break

    logging.info("Found %d raw channels for keyword '%s'", len(all_channels_raw), keyword)

    enriched: List[Dict[str, Any]] = []

    for ch in all_channels_raw[:max_channels]:
        channel_id = str(ch.get("id") or ch.get("channelId") or "")
        if not channel_id:
            logging.debug("Skipping channel without id: %s", ch)
            continue

        try:
            stream_raw = fetch_stream_for_user(handler, channel_id)
        except Exception as e:
            logging.warning("Failed to fetch stream for %s: %s", channel_id, e)
            stream_raw = None

        try:
            video_raw = fetch_latest_video_for_user(handler, channel_id)
        except Exception as e:
            logging.warning("Failed to fetch latest video for %s: %s", channel_id, e)
            video_raw = None

        try:
            clip_raw = fetch_top_clip_for_user(handler, channel_id)
        except Exception as e:
            logging.warning("Failed to fetch top clip for %s: %s", channel_id, e)
            clip_raw = None

        try:
            schedule_raw = fetch_schedule_for_user(handler, channel_id)
        except Exception as e:
            logging.warning("Failed to fetch schedule for %s: %s", channel_id, e)
            schedule_raw = None

        stream = parse_stream(stream_raw) if stream_raw else None
        latest_video = parse_video(video_raw) if video_raw else None
        top_clip = parse_clip(clip_raw) if clip_raw else None
        next_schedule = parse_schedule(schedule_raw) if schedule_raw else None

        record = build_channel_record(
            channel_raw=ch,
            stream=stream,
            latest_video=latest_video,
            top_clip=top_clip,
            next_schedule=next_schedule,
            keyword=keyword,
        )
        enriched.append(record)

    return enriched

def main() -> None:
    settings = load_settings()
    setup_logger(settings.get("logLevel", "INFO"))

    client_id = settings.get("clientId", "").strip()
    access_token = settings.get("accessToken", "").strip()

    if not client_id or not access_token:
        logging.error(
            "Twitch clientId or accessToken missing.\n"
            "Please update src/config/settings.example.json or create src/config/settings.json "
            "with valid Twitch API credentials, or set TWITCH_CLIENT_ID/TWITCH_ACCESS_TOKEN."
        )
        sys.exit(1)

    keywords_file = REPO_ROOT / settings.get("keywordsFile", "data/keywords.sample.txt")
    output_file = REPO_ROOT / settings.get("outputFile", "data/sample_output.json")
    max_per_keyword = int(settings.get("maxChannelsPerKeyword", 50))

    handler = RequestHandler(
        base_url=settings.get("baseUrl", "https://api.twitch.tv/helix"),
        client_id=client_id,
        access_token=access_token,
        max_retries=int(settings.get("maxRetries", 3)),
        timeout=float(settings.get("timeoutSeconds", 15)),
    )

    keywords = load_keywords(keywords_file)
    logging.info("Loaded %d keywords from %s", len(keywords), keywords_file)

    all_results: List[Dict[str, Any]] = []

    for kw in keywords:
        try:
            results = search_channels_for_keyword(handler, kw, max_per_keyword)
            all_results.extend(results)
            logging.info(
                "Collected %d channels for keyword '%s' (total so far: %d)",
                len(results),
                kw,
                len(all_results),
            )
        except Exception as e:
            logging.exception("Failed to collect channels for keyword '%s': %s", kw, e)

    if not all_results:
        logging.warning("No results collected; nothing to export.")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)
    export_to_json(all_results, output_file)
    logging.info("Exported %d records to %s", len(all_results), output_file)

if __name__ == "__main__":
    main()