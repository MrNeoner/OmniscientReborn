import os
import math
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    from android_utils import log
except Exception:
    def log(msg): print(msg)

try:
    from ..timeline import get_day_stats, format_duration, format_time
except Exception:
    from timeline import get_day_stats, format_duration, format_time

def _clean_card_text(text: str) -> str:
    if not text:
        return ""
    out = []
    for ch in str(text):
        cp = ord(ch)
        if cp >= 0x1F000 or (0x2300 <= cp <= 0x27BF) or (0xFE00 <= cp <= 0xFE0F) or cp == 0x200D:
            continue
        if ch in "🟢🔴👁️⚡🎯📌⭐🔹🔸♦️▪️▫️":
            continue
        out.append(ch)
    return " ".join("".join(out).split())

class OmniscientCardRenderer:
    def __init__(self, res_dir=None):
        self.res_dir = res_dir

    def _get_font(self, size, bold=False):
        font_name = "font_bold.ttf" if bold else "font_regular.ttf"

        if self.res_dir:
            res_font = os.path.join(self.res_dir, font_name)
            if os.path.exists(res_font):
                try:
                    return ImageFont.truetype(res_font, size)
                except Exception:
                    pass

        try:
            f_val = globals().get("__file__")
            curr = os.path.dirname(os.path.abspath(f_val)) if f_val else ""
            for parent in (curr, os.path.dirname(curr) if curr else "", os.path.dirname(os.path.dirname(curr)) if curr else ""):
                if not parent:
                    continue
                cand = os.path.join(parent, "res", font_name)
                if os.path.exists(cand):
                    try:
                        return ImageFont.truetype(cand, size)
                    except Exception:
                        pass
        except Exception:
            pass

        import sys
        for sp in sys.path:
            try:
                for base_p in (sp, os.path.dirname(sp)):
                    cand = os.path.join(base_p, "res", font_name)
                    if os.path.exists(cand):
                        try:
                            return ImageFont.truetype(cand, size)
                        except Exception:
                            pass
            except Exception:
                pass

        font_candidates = [
            "C:/Windows/Fonts/bahnschrift.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
            "/system/fonts/Roboto-Medium.ttf",
            "/system/fonts/RobotoFlex-Regular.ttf",
            "/system/fonts/RobotoStatic-Regular.ttf",
            "/system/fonts/Roboto.ttf",
            "/system/fonts/DroidSans-Bold.ttf" if bold else "/system/fonts/DroidSans.ttf",
            "/system/fonts/NotoSans-Regular.ttf",
        ]
        for p in font_candidates:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass

        try:
            return ImageFont.load_default()
        except Exception:
            return None

    def render_card(self, user_data, output_path=None, scale=2, theme="dark", custom_bg_path=None, lang="ru"):
        s = int(scale) if scale in (1, 2, 3) else 2
        w, h = 1080 * s, 680 * s
        is_dark = (str(theme).lower() != "light")
        if not lang or str(lang).lower() == "auto":
            try:
                from org.telegram.messenger import LocaleController
                loc = LocaleController.getInstance().getCurrentLocale()
                l_code = str(loc.getLanguage()).lower() if loc else ""
                lang = "ru" if l_code in ("ru", "be", "uk") else "en"
            except Exception:
                lang = "ru"
        is_en = (str(lang).lower() == "en")

        if is_dark:
            bg_top = (14, 19, 32)
            bg_bot = (9, 13, 22)
            text_title = (248, 250, 252, 255)
            text_sub = (148, 163, 184, 255)
            card_fill = (19, 28, 46, 200)
            card_stroke = (56, 189, 248, 40)
            box_fill = (15, 23, 42, 180)
            box_stroke = (56, 189, 248, 40)
            grid_col = (30, 41, 59, 120)
            bar_empty = (22, 33, 54, 90)
            axis_col = (100, 116, 139, 255)
            brand_col = (100, 116, 139, 255)
            prog_bg = (30, 41, 59, 200)
        else:
            bg_top = (248, 250, 252)
            bg_bot = (226, 232, 240)
            text_title = (15, 23, 42, 255)
            text_sub = (100, 116, 139, 255)
            card_fill = (255, 255, 255, 240)
            card_stroke = (203, 213, 225, 220)
            box_fill = (255, 255, 255, 220)
            box_stroke = (203, 213, 225, 220)
            grid_col = (226, 232, 240, 255)
            bar_empty = (241, 245, 249, 200)
            axis_col = (100, 116, 139, 255)
            brand_col = (148, 163, 184, 255)
            prog_bg = (226, 232, 240, 255)

        img = Image.new("RGBA", (w, h), bg_top + (255,))
        draw = ImageDraw.Draw(img)

        custom_loaded = False
        if custom_bg_path and os.path.exists(custom_bg_path):
            try:
                with Image.open(custom_bg_path) as c_raw:
                    c_img = c_raw.convert("RGBA").copy()
                c_img = c_img.resize((w, h), Image.Resampling.LANCZOS)
                scrim_color = (11, 15, 25, 175) if is_dark else (248, 250, 252, 185)
                scrim = Image.new("RGBA", (w, h), scrim_color)
                img = Image.alpha_composite(c_img, scrim)
                draw = ImageDraw.Draw(img)
                custom_loaded = True
            except Exception:
                custom_loaded = False

        if not custom_loaded:
            for y in range(h):
                t = y / float(h)
                r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
                g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
                b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
                draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

            aura = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            aura_draw = ImageDraw.Draw(aura)
            if is_dark:
                aura_draw.ellipse([-50 * s, -50 * s, 450 * s, 450 * s], fill=(0, 180, 255, 35))
                aura_draw.ellipse([w - 400 * s, h - 350 * s, w + 100 * s, h + 150 * s], fill=(120, 50, 230, 30))
            else:
                aura_draw.ellipse([-50 * s, -50 * s, 450 * s, 450 * s], fill=(56, 189, 248, 25))
                aura_draw.ellipse([w - 400 * s, h - 350 * s, w + 100 * s, h + 150 * s], fill=(168, 85, 247, 20))
            aura = aura.filter(ImageFilter.GaussianBlur(50 * s))
            img = Image.alpha_composite(img, aura)
            draw = ImageDraw.Draw(img)

        f_title = self._get_font(28 * s, True)
        f_sub = self._get_font(15 * s, False)
        f_val = self._get_font(23 * s, True)
        f_lbl = self._get_font(12 * s, True)
        f_small = self._get_font(11 * s, False)

        av_x, av_y, av_size = 50 * s, 36 * s, 76 * s
        avatar_loaded = False
        avatar_path = user_data.get("avatar_path")
        if avatar_path and os.path.exists(avatar_path):
            try:
                with Image.open(avatar_path) as av_raw:
                    av_img = av_raw.convert("RGBA").copy()
                av_img = av_img.resize((av_size, av_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (av_size, av_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse([0, 0, av_size, av_size], fill=255)
                img.paste(av_img, (av_x, av_y), mask)
                draw.ellipse([av_x, av_y, av_x + av_size, av_y + av_size], outline=(56, 189, 248, 220), width=2 * s)
                avatar_loaded = True
            except Exception:
                avatar_loaded = False

        if not avatar_loaded:
            draw.ellipse([av_x, av_y, av_x + av_size, av_y + av_size], fill=(22, 33, 54, 255) if is_dark else (226, 232, 240, 255), outline=(56, 189, 248, 220), width=2 * s)
            name_raw = user_data.get("name", "Пользователь")
            clean_name = _clean_card_text(name_raw) or "Пользователь"
            initial = (clean_name[0] if clean_name else "?").upper()
            f_init = self._get_font(34 * s, True)
            ibox = draw.textbbox((0, 0), initial, font=f_init)
            iw = ibox[2] - ibox[0]
            ih = ibox[3] - ibox[1]
            draw.text((av_x + (av_size - iw) // 2 - ibox[0], av_y + (av_size - ih) // 2 - ibox[1]), initial, font=f_init, fill=(255, 255, 255, 255) if is_dark else (15, 23, 42, 255))

        default_user_name = "User" if is_en else "Пользователь"
        name = _clean_card_text(user_data.get("name", default_user_name)) or default_user_name
        draw.text((140 * s, 42 * s), name, font=f_title, fill=text_title)
        uname = _clean_card_text(user_data.get("username", ""))
        tag = _clean_card_text(user_data.get("custom_tag", ""))
        meta_parts = []
        if uname:
            meta_parts.append(f"@{uname}")
        meta_parts.append(f"ID: {user_data.get('id', '')}")
        if tag:
            meta_parts.append(f"[{tag}]")
        draw.text((142 * s, 82 * s), "  •  ".join(meta_parts), font=f_sub, fill=text_sub)

        is_online = user_data.get("last_status") == "online" or user_data.get("last_type") == "online"
        st_text = ("ONLINE" if is_online else "OFFLINE") if is_en else ("В СЕТИ" if is_online else "ОФФЛАЙН")
        f_st = self._get_font(14 * s, bold=True)

        st_box = draw.textbbox((0, 0), st_text, font=f_st)
        tw = st_box[2] - st_box[0]
        th = st_box[3] - st_box[1]

        badge_pad_x = 16 * s
        dot_dia = 8 * s
        dot_gap = 9 * s
        badge_w = badge_pad_x + dot_dia + dot_gap + tw + badge_pad_x
        badge_h = 34 * s

        bx2 = w - 50 * s
        bx1 = bx2 - badge_w
        by1 = 44 * s
        by2 = by1 + badge_h

        dot_x = bx1 + badge_pad_x
        dot_y = by1 + (badge_h - dot_dia) // 2
        tx = dot_x + dot_dia + dot_gap - st_box[0]
        ty = by1 + (badge_h - th) // 2 - st_box[1]

        if is_online:
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=17 * s, fill=(6, 78, 59, 180) if is_dark else (209, 250, 229, 230), outline=(16, 185, 129, 220), width=1 * s)
            draw.ellipse([dot_x, dot_y, dot_x + dot_dia, dot_y + dot_dia], fill=(52, 211, 153, 255) if is_dark else (5, 150, 105, 255))
            draw.text((tx, ty), st_text, font=f_st, fill=(110, 231, 183, 255) if is_dark else (6, 95, 70, 255))
        else:
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=17 * s, fill=(15, 23, 42, 220) if is_dark else (241, 245, 249, 230), outline=(71, 85, 105, 200) if is_dark else (203, 213, 225, 220), width=1 * s)
            draw.ellipse([dot_x, dot_y, dot_x + dot_dia, dot_y + dot_dia], fill=(148, 163, 184, 180) if is_dark else (100, 116, 139, 200))
            draw.text((tx, ty), st_text, font=f_st, fill=(203, 213, 225, 255) if is_dark else (71, 85, 105, 255))

        stats = get_day_stats(user_data)
        metrics = [
            ("ONLINE TIME" if is_en else "ВРЕМЯ ОНЛАЙН", stats["formatted_total"], (56, 189, 248, 255) if is_dark else (2, 132, 199, 255)),
            ("SESSIONS" if is_en else "СЕССИЙ", str(stats["sessions_count"]), (245, 158, 11, 255) if is_dark else (217, 119, 6, 255)),
            ("AVG SESSION" if is_en else "СР. СЕССИЯ", stats["formatted_avg"], (56, 189, 248, 255) if is_dark else (2, 132, 199, 255)),
            ("PEAK ACTIVITY" if is_en else "ПИК АКТИВНОСТИ", stats["peak_hour"], (168, 85, 247, 255) if is_dark else (147, 51, 234, 255))
        ]
        card_y = 128 * s
        card_w = (w - 100 * s - (3 * 16 * s)) // 4
        card_h = 86 * s
        for i, (lbl, val, col) in enumerate(metrics):
            cx = 50 * s + i * (card_w + 16 * s)
            draw.rounded_rectangle([cx, card_y, cx + card_w, card_y + card_h], radius=12 * s,
                                   fill=card_fill, outline=card_stroke, width=1 * s)
            draw.text((cx + 16 * s, card_y + 14 * s), lbl, font=f_lbl, fill=text_sub)
            draw.text((cx + 16 * s, card_y + 38 * s), val, font=f_val, fill=col)

        box_y = 232 * s
        box_h = 224 * s
        draw.rounded_rectangle([50 * s, box_y, w - 50 * s, box_y + box_h], radius=14 * s,
                               fill=box_fill, outline=box_stroke, width=1 * s)
        timeline_header = "HOURLY INTENSITY TIMELINE (24 HOURS)" if is_en else "ПОЧАСОВОЙ ГРАФИК ИНТЕНСИВНОСТИ (24 ЧАСА)"
        timeline_sub = "Activity min / hr" if is_en else "Мин. активности в час"
        draw.text((70 * s, box_y + 15 * s), timeline_header, font=f_lbl, fill=text_sub)
        draw.text((w - 230 * s, box_y + 15 * s), timeline_sub, font=f_small, fill=axis_col)

        g_left = 72 * s
        g_right = w - 72 * s
        g_width = g_right - g_left
        g_bottom = box_y + box_h - 38 * s
        g_top = box_y + 50 * s
        g_height = g_bottom - g_top

        for grid_min in (15, 30, 45, 60):
            gy = g_bottom - int((grid_min / 60.0) * g_height)
            draw.line([(g_left, gy), (g_right, gy)], fill=grid_col, width=1 * s)

        hourly_act = stats.get("hourly", [0] * 24)
        col_w = (g_width - (23 * 8 * s)) / 24.0

        for hr in range(24):
            mins = hourly_act[hr] if hr < len(hourly_act) else 0
            bx = g_left + hr * (col_w + 8 * s)
            draw.rounded_rectangle([bx, g_top, bx + col_w, g_bottom], radius=4 * s, fill=bar_empty)
            if mins > 0:
                bar_h = max(6 * s, int((min(60, mins) / 60.0) * g_height))
                by = g_bottom - bar_h
                t_frac = min(1.0, mins / 60.0)
                bar_col = (
                    int(56 * (1 - t_frac) + 168 * t_frac),
                    int(189 * (1 - t_frac) + 85 * t_frac),
                    int(248 * (1 - t_frac) + 247 * t_frac),
                    230
                )
                draw.rounded_rectangle([bx, by, bx + col_w, g_bottom], radius=4 * s, fill=bar_col)
                draw.rounded_rectangle([bx, by, bx + col_w, min(by + 3 * s, g_bottom)], radius=2 * s, fill=(255, 255, 255, 220))

        for hr, hlabel in ((0, "00:00"), (4, "04:00"), (8, "08:00"), (12, "12:00"), (16, "16:00"), (20, "20:00"), (23, "23:00")):
            tx_axis = g_left + hr * (col_w + 8 * s)
            draw.text((tx_axis - 6 * s, g_bottom + 8 * s), hlabel, font=f_small, fill=axis_col)

        an_y = 472 * s
        an_h = 148 * s
        an_w = (w - 100 * s - (2 * 16 * s)) // 3

        sleep_range = "01:00 — 08:30"
        try:
            night_hours = [hr for hr in range(24) if hourly_act[hr] == 0]
            if night_hours:
                start_h = min([h for h in night_hours if h >= 22] or [0])
                end_h = max([h for h in night_hours if h <= 10] or [7])
                sleep_range = f"{start_h:02d}:00 — {end_h:02d}:00"
        except Exception:
            pass

        peak_h = stats.get("peak_hour", "14:00")
        prob_text = (f"High near {peak_h}" if peak_h != "—" else "Steady activity") if is_en else (f"Высокая около {peak_h}" if peak_h != "—" else "Равномерная активность")
        total_reads = user_data.get("total_reads", 0)
        events_len = len(user_data.get("history", []))
        interaction_text = f"Events: {events_len} • Reads: {total_reads}" if is_en else f"Событий: {events_len} • Прочтений: {total_reads}"

        an_cols = [
            ("SLEEP & ROUTINE" if is_en else "РЕЖИМ И СОН", sleep_range, "Typical offline interval" if is_en else "Типичный интервал оффлайна", (56, 189, 248, 255) if is_dark else (2, 132, 199, 255), 0.85),
            ("ACTIVITY FORECAST" if is_en else "ПРОГНОЗ АКТИВНОСТИ", prob_text, "Peak appearance likelihood" if is_en else "Пиковая вероятность появления", (245, 158, 11, 255) if is_dark else (217, 119, 6, 255), 0.70),
            ("DAILY INTENSITY" if is_en else "ИНТЕНСИВНОСТЬ ДНЯ", interaction_text, "Online engagement level" if is_en else "Уровень взаимодействия в сети", (168, 85, 247, 255) if is_dark else (147, 51, 234, 255), 0.90)
        ]

        for i, (title, val, desc, col, prog) in enumerate(an_cols):
            cx = 50 * s + i * (an_w + 16 * s)
            draw.rounded_rectangle([cx, an_y, cx + an_w, an_y + an_h], radius=14 * s,
                                   fill=box_fill, outline=box_stroke, width=1 * s)
            draw.text((cx + 18 * s, an_y + 16 * s), title, font=f_lbl, fill=text_sub)
            draw.text((cx + 18 * s, an_y + 46 * s), val, font=self._get_font(18 * s, True), fill=col)
            draw.text((cx + 18 * s, an_y + 82 * s), desc, font=f_small, fill=text_sub)
            draw.rounded_rectangle([cx + 18 * s, an_y + 116 * s, cx + an_w - 18 * s, an_y + 120 * s], radius=2 * s, fill=prog_bg)
            draw.rounded_rectangle([cx + 18 * s, an_y + 116 * s, cx + 18 * s + int((an_w - 36 * s) * prog), an_y + 120 * s], radius=2 * s, fill=col)

        draw.text((50 * s, h - 34 * s), "OMNISCIENT REBORN", font=f_lbl, fill=brand_col)
        draw.text((w - 240 * s, h - 34 * s), "powered by exteraGram", font=f_lbl, fill=brand_col)

        if not output_path:
            output_path = os.path.join(os.path.expanduser("~"), f"omniscient_card_{user_data.get('id', 'user')}.png")
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        img.save(output_path, "PNG")
        return output_path
