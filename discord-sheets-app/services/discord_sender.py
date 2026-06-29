import os
import requests
from datetime import datetime, timedelta

NICKNAMES = {
    "Queen Ant": "QA",
    "Frintezza": "Tezza",
    "Core": "Core",
    "Orfen": "Orfen",
    "Zaken": "Zaken",
    "Antharas": "Antharas",
    "Valakas": "Valakas",
    "Baium": "Baium",
    "Sailren": "Sailren",
    "Anakim": "Anakim",
    "Lilith": "Lilith",
}


def _parse_boss_datetime(raw_date: str, window_start: str) -> datetime:
    """Parse DD.MM.YYYY + HH:MM into a datetime object (UTC)."""
    return datetime.strptime(f"{raw_date} {window_start}", "%d.%m.%Y %H:%M")


def _build_entries(bosses: list[dict], offset_hours: int) -> list[tuple]:
    entries = []
    for b in bosses:
        dt_utc = _parse_boss_datetime(b["date"], b["window_start"])
        regroup_utc = dt_utc - timedelta(minutes=30)
        dt_local = regroup_utc + timedelta(hours=offset_hours)
        nickname = NICKNAMES.get(b["boss"], b["boss"])
        day_month = dt_local.strftime("%d/%m")
        regroup_time = dt_local.strftime("%H:%M")
        sort_key = dt_local.strftime("%Y%m%d%H%M")
        entries.append((sort_key, day_month, nickname, regroup_time))
    entries.sort(key=lambda x: x[0])
    return entries


def _format_entries(entries: list[tuple], header: str) -> str:
    lines = [header]
    prev_date = None
    for sort_key, day_month, nickname, regroup in entries:
        date_part = sort_key[:8]
        if prev_date is not None and prev_date != date_part:
            lines.append("")
            lines.append("----------------------------------")
        lines.append("")
        lines.append(f"{day_month} - {nickname} - {regroup}")
        prev_date = date_part
    return "\n".join(lines)


def build_discord_message(bosses: list[dict]) -> str:
    entries = _build_entries(bosses, offset_hours=0)
    return _format_entries(entries, "@everyone Next Epics:")


def build_whatsapp_message(bosses: list[dict]) -> str:
    entries = _build_entries(bosses, offset_hours=-3)
    return _format_entries(entries, "Proximos Epics:")


def send_to_discord(message: str) -> dict:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL não configurado no .env")

    response = requests.post(webhook_url, json={"content": message}, timeout=10)
    response.raise_for_status()
    return {"status": "ok", "code": response.status_code}
