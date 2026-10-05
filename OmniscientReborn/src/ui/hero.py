import os
from datetime import datetime

try:
    from android.view import Gravity, View
    from android.widget import FrameLayout, LinearLayout, ImageView, TextView
    from android.graphics.drawable import GradientDrawable
    from android.graphics import BitmapFactory, Typeface
    from org.telegram.messenger import AndroidUtilities
    from org.telegram.ui.ActionBar import Theme
    from android_utils import OnClickListener, run_on_ui_thread
except Exception:
    Gravity = View = FrameLayout = LinearLayout = ImageView = TextView = None
    GradientDrawable = BitmapFactory = Typeface = AndroidUtilities = Theme = None
    OnClickListener = run_on_ui_thread = None

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
    else:
        try:
            import main
            lang = getattr(main, "LANG", "ru")
        except Exception:
            pass
    return ru_text if lang == "ru" else en_text

class HeroHeaderUI:
    @staticmethod
    def create_hero_banner(plugin, ctx, on_add_click=None, on_summary_click=None, on_export_click=None):
        if ctx is None or FrameLayout is None or LinearLayout is None:
            return None

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            wrapper = FrameLayout(ctx)
            wrapper.setPadding(dp(14), dp(6), dp(14), dp(8))

            root = FrameLayout(ctx)
            root.setLayoutParams(FrameLayout.LayoutParams(-1, -2))

            bg_shape = GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                [c(0xFF0F172A), c(0xFF0C101A), c(0xFF060911)] if dark else [c(0xFFFFFFFF), c(0xFFF8FAFC), c(0xFFE2E8F0)]
            )
            bg_shape.setCornerRadius(float(dp(16)))
            bg_shape.setStroke(dp(1), c(0x3538BDF8 if dark else 0x18000000))
            root.setBackground(bg_shape)
            try:
                root.setClipToOutline(True)
                root.setClipChildren(True)
            except Exception:
                pass

            bg_container = FrameLayout(ctx)
            bg_view = ImageView(ctx)
            bg_view.setScaleType(ImageView.ScaleType.CENTER_CROP)
            try:
                bg_view.setAlpha(0.25 if dark else 0.18)
            except Exception:
                pass
            bg_file = "banner_bgdark.png" if dark else "banner_bg.png"
            bg_path = plugin._res_path(bg_file) if hasattr(plugin, "_res_path") else ""
            if bg_path and os.path.exists(bg_path):
                try:
                    bmp = BitmapFactory.decodeFile(bg_path)
                    if bmp:
                        bg_view.setImageBitmap(bmp)
                except Exception:
                    pass
            bg_container.addView(bg_view, FrameLayout.LayoutParams(-1, -1))
            root.addView(bg_container, FrameLayout.LayoutParams(-1, -1))

            content = LinearLayout(ctx)
            content.setOrientation(LinearLayout.VERTICAL)
            content.setPadding(dp(16), dp(14), dp(16), dp(14))

            top_row = LinearLayout(ctx)
            top_row.setOrientation(LinearLayout.HORIZONTAL)
            top_row.setGravity(Gravity.CENTER_VERTICAL)

            icon_view = ImageView(ctx)
            icon_path = plugin._res_path("icon.png") if hasattr(plugin, "_res_path") else ""
            if icon_path and os.path.exists(icon_path):
                try:
                    icon_bmp = BitmapFactory.decodeFile(icon_path)
                    if icon_bmp:
                        icon_view.setImageBitmap(icon_bmp)
                except Exception:
                    pass
            top_row.addView(icon_view, LinearLayout.LayoutParams(dp(22), dp(22)))

            title_view = TextView(ctx)
            title_view.setText("OMNISCIENT REBORN")
            title_view.setTextSize(1, 14.5)
            title_view.setTextColor(c(0xFFF8FAFC if dark else 0xFF0F172A))
            try:
                title_view.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            title_lp = LinearLayout.LayoutParams(-2, -2)
            title_lp.leftMargin = dp(8)
            top_row.addView(title_view, title_lp)

            badge = TextView(ctx)
            badge.setText("PRO")
            badge.setTextSize(1, 9.0)
            badge.setTextColor(c(0xFF38BDF8))
            try:
                badge.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            b_bg = GradientDrawable()
            b_bg.setCornerRadius(float(dp(4)))
            b_bg.setColor(c(0x2038BDF8))
            b_bg.setStroke(dp(1), c(0x6038BDF8))
            badge.setBackground(b_bg)
            badge.setPadding(dp(5), dp(1), dp(5), dp(1))
            badge_lp = LinearLayout.LayoutParams(-2, -2)
            badge_lp.leftMargin = dp(6)
            top_row.addView(badge, badge_lp)

            spacer = View(ctx)
            top_row.addView(spacer, LinearLayout.LayoutParams(0, 1, 1.0))

            lang_chip = LinearLayout(ctx)
            lang_chip.setOrientation(LinearLayout.HORIZONTAL)
            lang_chip.setGravity(Gravity.CENTER)
            l_bg = GradientDrawable()
            l_bg.setCornerRadius(float(dp(10)))
            l_bg.setColor(c(0x2038BDF8 if dark else 0x10000000))
            l_bg.setStroke(dp(1), c(0x3538BDF8 if dark else 0x18000000))
            lang_chip.setBackground(l_bg)
            lang_chip.setPadding(dp(7), dp(3), dp(7), dp(3))
            lang_chip.setClickable(True)
            lang_chip.setFocusable(True)
            if OnClickListener:
                def _open_lang_menu(v):
                    if hasattr(plugin, "show_language_menu"):
                        plugin.show_language_menu(v)
                    elif hasattr(plugin, "show_language_dialog"):
                        plugin.show_language_dialog()
                lang_chip.setOnClickListener(OnClickListener(_open_lang_menu))

            lang_ic = ImageView(ctx)
            lic_id = 0
            try:
                from java import jclass
                R_drawable = jclass("org.telegram.messenger.R$drawable")
                lic_id = getattr(R_drawable, "msg_translate", 0) or getattr(R_drawable, "msg_language", 0)
            except Exception:
                pass
            if lic_id != 0:
                try:
                    lang_ic.setImageResource(lic_id)
                    lang_ic.setColorFilter(c(0xFF38BDF8 if dark else 0xFF0284C7))
                except Exception:
                    pass
            lang_chip.addView(lang_ic, LinearLayout.LayoutParams(dp(15), dp(15)))
            top_row.addView(lang_chip, LinearLayout.LayoutParams(-2, -2))

            is_beta = getattr(plugin, "is_beta", False)
            ver_str = str(getattr(plugin, "__version__", "") or "").lower()
            if "alpha" in ver_str:
                ver_status = "Alpha"
                st_color = 0xFFA855F7
            elif is_beta or "beta" in ver_str:
                ver_status = "Beta"
                st_color = 0xFFF59E0B
            else:
                ver_status = "Stable"
                st_color = 0xFF22C55E

            status_chip = LinearLayout(ctx)
            status_chip.setOrientation(LinearLayout.HORIZONTAL)
            status_chip.setGravity(Gravity.CENTER_VERTICAL)
            sc_bg = GradientDrawable()
            sc_bg.setCornerRadius(float(dp(10)))
            sc_bg.setColor(c((st_color & 0x00FFFFFF) | 0x22000000))
            status_chip.setBackground(sc_bg)
            status_chip.setPadding(dp(8), dp(3), dp(8), dp(3))

            status_dot = View(ctx)
            dot_bg = GradientDrawable()
            dot_bg.setShape(GradientDrawable.OVAL)
            dot_bg.setColor(c(st_color))
            status_dot.setBackground(dot_bg)
            status_chip.addView(status_dot, LinearLayout.LayoutParams(dp(6), dp(6)))

            status_txt = TextView(ctx)
            status_txt.setText(ver_status)
            status_txt.setTextSize(1, 10.0)
            status_txt.setTextColor(c(st_color))
            try:
                status_txt.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            st_lp = LinearLayout.LayoutParams(-2, -2)
            st_lp.leftMargin = dp(5)
            status_chip.addView(status_txt, st_lp)

            sc_lp = LinearLayout.LayoutParams(-2, -2)
            sc_lp.leftMargin = dp(6)
            top_row.addView(status_chip, sc_lp)
            content.addView(top_row, LinearLayout.LayoutParams(-1, -2))

            stats_row = LinearLayout(ctx)
            stats_row.setOrientation(LinearLayout.HORIZONTAL)
            stats_lp = LinearLayout.LayoutParams(-1, -2)
            stats_lp.topMargin = dp(12)
            stats_lp.bottomMargin = dp(8)

            tracked_count = len(plugin.tracked_users) if hasattr(plugin, "tracked_users") else 0

            leader_name = "—"
            leader_events = 0
            total_actions = 0
            total_online_secs = 0

            if hasattr(plugin, "tracked_users"):
                for uid, u in plugin.tracked_users.items():
                    total_online_secs += int(u.get("total_online_time", 0))
                    act_count = len(u.get("history", []))
                    total_actions += act_count
                    if act_count > leader_events:
                        leader_events = act_count
                        if hasattr(plugin, "get_display_name"):
                            leader_name = plugin.get_display_name(uid, u)
                        else:
                            leader_name = u.get("name", uid)

            hours = total_online_secs // 3600
            mins = (total_online_secs % 3600) // 60
            dur_fmt = f"{hours}ч {mins}м" if _t(plugin, "ru", "en") == "ru" else f"{hours}h {mins}m"
            if hours == 0:
                dur_fmt = f"{mins}м" if _t(plugin, "ru", "en") == "ru" else f"{mins}m"

            columns = [
                (_t(plugin, "ОТСЛЕЖИВАЕТСЯ", "TRACKED"), str(tracked_count), c(0xFF38BDF8)),
                (_t(plugin, "ДЕЙСТВИЙ", "ACTIONS"), str(total_actions), c(0xFFF59E0B)),
                (_t(plugin, "В СЕТИ", "ONLINE"), dur_fmt, c(0xFF10B981))
            ]

            for i, (label, val_str, val_col) in enumerate(columns):
                col = LinearLayout(ctx)
                col.setOrientation(LinearLayout.VERTICAL)
                col.setGravity(Gravity.CENTER)
                c_bg = GradientDrawable()
                c_bg.setCornerRadius(float(dp(10)))
                c_bg.setColor(c(0x221E293B if dark else 0x08000000))
                c_bg.setStroke(dp(1), c(0x2038BDF8 if dark else 0x12000000))
                col.setBackground(c_bg)
                col.setPadding(dp(6), dp(8), dp(6), dp(8))

                v_tv = TextView(ctx)
                v_tv.setText(val_str)
                v_tv.setTextSize(1, 15.0)
                v_tv.setTextColor(val_col)
                try: v_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                col.addView(v_tv, LinearLayout.LayoutParams(-2, -2))

                l_tv = TextView(ctx)
                l_tv.setText(label)
                l_tv.setTextSize(1, 9.0)
                l_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                lt_lp = LinearLayout.LayoutParams(-2, -2)
                lt_lp.topMargin = dp(2)
                col.addView(l_tv, lt_lp)

                col_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                if i > 0:
                    col_lp.leftMargin = dp(8)
                stats_row.addView(col, col_lp)

            content.addView(stats_row, stats_lp)

            leader_chip = LinearLayout(ctx)
            leader_chip.setOrientation(LinearLayout.HORIZONTAL)
            leader_chip.setGravity(Gravity.CENTER_VERTICAL)
            lc_bg = GradientDrawable()
            lc_bg.setCornerRadius(float(dp(8)))
            lc_bg.setColor(c(0x1838BDF8 if dark else 0x08000000))
            lc_bg.setStroke(dp(1), c(0x3038BDF8 if dark else 0x15000000))
            leader_chip.setBackground(lc_bg)
            leader_chip.setPadding(dp(10), dp(5), dp(10), dp(5))

            lc_txt = TextView(ctx)
            if leader_events > 0:
                clean_leader = leader_name.replace("®", "").strip()
                lc_txt.setText(_t(plugin, f"Лидер активности: {clean_leader} • {leader_events} действий", f"Activity leader: {clean_leader} • {leader_events} events"))
            else:
                lc_txt.setText(_t(plugin, "Лидер активности: нет зафиксированных действий", "Activity leader: no recorded events"))
            lc_txt.setTextSize(1, 11.0)
            lc_txt.setTextColor(c(0xFFE2E8F0 if dark else 0xFF1E293B))
            try:
                lc_txt.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            leader_chip.addView(lc_txt, LinearLayout.LayoutParams(-2, -2))

            lc_lp = LinearLayout.LayoutParams(-1, -2)
            lc_lp.bottomMargin = dp(10)
            content.addView(leader_chip, lc_lp)

            actions_row = LinearLayout(ctx)
            actions_row.setOrientation(LinearLayout.HORIZONTAL)
            actions_row.setGravity(Gravity.CENTER_VERTICAL)

            def _wrap_cb(fn):
                if not fn: return None
                def _invoke(v=None):
                    try:
                        fn()
                    except TypeError:
                        try:
                            fn(v)
                        except Exception:
                            pass
                return _invoke

            def make_pill_button(title, callback, is_accent=False):
                btn = TextView(ctx)
                btn.setText(title)
                btn.setTextSize(1, 11.5)
                btn.setTextColor(c(0xFF38BDF8 if is_accent else (0xFFF8FAFC if dark else 0xFF0F172A)))
                btn.setGravity(Gravity.CENTER)
                try: btn.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                btn_bg = GradientDrawable()
                btn_bg.setCornerRadius(float(dp(8)))
                if is_accent:
                    btn_bg.setColor(c(0x2238BDF8))
                    btn_bg.setStroke(dp(1), c(0x5538BDF8))
                else:
                    btn_bg.setColor(c(0x25FFFFFF if dark else 0x12000000))
                    btn_bg.setStroke(dp(1), c(0x20FFFFFF if dark else 0x18000000))
                btn.setBackground(btn_bg)
                btn.setPadding(dp(10), dp(6), dp(10), dp(6))
                btn.setClickable(True)
                if callback and OnClickListener:
                    cb = _wrap_cb(callback)
                    btn.setOnClickListener(OnClickListener(lambda v: cb(v)))
                return btn

            b_add = make_pill_button(_t(plugin, "+ Добавить контакт", "+ Add Contact"), on_add_click, is_accent=True)
            actions_row.addView(b_add, LinearLayout.LayoutParams(0, -2, 1.0))

            b_export = make_pill_button(_t(plugin, "Экспорт бэкапа", "Export Backup"), on_export_click, is_accent=False)
            be_lp = LinearLayout.LayoutParams(0, -2, 1.0)
            be_lp.leftMargin = dp(8)
            actions_row.addView(b_export, be_lp)

            content.addView(actions_row, LinearLayout.LayoutParams(-1, -2))
            root.addView(content, FrameLayout.LayoutParams(-1, -1))
            wrapper.addView(root, FrameLayout.LayoutParams(-1, -1))

            return wrapper
        except Exception as e:
            if hasattr(plugin, "_log_error"):
                plugin._log_error(f"Hero banner err: {e}")
            return None

    @staticmethod
    def create_contacts_hero(plugin, ctx):
        if ctx is None or FrameLayout is None or LinearLayout is None:
            return None

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            wrapper = FrameLayout(ctx)
            wrapper.setPadding(dp(14), dp(8), dp(14), dp(6))

            card = LinearLayout(ctx)
            card.setOrientation(LinearLayout.VERTICAL)
            c_bg = GradientDrawable()
            c_bg.setShape(GradientDrawable.RECTANGLE)
            c_bg.setCornerRadius(float(dp(14)))
            c_bg.setColor(c(0xFF141C2B if dark else 0xFFF1F5F9))
            c_bg.setStroke(dp(1), c(0x2838BDF8 if dark else 0x18000000))
            card.setBackground(c_bg)
            card.setPadding(dp(14), dp(12), dp(14), dp(12))

            tracked_count = len(plugin.tracked_users) if hasattr(plugin, "tracked_users") else 0
            leader_name = "—"
            leader_events = 0
            total_actions = 0
            online_now = 0

            if hasattr(plugin, "tracked_users"):
                for uid, u in plugin.tracked_users.items():
                    act_count = len(u.get("history", []))
                    total_actions += act_count
                    if u.get("last_type") == "online" or u.get("last_status") == "online":
                        online_now += 1
                    if act_count > leader_events:
                        leader_events = act_count
                        if hasattr(plugin, "get_display_name"):
                            leader_name = plugin.get_display_name(uid, u)
                        else:
                            leader_name = u.get("name", uid)

            clean_leader = leader_name.replace("®", "").strip()

            row1 = LinearLayout(ctx)
            row1.setOrientation(LinearLayout.HORIZONTAL)
            row1.setGravity(Gravity.CENTER_VERTICAL)

            t_title = TextView(ctx)
            t_title.setText(_t(plugin, "СТАТИСТИКА МОНИТОРИНГА", "MONITORING STATISTICS"))
            t_title.setTextSize(1, 12.0)
            t_title.setTextColor(c(0xFF38BDF8))
            try: t_title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception: pass
            row1.addView(t_title)

            sp = View(ctx)
            row1.addView(sp, LinearLayout.LayoutParams(0, 1, 1.0))

            on_badge = TextView(ctx)
            on_badge.setText(_t(plugin, f"В сети: {online_now}", f"Online: {online_now}"))
            on_badge.setTextSize(1, 11.0)
            on_badge.setTextColor(c(0xFF22C55E if online_now > 0 else 0xFF94A3B8))
            try: on_badge.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception: pass
            row1.addView(on_badge)

            card.addView(row1, LinearLayout.LayoutParams(-1, -2))

            stats_row = LinearLayout(ctx)
            stats_row.setOrientation(LinearLayout.HORIZONTAL)
            s_lp = LinearLayout.LayoutParams(-1, -2)
            s_lp.topMargin = dp(10)
            s_lp.bottomMargin = dp(8)

            cols = [
                (_t(plugin, "ОТСЛЕЖИВАЕТСЯ", "TRACKED"), str(tracked_count), c(0xFF38BDF8)),
                (_t(plugin, "ДЕЙСТВИЙ", "ACTIONS"), str(total_actions), c(0xFFF59E0B)),
                (_t(plugin, "ЛИДЕР", "LEADER"), clean_leader[:10] + ("…" if len(clean_leader) > 10 else ""), c(0xFF10B981))
            ]

            for i, (lab, val, col_hex) in enumerate(cols):
                box = LinearLayout(ctx)
                box.setOrientation(LinearLayout.VERTICAL)
                box.setGravity(Gravity.CENTER)
                b_bg = GradientDrawable()
                b_bg.setCornerRadius(float(dp(8)))
                b_bg.setColor(c(0x221E293B if dark else 0xFFFFFFFF))
                b_bg.setStroke(dp(1), c(0x2038BDF8 if dark else 0x12000000))
                box.setBackground(b_bg)
                box.setPadding(dp(4), dp(6), dp(4), dp(6))

                tv_v = TextView(ctx)
                tv_v.setText(val)
                tv_v.setTextSize(1, 14.0)
                tv_v.setTextColor(col_hex)
                try: tv_v.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception: pass
                box.addView(tv_v, LinearLayout.LayoutParams(-2, -2))

                tv_l = TextView(ctx)
                tv_l.setText(lab)
                tv_l.setTextSize(1, 8.5)
                tv_l.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                t_lp = LinearLayout.LayoutParams(-2, -2)
                t_lp.topMargin = dp(2)
                box.addView(tv_l, t_lp)

                b_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                if i > 0:
                    b_lp.leftMargin = dp(6)
                stats_row.addView(box, b_lp)

            card.addView(stats_row, s_lp)

            lead_row = TextView(ctx)
            if leader_events > 0:
                lead_row.setText(_t(plugin, f"Лидер активности: {clean_leader} ({leader_events} действий)", f"Activity leader: {clean_leader} ({leader_events} events)"))
            else:
                lead_row.setText(_t(plugin, "Лидер активности: нет зафиксированных действий", "Activity leader: no recorded events"))
            lead_row.setTextSize(1, 11.5)
            lead_row.setTextColor(c(0xFFCBD5E1 if dark else 0xFF334155))
            card.addView(lead_row, LinearLayout.LayoutParams(-1, -2))

            wrapper.addView(card, FrameLayout.LayoutParams(-1, -2))
            return wrapper
        except Exception as e:
            if hasattr(plugin, "_log_error"):
                plugin._log_error(f"Contacts hero err: {e}")
            return None
