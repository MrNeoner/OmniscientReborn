import os
import json
import time
import copy
import threading

try:
    from android_utils import log
except Exception:
    def log(msg): print(msg)

class DataStorage:
    def __init__(self, data_file_path):
        self.file_path = data_file_path
        self._lock = threading.RLock()
        self.tracked_users = {}
        self.last_flush = 0
        self._load()

    def _load(self):
        with self._lock:
            if os.path.exists(self.file_path):
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self.tracked_users = data
                            return
                except Exception as e:
                    log(f"[Omniscient Reborn] Error loading storage: {e}")
            self.tracked_users = {}

    def save(self, force=False):
        now = time.time()
        with self._lock:
            if not force and (now - self.last_flush < 5.0):
                return
            self.last_flush = now
            try:
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                snapshot = copy.deepcopy(self.tracked_users)
                temp_path = self.file_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, ensure_ascii=False, indent=2)
                if os.path.exists(self.file_path):
                    os.replace(temp_path, self.file_path)
                else:
                    os.rename(temp_path, self.file_path)
            except Exception as e:
                log(f"[Omniscient Reborn] Error saving storage: {e}")

    def get_user(self, user_id):
        with self._lock:
            return self.tracked_users.get(str(user_id))

    def add_user(self, user_id, name="", username=""):
        uid = str(user_id)
        with self._lock:
            if uid not in self.tracked_users:
                self.tracked_users[uid] = {
                    "id": int(user_id),
                    "name": name or f"User {user_id}",
                    "username": username or "",
                    "added_at": int(time.time()),
                    "last_seen": 0,
                    "last_status": "offline",
                    "current_session_start": 0,
                    "sessions": [],
                    "events": [],
                    "settings": {
                        "online": True,
                        "offline": True,
                        "read": True,
                        "typing": True,
                        "reactions": True
                    }
                }
            else:
                if name: self.tracked_users[uid]["name"] = name
                if username: self.tracked_users[uid]["username"] = username
            self.save(force=True)
            return self.tracked_users[uid]

    def remove_user(self, user_id):
        uid = str(user_id)
        with self._lock:
            if uid in self.tracked_users:
                del self.tracked_users[uid]
                self.save(force=True)
                return True
        return False

    def list_users(self):
        with self._lock:
            return copy.deepcopy(list(self.tracked_users.values()))

    def get_users_count(self):
        with self._lock:
            return len(self.tracked_users)

    def record_online(self, user_id, timestamp=None):
        uid = str(user_id)
        ts = int(timestamp or time.time())
        with self._lock:
            user = self.tracked_users.get(uid)
            if not user:
                return False
            if user.get("last_status") == "online":
                return False
            user["last_status"] = "online"
            user["current_session_start"] = ts
            user["last_seen"] = ts
            self._add_event(user, "online", ts)
            self.save()
            return True

    def record_offline(self, user_id, timestamp=None):
        uid = str(user_id)
        ts = int(timestamp or time.time())
        duration = 0
        with self._lock:
            user = self.tracked_users.get(uid)
            if not user:
                return False, 0
            if user.get("last_status") == "offline":
                return False, 0
            user["last_status"] = "offline"
            user["last_seen"] = ts
            start = user.get("current_session_start", 0)
            if start and ts >= start:
                duration = ts - start
                if duration > 0:
                    sessions = user.setdefault("sessions", [])
                    sessions.append({"start": start, "end": ts, "duration": duration})
                    if len(sessions) > 500:
                        user["sessions"] = sessions[-500:]
            user["current_session_start"] = 0
            self._add_event(user, "offline", ts, {"duration": duration})
            self.save()
            return True, duration

    def record_action(self, user_id, action_type, details=None):
        uid = str(user_id)
        ts = int(time.time())
        with self._lock:
            user = self.tracked_users.get(uid)
            if not user:
                return
            self._add_event(user, action_type, ts, details)
            self.save()

    def _add_event(self, user, event_type, ts, details=None):
        events = user.setdefault("events", [])
        events.append({
            "type": event_type,
            "ts": ts,
            "details": details or {}
        })
        if len(events) > 300:
            user["events"] = events[-300:]

    def get_events_today_count(self):
        now = time.time()
        start_of_day = now - (now % 86400)
        count = 0
        with self._lock:
            for u in self.tracked_users.values():
                for ev in u.get("events", []):
                    if ev.get("ts", 0) >= start_of_day:
                        count += 1
        return count

    def clear_all_events(self):
        with self._lock:
            for u in self.tracked_users.values():
                u["sessions"] = []
                u["events"] = []
                u["current_session_start"] = 0
            self.save(force=True)
