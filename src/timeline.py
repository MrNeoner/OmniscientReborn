import time
from datetime import datetime

def format_duration(seconds, lang="ru"):
    is_ru = (lang == "ru")
    if seconds <= 0:
        return "0с" if is_ru else "0s"
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours}ч" if is_ru else f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}м" if is_ru else f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}с" if is_ru else f"{secs}s")
    return " ".join(parts)

def format_time(ts, include_seconds=True, lang="ru"):
    if not ts:
        return "Никогда" if lang == "ru" else "Never"
    fmt = "%H:%M:%S" if include_seconds else "%H:%M"
    return datetime.fromtimestamp(ts).strftime(fmt)

def time_ago(ts, lang="ru"):
    is_ru = (lang == "ru")
    if not ts:
        return "неизвестно" if is_ru else "unknown"
    diff = int(time.time() - ts)
    if diff < 60:
        return f"{diff} сек назад" if is_ru else f"{diff}s ago"
    if diff < 3600:
        return f"{diff // 60} мин назад" if is_ru else f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600} ч назад" if is_ru else f"{diff // 3600}h ago"
    return f"{diff // 86400} дн назад" if is_ru else f"{diff // 86400}d ago"

def get_day_stats(user_data, day_timestamp=None, lang="ru"):
    total_seconds = int(user_data.get("total_online_time", 0))
    activity = user_data.get("activity_hours", [0] * 24)
    if len(activity) != 24:
        activity = [0] * 24

    peak_hour = activity.index(max(activity)) if max(activity) > 0 else None
    sessions_log = user_data.get("sessions_log", [])

    session_count = len(sessions_log)
    if session_count == 0:
        history = user_data.get("history", [])
        for ev in history:
            txt = ev.get("text", "")
            if "Выход" in txt or "сессия" in txt or "offline" in txt.lower():
                session_count += 1
        if session_count == 0 and total_seconds > 0:
            session_count = 1

    avg_duration = total_seconds // session_count if session_count > 0 else total_seconds

    return {
        "total_seconds": total_seconds,
        "formatted_total": format_duration(total_seconds, lang=lang),
        "sessions_count": session_count,
        "avg_duration": avg_duration,
        "formatted_avg": format_duration(avg_duration, lang=lang),
        "peak_hour": f"{peak_hour:02d}:00" if peak_hour is not None else "—",
        "hourly": activity
    }
