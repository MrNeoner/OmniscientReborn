import os
import time

try:
    from android.view import Gravity, View
    from android.widget import FrameLayout, LinearLayout, ImageView, TextView, ScrollView
    from android.graphics.drawable import GradientDrawable
    from android.graphics import BitmapFactory, Typeface
    from org.telegram.messenger import AndroidUtilities
    from org.telegram.ui.ActionBar import Theme, BottomSheet
    from android_utils import OnClickListener, run_on_ui_thread
except Exception:
    Gravity = View = FrameLayout = LinearLayout = ImageView = TextView = ScrollView = None
    GradientDrawable = BitmapFactory = Typeface = AndroidUtilities = Theme = BottomSheet = None
    OnClickListener = run_on_ui_thread = None

try:
    from ui.alert import AlertDialogBuilder
except Exception:
    try:
        from alert_dialog_builder import AlertDialogBuilder
    except Exception:
        AlertDialogBuilder = None

def c(val):
    if isinstance(val, int):
        val = val & 0xFFFFFFFF
        if val > 0x7FFFFFFF:
            return val - 0x100000000
        return val
    return 0

def _t(plugin, ru_text, en_text):
    lang = "ru"
    if plugin and hasattr(plugin, "get_lang_code"):
        try:
            lang = plugin.get_lang_code()
        except Exception:
            pass
    return ru_text if lang == "ru" else en_text

def translate_event_text(text: str, is_ru: bool) -> str:
    if not text:
        return ""
    t = str(text).strip()

    if any(k in t.lower() for k in ("кратковремен", "micro-session", "микро-визит", "микровизит", "micro_session")):
        return "Кратковременный визит (< 5 сек)" if is_ru else "Micro-session (< 5 sec)"

    if t.lower() in ("в сети", "online"):
        return "В сети" if is_ru else "Online"
    if t.lower() in ("оффлайн", "offline"):
        return "Оффлайн" if is_ru else "Offline"
    if "зашел" in t.lower() or "зашёл" in t.lower() or "came and left" in t.lower():
        return "Зашёл и сразу вышел" if is_ru else "Came and left immediately"
    if "спам-ловушка" in t.lower() or "spam trap" in t.lower() or "spam_trap" in t.lower():
        return "Спам-ловушка" if is_ru else "Spam trap"
    if "набирает" in t.lower() or "печатает" in t.lower() or "typing" in t.lower():
        return "Печатает..." if is_ru else "Typing..."
    if "прочита" in t.lower() or "read message" in t.lower() or t.lower() in ("read", "прочтение"):
        return "Прочитано сообщение" if is_ru else "Read message"
    if "перезапущен" in t.lower() or "restarted" in t.lower():
        return "Плагин был перезапущен" if is_ru else "Plugin was restarted"
    if "изменил" in t.lower() or "changed name" in t.lower():
        prefix_trans = "Изменил(а) имя" if is_ru else "Changed name"
        if ":" in t:
            parts = t.split(":", 1)
            return f"{prefix_trans}: {parts[1].strip()}"
        elif "->" in t:
            parts = t.split("->")
            return f"{prefix_trans}: {parts[0].split()[-1]} -> {parts[1].strip()}"
    return t

def translate_duration_str(dur: str, is_ru: bool) -> str:
    if not dur:
        return ""
    res = str(dur)
    import re
    if is_ru:
        res = re.sub(r'(\d+)\s*days?', r'\1д', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*d\b', r'\1д', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*hours?', r'\1ч', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*h\b', r'\1ч', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*mins?', r'\1м', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*m\b', r'\1м', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*secs?', r'\1с', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*s\b', r'\1с', res, flags=re.IGNORECASE)
    else:
        res = re.sub(r'(\d+)\s*дн?', r'\1d', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*ч', r'\1h', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*мин', r'\1m', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*м\b', r'\1m', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*сек', r'\1s', res, flags=re.IGNORECASE)
        res = re.sub(r'(\d+)\s*с\b', r'\1s', res, flags=re.IGNORECASE)
    return res

try:
    from ..timeline import format_duration, format_time, time_ago, get_day_stats
except Exception:
    from timeline import format_duration, format_time, time_ago, get_day_stats

class OmniscientContactSheet:
    @staticmethod
    def show(plugin, ctx, user_data, alert_builder_cls=None, on_card_click=None, on_logs_click=None, on_settings_click=None, on_remove_click=None):
        if ctx is None or LinearLayout is None:
            return

        builder_cls = alert_builder_cls or AlertDialogBuilder
        if not builder_cls:
            if hasattr(plugin, "_log_error"):
                plugin._log_error("AlertDialogBuilder not found for contact sheet")
            return

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            scroll = ScrollView(ctx)
            root = LinearLayout(ctx)
            root.setOrientation(LinearLayout.VERTICAL)
            root.setPadding(dp(18), dp(16), dp(18), dp(18))

            card_bg = GradientDrawable()
            card_bg.setShape(GradientDrawable.RECTANGLE)
            card_bg.setCornerRadius(float(dp(16)))
            card_bg.setColor(c(0xFF0F172A if dark else 0xFFFFFFFF))
            card_bg.setStroke(dp(1), c(0x3038BDF8 if dark else 0x18000000))
            root.setBackground(card_bg)

            header = LinearLayout(ctx)
            header.setOrientation(LinearLayout.HORIZONTAL)
            header.setGravity(Gravity.CENTER_VERTICAL)

            avatar = TextView(ctx)
            name = user_data.get("name", "User")
            initial = (name[0] if name else "?").upper()
            avatar.setText(initial)
            avatar.setTextSize(1, 18.0)
            avatar.setTextColor(c(0xFFFFFFFF))
            avatar.setGravity(Gravity.CENTER)
            try:
                avatar.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            av_bg = GradientDrawable()
            av_bg.setShape(GradientDrawable.OVAL)
            av_bg.setColor(c(0xFF0284C7 if dark else 0xFF0288D1))
            avatar.setBackground(av_bg)
            header.addView(avatar, LinearLayout.LayoutParams(dp(44), dp(44)))

            col = LinearLayout(ctx)
            col.setOrientation(LinearLayout.VERTICAL)
            col_lp = LinearLayout.LayoutParams(0, -2, 1.0)
            col_lp.leftMargin = dp(12)

            name_tv = TextView(ctx)
            name_tv.setText(name)
            name_tv.setTextSize(1, 15.5)
            name_tv.setTextColor(c(0xFFF8FAFC if dark else 0xFF0F172A))
            try:
                name_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            col.addView(name_tv, LinearLayout.LayoutParams(-2, -2))

            uid_str = str(user_data.get("id", ""))
            sub_title = f"ID: {uid_str}"
            tag = user_data.get("custom_tag", "")
            if tag:
                sub_title += f" • [{tag}]"
            sub_tv = TextView(ctx)
            sub_tv.setText(sub_title)
            sub_tv.setTextSize(1, 11.5)
            sub_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
            col.addView(sub_tv, LinearLayout.LayoutParams(-2, -2))

            header.addView(col, col_lp)

            lang = plugin.get_lang_code() if hasattr(plugin, "get_lang_code") else "ru"
            is_ru = (lang == "ru")

            is_online = user_data.get("last_type") == "online" or user_data.get("last_status") == "online"
            st_badge = TextView(ctx)
            st_badge.setText(_t(plugin, "В СЕТИ", "ONLINE") if is_online else _t(plugin, "ОФФЛАЙН", "OFFLINE"))
            st_badge.setTextSize(1, 10.5)
            st_badge.setTextColor(c(0xFF22C55E if is_online else 0xFF94A3B8))
            try:
                st_badge.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            st_bg = GradientDrawable()
            st_bg.setCornerRadius(float(dp(8)))
            st_bg.setColor(c(0x2222C55E if is_online else (0x20FFFFFF if dark else 0x12000000)))
            st_badge.setBackground(st_bg)
            st_badge.setPadding(dp(9), dp(4), dp(9), dp(4))
            header.addView(st_badge, LinearLayout.LayoutParams(-2, -2))

            root.addView(header, LinearLayout.LayoutParams(-1, -2))

            stats = get_day_stats(user_data, lang=lang)
            stats_box = LinearLayout(ctx)
            stats_box.setOrientation(LinearLayout.HORIZONTAL)
            stats_box.setGravity(Gravity.CENTER)
            sb_bg = GradientDrawable()
            sb_bg.setCornerRadius(float(dp(12)))
            sb_bg.setColor(c(0x18FFFFFF if dark else 0x0A000000))
            sb_bg.setStroke(dp(1), c(0x18FFFFFF if dark else 0x12000000))
            stats_box.setBackground(sb_bg)
            stats_box.setPadding(dp(10), dp(10), dp(10), dp(10))
            sb_lp = LinearLayout.LayoutParams(-1, -2)
            sb_lp.topMargin = dp(14)
            sb_lp.bottomMargin = dp(14)

            def add_mini_stat(label, value):
                v_box = LinearLayout(ctx)
                v_box.setOrientation(LinearLayout.VERTICAL)
                v_box.setGravity(Gravity.CENTER)
                val_tv = TextView(ctx)
                val_tv.setText(value)
                val_tv.setTextSize(1, 13.5)
                val_tv.setTextColor(c(0xFF38BDF8 if dark else 0xFF0284C7))
                try: val_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                v_box.addView(val_tv, LinearLayout.LayoutParams(-2, -2))

                lbl_tv = TextView(ctx)
                lbl_tv.setText(label)
                lbl_tv.setTextSize(1, 9.5)
                lbl_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                v_box.addView(lbl_tv, LinearLayout.LayoutParams(-2, -2))
                stats_box.addView(v_box, LinearLayout.LayoutParams(0, -2, 1.0))

            add_mini_stat(_t(plugin, "Время онлайн", "Online Time"), stats["formatted_total"])
            add_mini_stat(_t(plugin, "Сессий", "Sessions"), str(stats["sessions_count"]))
            add_mini_stat(_t(plugin, "Ср. сессия", "Avg Session"), stats["formatted_avg"])
            add_mini_stat(_t(plugin, "Пик активности", "Peak Hour"), str(stats["peak_hour"]))

            root.addView(stats_box, sb_lp)

            feed_title = TextView(ctx)
            feed_title.setText(_t(plugin, "ХРОНИКА АКТИВНОСТИ", "ACTIVITY TIMELINE"))
            feed_title.setTextSize(1, 10.5)
            feed_title.setTextColor(c(0xFF64748B))
            try: feed_title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception: pass
            root.addView(feed_title, LinearLayout.LayoutParams(-2, -2))

            history = (user_data.get("history") or user_data.get("events") or [])[-4:]
            if not history:
                no_ev = TextView(ctx)
                no_ev.setText(_t(plugin, "Событий пока не зафиксировано", "No events recorded yet"))
                no_ev.setTextSize(1, 12.0)
                no_ev.setTextColor(c(0xFF64748B))
                no_ev_lp = LinearLayout.LayoutParams(-2, -2)
                no_ev_lp.topMargin = dp(6)
                no_ev_lp.bottomMargin = dp(12)
                root.addView(no_ev, no_ev_lp)
            else:
                feed_box = LinearLayout(ctx)
                feed_box.setOrientation(LinearLayout.VERTICAL)
                fb_lp = LinearLayout.LayoutParams(-1, -2)
                fb_lp.topMargin = dp(6)
                fb_lp.bottomMargin = dp(14)
                for ev in reversed(history):
                    ev_row = LinearLayout(ctx)
                    ev_row.setOrientation(LinearLayout.HORIZONTAL)
                    ev_row.setGravity(Gravity.CENTER_VERTICAL)
                    ev_row.setPadding(0, dp(3), 0, dp(3))

                    t_tv = TextView(ctx)
                    t_tv.setText(ev.get("time", ""))
                    t_tv.setTextSize(1, 10.5)
                    t_tv.setTextColor(c(0xFF38BDF8))
                    ev_row.addView(t_tv, LinearLayout.LayoutParams(-2, -2))

                    text = ev.get("text", "")
                    clean_text = "".join(ch for ch in text if ord(ch) < 0x10000 and ch not in "🟢🔴👁️⚡🎯📌").strip()
                    clean_text = translate_event_text(clean_text, is_ru)

                    desc_tv = TextView(ctx)
                    desc_tv.setText(f"  •  {clean_text}")
                    desc_tv.setTextSize(1, 12.0)
                    desc_tv.setTextColor(c(0xFFF1F5F9 if dark else 0xFF1E293B))
                    desc_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                    desc_lp.leftMargin = dp(6)
                    ev_row.addView(desc_tv, desc_lp)

                    feed_box.addView(ev_row, LinearLayout.LayoutParams(-1, -2))

                root.addView(feed_box, fb_lp)

            dialog_holder = [None]

            btn_row = LinearLayout(ctx)
            btn_row.setOrientation(LinearLayout.HORIZONTAL)
            btn_row.setGravity(Gravity.CENTER_VERTICAL)

            def make_action_btn(text, bg_col, text_col, on_click):
                b = TextView(ctx)
                b.setText(text)
                b.setTextSize(1, 11.0)
                b.setTextColor(text_col)
                b.setGravity(Gravity.CENTER)
                try: b.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                d = GradientDrawable()
                d.setCornerRadius(float(dp(8)))
                d.setColor(bg_col)
                b.setBackground(d)
                b.setPadding(dp(8), dp(7), dp(8), dp(7))
                b.setClickable(True)
                if on_click and OnClickListener:
                    def click_wrapped(v):
                        try:
                            if dialog_holder[0]:
                                dialog_holder[0].dismiss()
                        except Exception:
                            pass
                        on_click()
                    b.setOnClickListener(OnClickListener(click_wrapped))
                return b

            b_card = make_action_btn(_t(plugin, "Инфографика", "Infographic"), c(0x2538BDF8), c(0xFF38BDF8), on_card_click)
            btn_row.addView(b_card, LinearLayout.LayoutParams(0, -2, 1.3))

            b_logs = make_action_btn(_t(plugin, "Логи", "Logs"), c(0x20FFFFFF if dark else 0x12000000), c(0xFFF8FAFC if dark else 0xFF0F172A), on_logs_click)
            bl_lp = LinearLayout.LayoutParams(0, -2, 0.9)
            bl_lp.leftMargin = dp(6)
            btn_row.addView(b_logs, bl_lp)

            b_opts = make_action_btn(_t(plugin, "Опции", "Options"), c(0x20FFFFFF if dark else 0x12000000), c(0xFFF8FAFC if dark else 0xFF0F172A), on_settings_click)
            bo_lp = LinearLayout.LayoutParams(0, -2, 0.9)
            bo_lp.leftMargin = dp(6)
            btn_row.addView(b_opts, bo_lp)

            b_del = make_action_btn(_t(plugin, "Удалить", "Delete"), c(0x22EF4444), c(0xFFEF4444), on_remove_click)
            bd_lp = LinearLayout.LayoutParams(0, -2, 0.9)
            bd_lp.leftMargin = dp(6)
            btn_row.addView(b_del, bd_lp)

            root.addView(btn_row, LinearLayout.LayoutParams(-1, -2))
            scroll.addView(root, FrameLayout.LayoutParams(-1, -2))

            builder = builder_cls(ctx)
            builder.set_view(scroll)
            try:
                builder.set_blurred_background(True)
                builder.set_dim_enabled(True)
                builder.set_canceled_on_touch_outside(True)
            except Exception:
                pass
            builder.set_negative_button(_t(plugin, "Закрыть", "Close"), lambda d, w: None)
            dialog = builder.show()
            dialog_holder[0] = dialog
        except Exception as e:
            if hasattr(plugin, "_log_error"):
                plugin._log_error(f"Contact sheet err: {e}")

class OmniscientContactCardWidget:
    @staticmethod
    def create_card_view(plugin, ctx, user_data, on_infographic_click=None, on_logs_click=None):
        if ctx is None or LinearLayout is None:
            return None
        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            root = FrameLayout(ctx)
            root.setPadding(dp(14), dp(8), dp(14), dp(6))

            card = LinearLayout(ctx)
            card.setOrientation(LinearLayout.VERTICAL)
            card.setPadding(dp(16), dp(14), dp(16), dp(14))

            card_bg = GradientDrawable()
            card_bg.setShape(GradientDrawable.RECTANGLE)
            card_bg.setCornerRadius(float(dp(16)))
            card_bg.setColor(c(0xFF0F172A if dark else 0xFFFFFFFF))
            card_bg.setStroke(dp(1), c(0x3038BDF8 if dark else 0x18000000))
            card.setBackground(card_bg)

            header = LinearLayout(ctx)
            header.setOrientation(LinearLayout.HORIZONTAL)
            header.setGravity(Gravity.CENTER_VERTICAL)

            av_size = dp(46)
            avatar_view = None
            uid_str = str(user_data.get("id", ""))
            try:
                from org.telegram.ui.Components import BackupImageView, AvatarDrawable
                from org.telegram.messenger import MessagesController, UserConfig
                acc = getattr(plugin, "current_account", None)
                if acc is None:
                    acc = UserConfig.selectedAccount
                mc = MessagesController.getInstance(acc)
                user_obj = mc.getUser(int(uid_str))
                if user_obj:
                    avatar_view = BackupImageView(ctx)
                    avatar_drawable = AvatarDrawable()
                    avatar_drawable.setInfo(acc, user_obj)
                    avatar_view.setForUserOrChat(user_obj, avatar_drawable)
                    avatar_view.setRoundRadius(dp(23))
            except Exception:
                avatar_view = None

            if avatar_view is None:
                avatar_view = TextView(ctx)
                name = user_data.get("name", "User")
                initial = (name[0] if name else "?").upper()
                avatar_view.setText(initial)
                avatar_view.setTextSize(1, 19.0)
                avatar_view.setTextColor(c(0xFFFFFFFF))
                avatar_view.setGravity(Gravity.CENTER)
                try:
                    avatar_view.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                av_bg = GradientDrawable()
                av_bg.setShape(GradientDrawable.OVAL)
                av_bg.setColor(c(0xFF0284C7 if dark else 0xFF0288D1))
                avatar_view.setBackground(av_bg)

            header.addView(avatar_view, LinearLayout.LayoutParams(av_size, av_size))

            col = LinearLayout(ctx)
            col.setOrientation(LinearLayout.VERTICAL)
            col_lp = LinearLayout.LayoutParams(0, -2, 1.0)
            col_lp.leftMargin = dp(12)

            name_tv = TextView(ctx)
            name_tv.setText(user_data.get("name", "User"))
            name_tv.setTextSize(1, 15.5)
            name_tv.setTextColor(c(0xFFF8FAFC if dark else 0xFF0F172A))
            try:
                name_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            col.addView(name_tv, LinearLayout.LayoutParams(-2, -2))

            sub_title = f"ID: {uid_str}"
            uname = user_data.get("username", "")
            if uname:
                sub_title = f"@{uname} • " + sub_title
            tag = user_data.get("custom_tag", "")
            if tag:
                sub_title += f" • [{tag}]"

            sub_tv = TextView(ctx)
            sub_tv.setText(sub_title)
            sub_tv.setTextSize(1, 11.5)
            sub_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
            col.addView(sub_tv, LinearLayout.LayoutParams(-2, -2))
            header.addView(col, col_lp)

            is_online = user_data.get("last_type") == "online" or user_data.get("last_status") == "online"
            st_badge = TextView(ctx)
            st_badge.setText(_t(plugin, "В СЕТИ", "ONLINE") if is_online else _t(plugin, "ОФФЛАЙН", "OFFLINE"))
            st_badge.setTextSize(1, 10.0)
            st_badge.setTextColor(c(0xFF22C55E if is_online else 0xFF94A3B8))
            try:
                st_badge.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            st_bg = GradientDrawable()
            st_bg.setCornerRadius(float(dp(8)))
            st_bg.setColor(c(0x2222C55E if is_online else (0x20FFFFFF if dark else 0x12000000)))
            st_badge.setBackground(st_bg)
            st_badge.setPadding(dp(9), dp(4), dp(9), dp(4))
            header.addView(st_badge, LinearLayout.LayoutParams(-2, -2))

            card.addView(header, LinearLayout.LayoutParams(-1, -2))

            lang = plugin.get_lang_code() if hasattr(plugin, "get_lang_code") else "ru"
            stats = get_day_stats(user_data, lang=lang)
            stats_box = LinearLayout(ctx)
            stats_box.setOrientation(LinearLayout.HORIZONTAL)
            stats_box.setGravity(Gravity.CENTER)
            sb_bg = GradientDrawable()
            sb_bg.setCornerRadius(float(dp(12)))
            sb_bg.setColor(c(0x18FFFFFF if dark else 0x0A000000))
            sb_bg.setStroke(dp(1), c(0x18FFFFFF if dark else 0x12000000))
            stats_box.setBackground(sb_bg)
            stats_box.setPadding(dp(8), dp(9), dp(8), dp(9))
            sb_lp = LinearLayout.LayoutParams(-1, -2)
            sb_lp.topMargin = dp(12)
            sb_lp.bottomMargin = dp(10)

            def add_mini_stat(label, value, col_hex):
                v_box = LinearLayout(ctx)
                v_box.setOrientation(LinearLayout.VERTICAL)
                v_box.setGravity(Gravity.CENTER)
                val_tv = TextView(ctx)
                val_tv.setText(value)
                val_tv.setTextSize(1, 13.0)
                val_tv.setTextColor(c(col_hex if dark else 0xFF0284C7))
                try: val_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                v_box.addView(val_tv, LinearLayout.LayoutParams(-2, -2))

                lbl_tv = TextView(ctx)
                lbl_tv.setText(label)
                lbl_tv.setTextSize(1, 9.0)
                lbl_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                v_box.addView(lbl_tv, LinearLayout.LayoutParams(-2, -2))
                stats_box.addView(v_box, LinearLayout.LayoutParams(0, -2, 1.0))

            add_mini_stat(_t(plugin, "Время онлайн", "Online Time"), stats["formatted_total"], 0xFF38BDF8)
            add_mini_stat(_t(plugin, "Сессий", "Sessions"), str(stats["sessions_count"]), 0xFFF59E0B)
            add_mini_stat(_t(plugin, "Ср. сессия", "Avg Session"), stats["formatted_avg"], 0xFF38BDF8)
            add_mini_stat(_t(plugin, "Пик активности", "Peak Hour"), str(stats["peak_hour"]), 0xFFA855F7)

            card.addView(stats_box, sb_lp)

            bar_box = LinearLayout(ctx)
            bar_box.setOrientation(LinearLayout.HORIZONTAL)
            bar_box.setGravity(Gravity.CENTER_VERTICAL)
            bar_box.setPadding(dp(4), dp(4), dp(4), dp(4))
            bb_bg = GradientDrawable()
            bb_bg.setCornerRadius(float(dp(8)))
            bb_bg.setColor(c(0x15FFFFFF if dark else 0x08000000))
            bar_box.setBackground(bb_bg)

            act_hours = stats.get("hourly", [0] * 24)
            for h_idx in range(24):
                mins = act_hours[h_idx] if h_idx < len(act_hours) else 0
                seg = View(ctx)
                seg_bg = GradientDrawable()
                seg_bg.setCornerRadius(float(dp(2)))
                if mins > 0:
                    alpha = min(255, int(80 + (mins / 60.0) * 175))
                    seg_bg.setColor(c((alpha << 24) | 0x38BDF8))
                else:
                    seg_bg.setColor(c(0x20FFFFFF if dark else 0x10000000))
                seg.setBackground(seg_bg)
                seg_lp = LinearLayout.LayoutParams(0, dp(12), 1.0)
                if h_idx > 0:
                    seg_lp.leftMargin = dp(2)
                bar_box.addView(seg, seg_lp)

            card.addView(bar_box, LinearLayout.LayoutParams(-1, -2))

            root.addView(card, FrameLayout.LayoutParams(-1, -2))
            return root
        except Exception as e:
            if hasattr(plugin, "_log_error"):
                plugin._log_error(f"create_card_view err: {e}")
            return None

class OmniscientEventsSheet:
    @staticmethod
    def show(plugin, ctx, user_id, user_data, on_export_click=None):
        if ctx is None or LinearLayout is None:
            return

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            lang = plugin.get_lang_code() if hasattr(plugin, "get_lang_code") else "ru"
            is_ru = (lang == "ru")
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            sheet = None
            if BottomSheet is not None:
                try:
                    sheet = BottomSheet(ctx, True)
                except Exception:
                    sheet = None

            sheet_root = LinearLayout(ctx)
            sheet_root.setOrientation(LinearLayout.VERTICAL)
            sheet_root.setPadding(dp(18), dp(12), dp(18), dp(16))
            sheet_bg_color = 0xFF0F172A if dark else 0xFFFFFFFF
            sheet_shape = GradientDrawable()
            sheet_shape.setColor(c(sheet_bg_color))
            sheet_root.setBackground(sheet_shape)

            grabber = View(ctx)
            g_bg = GradientDrawable()
            g_bg.setColor(c(0x35FFFFFF if dark else 0x20000000))
            g_bg.setCornerRadius(float(dp(3)))
            grabber.setBackground(g_bg)
            g_lp = LinearLayout.LayoutParams(dp(36), dp(4))
            g_lp.gravity = Gravity.CENTER_HORIZONTAL
            g_lp.bottomMargin = dp(12)
            sheet_root.addView(grabber, g_lp)

            head_row = LinearLayout(ctx)
            head_row.setOrientation(LinearLayout.HORIZONTAL)
            head_row.setGravity(Gravity.CENTER_VERTICAL)

            name = user_data.get("name", "User")
            initial = (name[0] if name else "?").upper()
            av_view = TextView(ctx)
            av_view.setText(initial)
            av_view.setTextSize(1, 16.0)
            av_view.setTextColor(c(0xFFFFFFFF))
            av_view.setGravity(Gravity.CENTER)
            try:
                av_view.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            av_bg = GradientDrawable()
            av_bg.setShape(GradientDrawable.OVAL)
            av_bg.setColor(c(0xFF0284C7 if dark else 0xFF0288D1))
            av_view.setBackground(av_bg)
            head_row.addView(av_view, LinearLayout.LayoutParams(dp(38), dp(38)))

            name_col = LinearLayout(ctx)
            name_col.setOrientation(LinearLayout.VERTICAL)
            nc_lp = LinearLayout.LayoutParams(0, -2, 1.0)
            nc_lp.leftMargin = dp(10)

            title_tv = TextView(ctx)
            title_tv.setText(name)
            title_tv.setTextSize(1, 15.0)
            title_tv.setTextColor(c(0xFFF8FAFC if dark else 0xFF0F172A))
            try:
                title_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            name_col.addView(title_tv)

            sub_parts = []
            uname = user_data.get("username", "")
            if uname:
                sub_parts.append(f"@{uname}")
            sub_parts.append(f"ID: {user_id}")
            tag = user_data.get("custom_tag", "")
            if tag:
                sub_parts.append(f"[{tag}]")

            sub_tv = TextView(ctx)
            sub_tv.setText(" • ".join(sub_parts))
            sub_tv.setTextSize(1, 11.0)
            sub_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
            name_col.addView(sub_tv)
            head_row.addView(name_col, nc_lp)

            is_online = user_data.get("last_type") == "online" or user_data.get("last_status") == "online"
            st_badge = TextView(ctx)
            st_badge.setText(_t(plugin, "В СЕТИ", "ONLINE") if is_online else _t(plugin, "ОФФЛАЙН", "OFFLINE"))
            st_badge.setTextSize(1, 10.0)
            st_badge.setTextColor(c(0xFF22C55E if is_online else 0xFF94A3B8))
            try:
                st_badge.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            st_bg = GradientDrawable()
            st_bg.setCornerRadius(float(dp(8)))
            st_bg.setColor(c(0x2222C55E if is_online else (0x20FFFFFF if dark else 0x12000000)))
            st_badge.setBackground(st_bg)
            st_badge.setPadding(dp(8), dp(3), dp(8), dp(3))
            head_row.addView(st_badge, LinearLayout.LayoutParams(-2, -2))

            sheet_root.addView(head_row, LinearLayout.LayoutParams(-1, -2))

            stats = get_day_stats(user_data, lang=lang)
            stats_box = LinearLayout(ctx)
            stats_box.setOrientation(LinearLayout.HORIZONTAL)
            stats_box.setGravity(Gravity.CENTER)
            sb_bg = GradientDrawable()
            sb_bg.setCornerRadius(float(dp(12)))
            sb_bg.setColor(c(0x18FFFFFF if dark else 0x0A000000))
            sb_bg.setStroke(dp(1), c(0x2038BDF8 if dark else 0x12000000))
            stats_box.setBackground(sb_bg)
            stats_box.setPadding(dp(6), dp(8), dp(6), dp(8))
            sb_lp = LinearLayout.LayoutParams(-1, -2)
            sb_lp.topMargin = dp(10)
            sb_lp.bottomMargin = dp(10)

            def add_mini(label, val, col_hex):
                b = LinearLayout(ctx)
                b.setOrientation(LinearLayout.VERTICAL)
                b.setGravity(Gravity.CENTER)
                v = TextView(ctx)
                v.setText(str(val))
                v.setTextSize(1, 12.5)
                v.setTextColor(c(col_hex if dark else 0xFF0284C7))
                try:
                    v.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                b.addView(v)
                l = TextView(ctx)
                l.setText(label)
                l.setTextSize(1, 9.0)
                l.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                b.addView(l)
                stats_box.addView(b, LinearLayout.LayoutParams(0, -2, 1.0))

            add_mini(_t(plugin, "В сети", "Online"), stats["formatted_total"], 0xFF38BDF8)
            add_mini(_t(plugin, "Сессий", "Sessions"), stats["sessions_count"], 0xFFF59E0B)
            add_mini(_t(plugin, "Прочтений", "Reads"), user_data.get("total_reads", 0), 0xFFA855F7)
            add_mini(_t(plugin, "Пик часа", "Peak"), stats["peak_hour"], 0xFF10B981)

            sheet_root.addView(stats_box, sb_lp)

            filter_box = LinearLayout(ctx)
            filter_box.setOrientation(LinearLayout.HORIZONTAL)
            filter_box.setGravity(Gravity.CENTER_VERTICAL)

            current_filter = [0]
            tabs_data = [
                (0, _t(plugin, "Все", "All")),
                (1, _t(plugin, "Сессии", "Sessions")),
                (2, _t(plugin, "Текст", "Typing")),
                (3, _t(plugin, "Чтение", "Reads"))
            ]

            scroll = ScrollView(ctx)
            scroll_content = LinearLayout(ctx)
            scroll_content.setOrientation(LinearLayout.VERTICAL)
            scroll.addView(scroll_content, FrameLayout.LayoutParams(-1, -2))

            history = user_data.get("history", [])
            sessions_log = user_data.get("sessions_log", [])
            tab_views = []

            def render_events():
                scroll_content.removeAllViews()
                f = current_filter[0]

                items_to_show = []

                if f in (0, 1):

                    is_online_now = user_data.get("last_type") == "online" or user_data.get("last_status") == "online"
                    if is_online_now:
                        s_start = user_data.get("session_start_ts") or user_data.get("last_ts", 0)
                        if s_start > 0:
                            start_s = datetime.fromtimestamp(s_start).strftime("%H:%M:%S")
                            cur_dur = int(time.time() - s_start)
                            dur_label = format_duration(cur_dur, lang=lang) if cur_dur > 0 else _t(plugin, "только что", "just now")
                            items_to_show.append({
                                "type": "active_session",
                                "icon": "🟢",
                                "text": f"{start_s} — " + _t(plugin, "Сейчас в сети", "Currently online"),
                                "time": _t(plugin, f"Активная сессия: {dur_label}", f"Active duration: {dur_label}"),
                                "is_active": True
                            })

                    for s in sessions_log:
                        s_raw = str(s).strip()
                        if not s_raw:
                            continue
                        interval_label = s_raw
                        dur_label = ""
                        if "(" in s_raw and s_raw.endswith(")"):
                            parts = s_raw.rsplit("(", 1)
                            interval_label = parts[0].strip().replace(" - ", " — ")
                            dur_str = translate_duration_str(parts[1].rstrip(")").strip(), is_ru)
                            dur_label = _t(plugin, "Длительность: ", "Duration: ") + dur_str
                        items_to_show.append({
                            "type": "session",
                            "icon": "⏱",
                            "text": interval_label,
                            "time": dur_label
                        })

                    for e in history:
                        if e.get("icon") == "⚡" or e.get("type") == "micro_session":
                            items_to_show.append({
                                "type": "micro_session",
                                "icon": "⚡",
                                "text": translate_event_text(e.get("text", ""), is_ru) or _t(plugin, "Кратковременный визит (< 5 сек)", "Micro-session (< 5 sec)"),
                                "time": e.get("time", "")
                            })

                if f == 0:
                    for e in history:
                        e_type = e.get("type", "")
                        icon = e.get("icon", "•")
                        if icon in ("✍️", "📝", "👁️", "✔️") or "typing" in e_type or "read" in e_type or "name" in e_type:
                            items_to_show.append(e)
                elif f == 2:
                    for e in history:
                        e_type = e.get("type", "")
                        icon = e.get("icon", "•")
                        if icon in ("✍️", "📝") or "typing" in e_type or "text" in e_type:
                            items_to_show.append(e)
                elif f == 3:
                    for e in history:
                        e_type = e.get("type", "")
                        icon = e.get("icon", "•")
                        if icon in ("👁️", "✔️") or "read" in e_type:
                            items_to_show.append(e)

                if not items_to_show:
                    empty_tv = TextView(ctx)
                    empty_tv.setText(_t(plugin, "Событий в этой категории не найдено", "No events found in this category"))
                    empty_tv.setTextSize(1, 12.0)
                    empty_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                    empty_tv.setGravity(Gravity.CENTER)
                    empty_tv.setPadding(0, dp(30), 0, dp(30))
                    scroll_content.addView(empty_tv, LinearLayout.LayoutParams(-1, -2))
                    return

                for item in reversed(items_to_show[-80:]):
                    ev_row = LinearLayout(ctx)
                    ev_row.setOrientation(LinearLayout.HORIZONTAL)
                    ev_row.setGravity(Gravity.CENTER_VERTICAL)
                    ev_row.setPadding(dp(10), dp(7), dp(10), dp(7))

                    is_active = item.get("is_active", False)
                    r_bg = GradientDrawable()
                    r_bg.setCornerRadius(float(dp(10)))
                    if is_active:
                        r_bg.setColor(c(0x2822C55E if dark else 0x1822C55E))
                        r_bg.setStroke(dp(1), c(0x8022C55E))
                    else:
                        r_bg.setColor(c(0x12FFFFFF if dark else 0x06000000))
                    ev_row.setBackground(r_bg)

                    r_lp = LinearLayout.LayoutParams(-1, -2)
                    r_lp.bottomMargin = dp(5)

                    ic_tv = TextView(ctx)
                    ic_tv.setText(item.get("icon", "•"))
                    ic_tv.setTextSize(1, 13.0)
                    ev_row.addView(ic_tv, LinearLayout.LayoutParams(-2, -2))

                    txt_col = LinearLayout(ctx)
                    txt_col.setOrientation(LinearLayout.VERTICAL)
                    tc_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                    tc_lp.leftMargin = dp(10)

                    t_tv = TextView(ctx)
                    raw_text = item.get("text", "")
                    translated_text = translate_event_text(raw_text, is_ru)
                    t_tv.setText(translated_text)
                    t_tv.setTextSize(1, 12.0)
                    t_tv.setTextColor(c(0xFF22C55E if is_active else (0xFFF1F5F9 if dark else 0xFF1E293B)))
                    try:
                        if is_active:
                            t_tv.setTypeface(Typeface.DEFAULT_BOLD)
                    except Exception:
                        pass
                    txt_col.addView(t_tv)

                    t_time = item.get("time", "")
                    if t_time:
                        tm_tv = TextView(ctx)
                        translated_time = translate_duration_str(t_time, is_ru)
                        tm_tv.setText(translated_time)
                        tm_tv.setTextSize(1, 9.5)
                        tm_tv.setTextColor(c(0xFF22C55E if is_active else (0xFF64748B if dark else 0xFF94A3B8)))
                        txt_col.addView(tm_tv)

                    ev_row.addView(txt_col, tc_lp)
                    scroll_content.addView(ev_row, r_lp)

            def update_tabs():
                for t_idx, tv_chip in tab_views:
                    is_active = (current_filter[0] == t_idx)
                    ch_bg = GradientDrawable()
                    ch_bg.setCornerRadius(float(dp(8)))
                    ch_bg.setColor(c(0x2538BDF8 if is_active else (0x10FFFFFF if dark else 0x08000000)))
                    ch_bg.setStroke(dp(1), c(0x5038BDF8 if is_active else (0x20FFFFFF if dark else 0x10000000)))
                    tv_chip.setBackground(ch_bg)
                    tv_chip.setTextColor(c(0xFF38BDF8 if is_active else (0xFF94A3B8 if dark else 0xFF64748B)))

            for t_idx, t_name in tabs_data:
                tab_chip = TextView(ctx)
                tab_chip.setText(t_name)
                tab_chip.setTextSize(1, 11.0)
                tab_chip.setPadding(dp(10), dp(5), dp(10), dp(5))
                tab_chip.setGravity(Gravity.CENTER)
                tab_chip.setClickable(True)
                tab_chip.setFocusable(True)
                try:
                    tab_chip.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass

                def make_tab_cb(idx):
                    def _click(*a):
                        current_filter[0] = idx
                        update_tabs()
                        render_events()
                    return _click

                if OnClickListener:
                    tab_chip.setOnClickListener(OnClickListener(make_tab_cb(t_idx)))

                t_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                if t_idx > 0:
                    t_lp.leftMargin = dp(6)
                filter_box.addView(tab_chip, t_lp)
                tab_views.append((t_idx, tab_chip))

            update_tabs()
            sheet_root.addView(filter_box, LinearLayout.LayoutParams(-1, -2))

            sc_lp = LinearLayout.LayoutParams(-1, dp(270))
            sc_lp.topMargin = dp(8)
            sheet_root.addView(scroll, sc_lp)
            render_events()

            btn_row = LinearLayout(ctx)
            btn_row.setOrientation(LinearLayout.HORIZONTAL)
            br_lp = LinearLayout.LayoutParams(-1, -2)
            br_lp.topMargin = dp(10)

            exp_btn = TextView(ctx)
            exp_btn.setText(_t(plugin, "📥 Экспорт", "📥 Export"))
            exp_btn.setTextSize(1, 13.0)
            exp_btn.setGravity(Gravity.CENTER)
            exp_btn.setTextColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            try:
                exp_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            eb_bg = GradientDrawable()
            eb_bg.setCornerRadius(float(dp(12)))
            eb_bg.setColor(c(0x2000E5FF if dark else 0x180284C7))
            eb_bg.setStroke(dp(1), c(0x5000E5FF if dark else 0x350284C7))
            exp_btn.setBackground(eb_bg)
            exp_btn.setClickable(True)
            exp_btn.setFocusable(True)
            if OnClickListener and on_export_click:
                def _do_exp(*a):
                    if sheet is not None:
                        try:
                            sheet.dismiss()
                        except Exception:
                            pass
                    on_export_click()
                exp_btn.setOnClickListener(OnClickListener(_do_exp))
            btn_row.addView(exp_btn, LinearLayout.LayoutParams(0, dp(44), 1.0))

            close_btn = TextView(ctx)
            close_btn.setText(_t(plugin, "Закрыть", "Close"))
            close_btn.setTextSize(1, 13.5)
            close_btn.setGravity(Gravity.CENTER)
            close_btn.setTextColor(c(0xFFFFFFFF))
            try:
                close_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            cb_bg = GradientDrawable()
            cb_bg.setCornerRadius(float(dp(12)))
            cb_bg.setColor(c(0xFF0284C7 if dark else 0xFF0F172A))
            close_btn.setBackground(cb_bg)
            close_btn.setClickable(True)
            close_btn.setFocusable(True)
            if sheet is not None and OnClickListener:
                close_btn.setOnClickListener(OnClickListener(lambda *a: sheet.dismiss()))

            cb_lp = LinearLayout.LayoutParams(0, dp(44), 1.0)
            cb_lp.leftMargin = dp(8)
            btn_row.addView(close_btn, cb_lp)

            sheet_root.addView(btn_row, br_lp)

            if sheet is not None:
                sheet.setCustomView(sheet_root)
                sheet.show()
        except Exception as e:
            if hasattr(plugin, "_log_error"):
                plugin._log_error(f"OmniscientEventsSheet err: {e}")
