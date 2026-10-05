import time

try:
    from android_utils import log, run_on_ui_thread
    from client_utils import send_message, get_my_id
    from ui.bulletin import BulletinHelper
except Exception:
    def log(msg): print(msg)
    def run_on_ui_thread(cb): cb()
    send_message = None
    get_my_id = lambda acc: 0
    BulletinHelper = None

try:
    from .timeline import format_duration, format_time
except Exception:
    from timeline import format_duration, format_time

class TrackerEngine:
    def __init__(self, plugin, storage):
        self.plugin = plugin
        self.storage = storage

    def handle_status_update(self, user_id, status_obj, account=0):
        uid = str(user_id)
        user = self.storage.get_user(uid)
        if not user:
            return

        status_name = type(status_obj).__name__ if status_obj else ""
        now = int(time.time())

        if "UserStatusOnline" in status_name:
            if self.storage.record_online(uid, now):
                self._notify(user, "online", f"🟢 <b>{user['name']}</b> вошел(ла) в сеть", account)

        elif "UserStatusOffline" in status_name:
            was_offline, duration = self.storage.record_offline(uid, now)
            if was_offline:
                dur_str = format_duration(duration) if duration > 0 else "кратковременно"
                msg = f"🔴 <b>{user['name']}</b> вышел(ла) из сети\n⏱️ Сессия: <code>{dur_str}</code>"
                self._notify(user, "offline", msg, account)

        elif "UserStatusRecently" in status_name or "UserStatusLastWeek" in status_name:
            was_offline, duration = self.storage.record_offline(uid, now)
            if was_offline:
                dur_str = format_duration(duration) if duration > 0 else "неизвестно"
                msg = f"⚪ <b>{user['name']}</b> скрыл(а) статус сети\n⏱️ Сессия: <code>{dur_str}</code>"
                self._notify(user, "offline", msg, account)

    def handle_read(self, max_id, chat_id, account=0):
        uid = str(chat_id)
        user = self.storage.get_user(uid)
        if not user:
            return
        self.storage.record_action(uid, "read", {"max_id": max_id})
        msg = f"👁️ <b>{user['name']}</b> прочитал(а) ваше сообщение"
        self._notify(user, "read", msg, account)

    def handle_typing(self, chat_id, user_id, action_type, account=0):
        uid = str(user_id or chat_id)
        user = self.storage.get_user(uid)
        if not user:
            return

        action_names = {
            "typing": "печатает сообщение",
            "record-audio": "записывает голосовое...",
            "upload-audio": "отправляет аудио...",
            "record-video": "записывает видео...",
            "record-round": "записывает видеокружок...",
            "choose-sticker": "выбирает стикер..."
        }
        act_text = action_names.get(action_type, "активничает")
        self.storage.record_action(uid, f"typing_{action_type}")

        now = time.time()
        last_typ = getattr(self, f"_typ_{uid}", 0)
        if now - last_typ > 30.0:
            setattr(self, f"_typ_{uid}", now)
            msg = f"💬 <b>{user['name']}</b> {act_text}"
            self._notify(user, "typing", msg, account)

    def _notify(self, user, event_type, message_text, account=0):

        if not self.plugin.get_setting(f"track_{event_type}", True):
            return

        target_mode = self.plugin.get_setting("notify_target", 0)
        ts_now = format_time(int(time.time()), self.plugin.get_setting("show_seconds", True))
        full_msg = f"{message_text}\n🕒 <code>{ts_now}</code>"

        try:

            if target_mode == 0:
                acc = account if account is not None else 0
                my_id = get_my_id(acc) if get_my_id else 0
                if my_id and send_message:
                    send_message(my_id, full_msg, account=acc)

            elif target_mode == 1:
                clean_text = full_msg.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
                if BulletinHelper:
                    run_on_ui_thread(lambda: BulletinHelper.show_info(clean_text))

            elif target_mode == 3:
                custom_id = self.plugin.get_setting("custom_target_id", 0)
                if custom_id and send_message:
                    acc = account if account is not None else 0
                    send_message(int(custom_id), full_msg, account=acc)
        except Exception as e:
            log(f"[Omniscient Reborn] Error delivering notification: {e}")
