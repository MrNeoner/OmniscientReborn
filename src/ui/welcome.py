import os

try:
    from android.view import Gravity, View
    from android.widget import FrameLayout, LinearLayout, ImageView, TextView, ScrollView
    from android.graphics.drawable import GradientDrawable, Drawable
    from android.graphics import BitmapFactory, Typeface
    from org.telegram.messenger import AndroidUtilities, ApplicationLoader
    from org.telegram.ui.ActionBar import Theme, BottomSheet
    from android_utils import OnClickListener, run_on_ui_thread, log
except Exception:
    Gravity = View = FrameLayout = LinearLayout = ImageView = TextView = ScrollView = None
    GradientDrawable = Drawable = BitmapFactory = Typeface = AndroidUtilities = ApplicationLoader = Theme = BottomSheet = None
    OnClickListener = run_on_ui_thread = None
    def log(msg): print(msg)

def c(val):
    if isinstance(val, int):
        val = val & 0xFFFFFFFF
        if val > 0x7FFFFFFF:
            return val - 0x100000000
        return val
    return 0

def get_telegram_drawable_id(ctx, *names):
    if not ctx:
        return 0
    try:
        res = ctx.getResources()
        pkg = ctx.getPackageName()
        for name in names:
            try:
                rid = res.getIdentifier(str(name), "drawable", pkg)
                if rid != 0:
                    return rid
            except Exception:
                pass
    except Exception:
        pass
    return 0

def _t(plugin, ru, en):
    try:
        lang = getattr(plugin, "get_lang_code", lambda: "ru")()
        if lang == "en":
            return en
    except Exception:
        pass
    return ru

class OmniWelcomeUI:
    @staticmethod
    def resolve_res_path(plugin, filename: str) -> str:
        if not filename:
            return ""

        for mod_name in ("assets", "elyx.assets"):
            try:
                import sys
                m = sys.modules.get(mod_name)
                if not m:
                    m = __import__(mod_name, fromlist=["*"])
                if m:
                    stem = os.path.splitext(filename)[0]
                    for key in (stem, filename, filename.lower()):
                        obj = getattr(m, key, None)
                        if not obj and hasattr(m, "res"):
                            obj = getattr(m.res, key, None)
                        if not obj and hasattr(m, "assets"):
                            obj = getattr(m.assets, key, None)
                        if obj:
                            for p_attr in ("path_str", "path"):
                                p = getattr(obj, p_attr, None)
                                if p and os.path.exists(str(p)):
                                    return str(p)
                            if hasattr(obj, "java_file"):
                                jf = getattr(obj, "java_file")
                                if jf and hasattr(jf, "getAbsolutePath"):
                                    p = str(jf.getAbsolutePath())
                                    if os.path.exists(p):
                                        return p
            except Exception:
                pass

        for meth in ("_asset_path", "_res_path"):
            if hasattr(plugin, meth):
                try:
                    p = getattr(plugin, meth)(filename)
                    if p and os.path.exists(p):
                        return p
                except Exception:
                    pass

        try:
            from main import find_plugin_file
            for pref in ("res", "assets", "OmniscientReborn/res", "OmniscientReborn/assets", ""):
                t = os.path.join(pref, filename) if pref else filename
                cand = find_plugin_file(t)
                if cand and os.path.exists(cand):
                    return cand
        except Exception:
            pass

        try:
            from org.telegram.messenger import ApplicationLoader
            fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
            for folder in ("omniscient_reborn", "OmniscientReborn", "Omniscient_Reborn", "notifcont", ""):
                for sub in ("res", "assets", "OmniscientReborn/res", "OmniscientReborn/assets", ""):
                    if folder:
                        cand = os.path.join(fdir, "plugins", "ElyxPlugins", folder, sub, filename)
                        if os.path.exists(cand):
                            return cand
                        cand2 = os.path.join(fdir, "plugins", folder, sub, filename)
                        if os.path.exists(cand2):
                            return cand2
                        cand3 = os.path.join(fdir, folder, sub, filename)
                        if os.path.exists(cand3):
                            return cand3
                    else:
                        cand = os.path.join(fdir, sub, filename)
                        if os.path.exists(cand):
                            return cand
        except Exception:
            pass

        try:
            f_val = globals().get("__file__")
            curr = os.path.dirname(os.path.abspath(f_val)) if f_val else ""
            if curr:
                for _ in range(7):
                    for folder in ("res", "assets", os.path.join("OmniscientReborn", "res"), os.path.join("OmniscientReborn", "assets"), ""):
                        cand = os.path.join(curr, folder, filename) if folder else os.path.join(curr, filename)
                        if os.path.exists(cand):
                            return cand
                    curr = os.path.dirname(curr)
        except Exception:
            pass

        try:
            from org.telegram.messenger import ApplicationLoader
            fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
            cache_dir = os.path.join(fdir, "cache", "omniscient_res")
            target = os.path.join(cache_dir, filename)
            if os.path.exists(target):
                return target

            import zipfile
            plugins_dir = os.path.join(fdir, "plugins")
            if os.path.exists(plugins_dir):
                for root_dir, _, files in os.walk(plugins_dir):
                    for fn in files:
                        if fn.endswith((".eaf", ".zip")) and any(k in fn.lower() for k in ("omniscient", "reborn", "notif")):
                            archive = os.path.join(root_dir, fn)
                            try:
                                with zipfile.ZipFile(archive, 'r') as zf:
                                    for zname in zf.namelist():
                                        if zname.endswith("/" + filename) or zname == filename:
                                            os.makedirs(cache_dir, exist_ok=True)
                                            with open(target, "wb") as out_f:
                                                out_f.write(zf.read(zname))
                                            return target
                            except Exception:
                                pass
        except Exception:
            pass

        return ""

    @staticmethod
    def set_image_from_res(plugin, view, filenames):
        if not view:
            return False

        if isinstance(filenames, str):
            filenames = [filenames]

        for fname in filenames:

            for mod_name in ("assets", "elyx.assets"):
                try:
                    import sys
                    m = sys.modules.get(mod_name)
                    if not m:
                        m = __import__(mod_name, fromlist=["*"])
                    if m:
                        stem = os.path.splitext(fname)[0]
                        for key in (stem, fname, fname.lower()):
                            obj = getattr(m, key, None)
                            if not obj and hasattr(m, "res"):
                                obj = getattr(m.res, key, None)
                            if not obj and hasattr(m, "assets"):
                                obj = getattr(m.assets, key, None)
                            if obj:
                                if hasattr(obj, "to_drawable"):
                                    try:
                                        d = obj.to_drawable()
                                        if d is not None:
                                            view.setImageDrawable(d)
                                            return True
                                    except Exception:
                                        pass
                                for p_attr in ("path_str", "path"):
                                    p = getattr(obj, p_attr, None)
                                    if p and os.path.exists(str(p)):
                                        try:
                                            if BitmapFactory is not None:
                                                bmp = BitmapFactory.decodeFile(str(p))
                                                if bmp is not None:
                                                    view.setImageBitmap(bmp)
                                                    return True
                                        except Exception:
                                            pass
                                if hasattr(obj, "java_file"):
                                    jf = getattr(obj, "java_file")
                                    if jf and hasattr(jf, "getAbsolutePath"):
                                        p = str(jf.getAbsolutePath())
                                        if os.path.exists(p):
                                            try:
                                                if BitmapFactory is not None:
                                                    bmp = BitmapFactory.decodeFile(p)
                                                    if bmp is not None:
                                                        view.setImageBitmap(bmp)
                                                        return True
                                            except Exception:
                                                pass
                except Exception:
                    pass

            p = OmniWelcomeUI.resolve_res_path(plugin, fname)
            if p and os.path.exists(p):
                if BitmapFactory is not None:
                    try:
                        bmp = BitmapFactory.decodeFile(p)
                        if bmp is not None:
                            view.setImageBitmap(bmp)
                            return True
                    except Exception:
                        pass
                if Drawable is not None:
                    try:
                        d = Drawable.createFromPath(p)
                        if d is not None:
                            view.setImageDrawable(d)
                            return True
                    except Exception:
                        pass
        return False

    @staticmethod
    def load_web_avatar(icon_view, avatar_inner=None, dp_func=None, url="https://github.com/MrNeoner.png"):
        if not icon_view:
            return

        def _circle_crop_bytes(raw_bytes: bytes) -> bytes:
            try:
                from PIL import Image, ImageDraw
                import io
                im = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
                w, h = im.size
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 2
                im = im.crop((left, top, left + min_dim, top + min_dim))

                scale = 4
                big_dim = min_dim * scale
                big_mask = Image.new("L", (big_dim, big_dim), 0)
                draw = ImageDraw.Draw(big_mask)
                draw.ellipse((0, 0, big_dim, big_dim), fill=255)
                mask = big_mask.resize((min_dim, min_dim), Image.Resampling.LANCZOS)

                im.putalpha(mask)

                out = io.BytesIO()
                im.save(out, format="PNG")
                return out.getvalue()
            except Exception as e:
                log(f"[OmniWelcomeUI] Circle crop error: {e}")
                return raw_bytes

        def _fetch():
            try:
                import urllib.request
                import ssl
                import os

                cache_file = ""
                try:
                    if ApplicationLoader is not None:
                        fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
                        cache_dir = os.path.join(fdir, "cache", "omniscient_res")
                        os.makedirs(cache_dir, exist_ok=True)
                        cache_file = os.path.join(cache_dir, "web_avatar_circle_v4.png")
                except Exception:
                    pass

                if cache_file and os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
                    try:
                        if BitmapFactory is not None and run_on_ui_thread:
                            bmp = BitmapFactory.decodeFile(cache_file)
                            if bmp is not None:
                                def apply_cached():
                                    try:
                                        if avatar_inner and dp_func:
                                            avatar_inner.setPadding(dp_func(2.5), dp_func(2.5), dp_func(2.5), dp_func(2.5))
                                        icon_view.setImageBitmap(bmp)
                                    except Exception:
                                        pass
                                run_on_ui_thread(apply_cached)
                    except Exception:
                        pass

                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "OmniscientReborn/2.0 (Android)"}
                )
                with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as resp:
                    raw_data = resp.read()

                if raw_data and len(raw_data) > 100:
                    circular_data = _circle_crop_bytes(raw_data)

                    if cache_file:
                        try:
                            with open(cache_file, "wb") as f:
                                f.write(circular_data)
                        except Exception:
                            pass

                    if BitmapFactory is not None and run_on_ui_thread:
                        bmp = None
                        if cache_file and os.path.exists(cache_file):
                            try:
                                bmp = BitmapFactory.decodeFile(cache_file)
                            except Exception:
                                pass
                        if bmp is None:
                            try:
                                bmp = BitmapFactory.decodeByteArray(circular_data, 0, len(circular_data))
                            except Exception:
                                pass

                        if bmp is not None:
                            def update_avatar():
                                try:
                                    if avatar_inner and dp_func:
                                        avatar_inner.setPadding(dp_func(2.5), dp_func(2.5), dp_func(2.5), dp_func(2.5))
                                    icon_view.setImageBitmap(bmp)
                                except Exception:
                                    pass
                            run_on_ui_thread(update_avatar)
            except Exception as e:
                log(f"[OmniWelcomeUI] Web avatar error: {e}")

        import threading
        t = threading.Thread(target=_fetch, daemon=True)
        t.start()

    @staticmethod
    def open_url(ctx, url: str):
        if not url:
            return
        try:
            from org.telegram.messenger.browser import Browser
            if ctx is not None:
                Browser.openUrl(ctx, url)
                return
        except Exception:
            pass
        try:
            from android.content import Intent
            from android.net import Uri
            from org.telegram.messenger import ApplicationLoader
            intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            c_ctx = ctx or (ApplicationLoader.applicationContext if ApplicationLoader else None)
            if c_ctx is not None:
                c_ctx.startActivity(intent)
        except Exception:
            pass

    @staticmethod
    def load_web_banner(bg_view, bg_container, dp_func, url):
        if not url or bg_view is None:
            return

        urls = [url] if isinstance(url, str) else list(url)

        def _fetch_banner():
            try:
                import urllib.request
                import ssl
                import hashlib

                for u in urls:
                    if not u:
                        continue
                    try:
                        cache_file = ""
                        try:
                            from org.telegram.messenger import ApplicationLoader
                            if ApplicationLoader is not None:
                                fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
                                cdir = os.path.join(fdir, "cache", "omniscient_ui")
                                os.makedirs(cdir, exist_ok=True)
                                h = hashlib.md5(u.encode("utf-8")).hexdigest()[:12]
                                cache_file = os.path.join(cdir, f"web_banner_{h}.png")
                        except Exception:
                            pass

                        if cache_file and os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
                            try:
                                if BitmapFactory is not None and run_on_ui_thread:
                                    bmp = BitmapFactory.decodeFile(cache_file)
                                    if bmp is not None:
                                        run_on_ui_thread(lambda b=bmp: bg_view.setImageBitmap(b))
                                        return
                            except Exception:
                                pass

                        ssl_ctx = ssl.create_default_context()
                        ssl_ctx.check_hostname = False
                        ssl_ctx.verify_mode = ssl.CERT_NONE

                        req = urllib.request.Request(
                            u,
                            headers={"User-Agent": "OmniscientReborn/2.0 (Android)"}
                        )
                        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as resp:
                            raw_data = resp.read()

                        if raw_data and len(raw_data) > 100:
                            if cache_file:
                                try:
                                    with open(cache_file, "wb") as f:
                                        f.write(raw_data)
                                except Exception:
                                    pass

                            if BitmapFactory is not None and run_on_ui_thread:
                                bmp = None
                                if cache_file and os.path.exists(cache_file):
                                    try:
                                        bmp = BitmapFactory.decodeFile(cache_file)
                                    except Exception:
                                        pass
                                if bmp is None:
                                    try:
                                        bmp = BitmapFactory.decodeByteArray(raw_data, 0, len(raw_data))
                                    except Exception:
                                        pass
                                if bmp is not None:
                                    run_on_ui_thread(lambda b=bmp: bg_view.setImageBitmap(b))
                                    return
                    except Exception:
                        continue
            except Exception as e:
                log(f"[OmniWelcomeUI] Web banner error: {e}")
            except Exception as e:
                log(f"[OmniWelcomeUI] Web banner error: {e}")

        import threading
        t = threading.Thread(target=_fetch_banner, daemon=True)
        t.start()

    @staticmethod
    def show_about_sheet(plugin, ctx):
        if ctx is None or LinearLayout is None:
            return

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            sheet = None
            if BottomSheet is not None:
                try:
                    sheet = BottomSheet(ctx, True)
                except Exception:
                    sheet = None

            sheet_root = LinearLayout(ctx)
            sheet_root.setOrientation(LinearLayout.VERTICAL)
            sheet_root.setPadding(dp(20), dp(16), dp(20), dp(20))
            sheet_bg_color = 0xFF141C2B if dark else 0xFFFFFFFF
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
            g_lp.bottomMargin = dp(14)
            sheet_root.addView(grabber, g_lp)

            head_row = LinearLayout(ctx)
            head_row.setOrientation(LinearLayout.HORIZONTAL)
            head_row.setGravity(Gravity.CENTER_VERTICAL)

            title_tv = TextView(ctx)
            title_tv.setText("Omniscient Reborn")
            title_tv.setTextSize(1, 20.0)
            title_tv.setTextColor(c(0xFFFFFFFF if dark else 0xFF0F172A))
            try:
                title_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            head_row.addView(title_tv)

            v_chip = LinearLayout(ctx)
            v_chip.setOrientation(LinearLayout.HORIZONTAL)
            v_chip.setGravity(Gravity.CENTER_VERTICAL)
            v_bg = GradientDrawable()
            v_bg.setColor(c(0x2500E5FF if dark else 0x180284C7))
            v_bg.setCornerRadius(float(dp(10)))
            v_bg.setStroke(dp(1), c(0x6000E5FF if dark else 0x400284C7))
            v_chip.setBackground(v_bg)
            v_chip.setPadding(dp(7), dp(2), dp(7), dp(2))

            v_dot = View(ctx)
            vd_bg = GradientDrawable()
            vd_bg.setShape(GradientDrawable.OVAL)
            vd_bg.setColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            v_dot.setBackground(vd_bg)
            vd_lp = LinearLayout.LayoutParams(dp(6), dp(6))
            vd_lp.gravity = Gravity.CENTER_VERTICAL
            vd_lp.rightMargin = dp(4)
            v_chip.addView(v_dot, vd_lp)

            ver_str = f"v{getattr(plugin, 'version', '2.0.0')}"
            v_text = TextView(ctx)
            v_text.setText(ver_str)
            v_text.setTextSize(1, 10.5)
            v_text.setTextColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            try:
                v_text.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            v_chip.addView(v_text)

            vc_lp = LinearLayout.LayoutParams(-2, -2)
            vc_lp.leftMargin = dp(10)
            head_row.addView(v_chip, vc_lp)
            sheet_root.addView(head_row, LinearLayout.LayoutParams(-1, -2))

            sub_tv = TextView(ctx)
            sub_tv.setText(_t(plugin, "Автономный мониторинг активности контактов", "Autonomous contact activity monitoring"))
            sub_tv.setTextSize(1, 13.0)
            sub_tv.setTextColor(c(0xFF9AA4B2))
            sub_lp = LinearLayout.LayoutParams(-1, -2)
            sub_lp.topMargin = dp(4)
            sub_lp.bottomMargin = dp(14)
            sheet_root.addView(sub_tv, sub_lp)

            scroll = ScrollView(ctx)
            scroll_content = LinearLayout(ctx)
            scroll_content.setOrientation(LinearLayout.VERTICAL)

            intro_card = LinearLayout(ctx)
            intro_card.setOrientation(LinearLayout.VERTICAL)
            ic_bg = GradientDrawable()
            ic_bg.setColor(c(0x221E293B if dark else 0x08000000))
            ic_bg.setCornerRadius(float(dp(14)))
            ic_bg.setStroke(dp(1), c(0x2538BDF8 if dark else 0x15000000))
            intro_card.setBackground(ic_bg)
            intro_card.setPadding(dp(14), dp(12), dp(14), dp(12))

            intro_txt = TextView(ctx)
            intro_txt.setText(_t(
                plugin,
                "Omniscient Reborn — инструмент для детального отслеживания активности в Telegram. Работает полностью автономно на вашем устройстве, сохраняя данные в локальной базе.",
                "Omniscient Reborn is an autonomous tool for tracking contact activity in Telegram. Runs entirely locally on your device, storing all history in an encrypted local database."
            ))
            intro_txt.setTextSize(1, 13.0)
            intro_txt.setTextColor(c(0xFFCBD5E1 if dark else 0xFF334155))
            intro_card.addView(intro_txt)
            scroll_content.addView(intro_card, LinearLayout.LayoutParams(-1, -2))

            feat_card = LinearLayout(ctx)
            feat_card.setOrientation(LinearLayout.VERTICAL)
            fc_bg = GradientDrawable()
            fc_bg.setColor(c(0x221E293B if dark else 0x08000000))
            fc_bg.setCornerRadius(float(dp(14)))
            fc_bg.setStroke(dp(1), c(0x2538BDF8 if dark else 0x15000000))
            feat_card.setBackground(fc_bg)
            feat_card.setPadding(dp(14), dp(12), dp(14), dp(12))
            fc_lp = LinearLayout.LayoutParams(-1, -2)
            fc_lp.topMargin = dp(10)

            feat_title = TextView(ctx)
            feat_title.setText(_t(plugin, "Возможности системы", "System Features"))
            feat_title.setTextSize(1, 14.5)
            feat_title.setTextColor(c(0xFFFFFFFF if dark else 0xFF0F172A))
            try:
                feat_title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            feat_card.addView(feat_title)

            if _t(plugin, "ru", "en") == "ru":
                features = [
                    ("Точный трекинг сессий", "Фиксация времени входа и выхода, а также коротких сессий в реальном времени."),
                    ("События набора и прочтения", "Детекция момента набора текста и прочтения входящих сообщений."),
                    ("24ч инфографика", "Почасовая визуализация суточной активности с экспортом в высоком качестве."),
                    ("Локальное хранение", "Полная автономность без отправки ваших данных на внешние сервера."),
                    ("Экспорт и бэкапы", "Сохранение графиков в PNG, экспорт в CSV/TXT и резервные копии базы данных.")
                ]
            else:
                features = [
                    ("Accurate Session Tracking", "Real-time detection of online/offline events and short sessions."),
                    ("Typing & Read Events", "Instant detection of typing status and incoming message reads."),
                    ("24h Infographics", "Hourly activity chart visualization with high quality export."),
                    ("Local & Private", "Complete autonomy without sending any personal data to external servers."),
                    ("Export & Backups", "Save charts to PNG, export history to CSV/TXT and create database backups.")
                ]

            for h, desc in features:
                f_box = LinearLayout(ctx)
                f_box.setOrientation(LinearLayout.VERTICAL)
                fb_lp = LinearLayout.LayoutParams(-1, -2)
                fb_lp.topMargin = dp(8)

                h_tv = TextView(ctx)
                h_tv.setText(h)
                h_tv.setTextSize(1, 13.0)
                h_tv.setTextColor(c(0xFF38BDF8 if dark else 0xFF0284C7))
                try:
                    h_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                f_box.addView(h_tv)

                d_tv = TextView(ctx)
                d_tv.setText(desc)
                d_tv.setTextSize(1, 12.0)
                d_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                d_lp = LinearLayout.LayoutParams(-1, -2)
                d_lp.topMargin = dp(2)
                f_box.addView(d_tv, d_lp)

                feat_card.addView(f_box, fb_lp)

            scroll_content.addView(feat_card, fc_lp)

            guide_card = LinearLayout(ctx)
            guide_card.setOrientation(LinearLayout.VERTICAL)
            gc_bg = GradientDrawable()
            gc_bg.setColor(c(0x221E293B if dark else 0x08000000))
            gc_bg.setCornerRadius(float(dp(14)))
            gc_bg.setStroke(dp(1), c(0x2538BDF8 if dark else 0x15000000))
            guide_card.setBackground(gc_bg)
            guide_card.setPadding(dp(14), dp(12), dp(14), dp(12))
            gc_lp = LinearLayout.LayoutParams(-1, -2)
            gc_lp.topMargin = dp(10)

            guide_title = TextView(ctx)
            guide_title.setText(_t(plugin, "Как использовать плагин", "How to Use"))
            guide_title.setTextSize(1, 14.5)
            guide_title.setTextColor(c(0xFFFFFFFF if dark else 0xFF0F172A))
            try:
                guide_title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            guide_card.addView(guide_title)

            if _t(plugin, "ru", "en") == "ru":
                guides = [
                    ("1. Добавление из профиля", "Откройте профиль нужного пользователя, нажмите 3 точки в правом верхнем углу и выберите «Отслеживать активность»."),
                    ("2. Добавление по ID", "В настройках плагина нажмите кнопку «+ Добавить контакт» в верхней части экрана и введите цифровой Telegram ID."),
                    ("3. Инфографика и детальный лог", "Нажмите на контакт в списке отслеживаемых, чтобы открыть карточку сессий, просмотреть хронику или сгенерировать 24ч график."),
                    ("4. Фоновый режим (WakeLock)", "Чтобы отслеживание не прерывалось при блокировке экрана, включите WakeLock в разделе «Логи и хранилище» настроек.")
                ]
            else:
                guides = [
                    ("1. Add from User Profile", "Open any contact's profile, tap the 3 dots menu in the top-right corner, and select 'Track Activity'."),
                    ("2. Add by Telegram ID", "In plugin settings, tap the '+ Add Contact' button at the top banner and enter their numeric User ID."),
                    ("3. Infographics & Session Logs", "Tap any contact in the tracked list to inspect stats, view chronicle events, or render a 24h infographic image."),
                    ("4. Background Mode (WakeLock)", "To ensure monitoring continues while screen is off, enable WakeLock under 'Logs & Storage' in settings.")
                ]

            for gh, gdesc in guides:
                g_box = LinearLayout(ctx)
                g_box.setOrientation(LinearLayout.VERTICAL)
                gb_lp = LinearLayout.LayoutParams(-1, -2)
                gb_lp.topMargin = dp(8)

                gh_tv = TextView(ctx)
                gh_tv.setText(gh)
                gh_tv.setTextSize(1, 13.0)
                gh_tv.setTextColor(c(0xFF38BDF8 if dark else 0xFF0284C7))
                try:
                    gh_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                g_box.addView(gh_tv)

                gd_tv = TextView(ctx)
                gd_tv.setText(gdesc)
                gd_tv.setTextSize(1, 12.0)
                gd_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
                gd_lp = LinearLayout.LayoutParams(-1, -2)
                gd_lp.topMargin = dp(2)
                g_box.addView(gd_tv, gd_lp)

                guide_card.addView(g_box, gb_lp)

            scroll_content.addView(guide_card, gc_lp)

            scroll.addView(scroll_content, FrameLayout.LayoutParams(-1, -2))
            scroll_lp = LinearLayout.LayoutParams(-1, dp(370))
            sheet_root.addView(scroll, scroll_lp)

            actions_row = LinearLayout(ctx)
            actions_row.setOrientation(LinearLayout.HORIZONTAL)
            ar_lp = LinearLayout.LayoutParams(-1, -2)
            ar_lp.topMargin = dp(12)

            ch_btn = TextView(ctx)
            ch_btn.setText(_t(plugin, "Канал @neo_plugin", "Channel @neo_plugin"))
            ch_btn.setTextSize(1, 13.0)
            ch_btn.setGravity(Gravity.CENTER)
            ch_btn.setTextColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            try:
                ch_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            ch_shape = GradientDrawable()
            ch_shape.setCornerRadius(float(dp(12)))
            ch_shape.setColor(c(0x2000E5FF if dark else 0x180284C7))
            ch_shape.setStroke(dp(1), c(0x5000E5FF if dark else 0x400284C7))
            ch_btn.setBackground(ch_shape)
            ch_btn.setClickable(True)
            ch_btn.setFocusable(True)
            if OnClickListener:
                def _open_ch(*a):
                    if sheet is not None:
                        try: sheet.dismiss()
                        except Exception: pass
                    OmniWelcomeUI.open_url(ctx, "https://t.me/neo_plugin")
                ch_btn.setOnClickListener(OnClickListener(_open_ch))
            actions_row.addView(ch_btn, LinearLayout.LayoutParams(0, dp(42), 1.0))

            dev_btn = TextView(ctx)
            dev_btn.setText(_t(plugin, "Разработчик", "Developer"))
            dev_btn.setTextSize(1, 13.0)
            dev_btn.setGravity(Gravity.CENTER)
            dev_btn.setTextColor(c(0xFFCBD5E1 if dark else 0xFF334155))
            try:
                dev_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            dev_shape = GradientDrawable()
            dev_shape.setCornerRadius(float(dp(12)))
            dev_shape.setColor(c(0x1AFFFFFF if dark else 0x0A000000))
            dev_shape.setStroke(dp(1), c(0x30FFFFFF if dark else 0x18000000))
            dev_btn.setBackground(dev_shape)
            dev_btn.setClickable(True)
            dev_btn.setFocusable(True)
            if OnClickListener:
                def _open_dev(*a):
                    if sheet is not None:
                        try: sheet.dismiss()
                        except Exception: pass
                    OmniWelcomeUI.open_url(ctx, "https://t.me/mrneoner")
                dev_btn.setOnClickListener(OnClickListener(_open_dev))
            dev_lp = LinearLayout.LayoutParams(0, dp(42), 1.0)
            dev_lp.leftMargin = dp(8)
            actions_row.addView(dev_btn, dev_lp)

            sheet_root.addView(actions_row, ar_lp)

            close_btn = TextView(ctx)
            close_btn.setText(_t(plugin, "Закрыть", "Close"))
            close_btn.setTextSize(1, 14.5)
            close_btn.setGravity(Gravity.CENTER)
            close_btn.setTextColor(c(0xFFFFFFFF))
            try:
                close_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            close_shape = GradientDrawable()
            close_shape.setCornerRadius(float(dp(12)))
            close_shape.setColor(c(0xFF0284C7 if dark else 0xFF0F172A))
            close_btn.setBackground(close_shape)
            close_btn.setClickable(True)
            close_btn.setFocusable(True)
            if sheet is not None and OnClickListener:
                close_btn.setOnClickListener(OnClickListener(lambda *a: sheet.dismiss()))

            close_lp = LinearLayout.LayoutParams(-1, dp(44))
            close_lp.topMargin = dp(8)
            sheet_root.addView(close_btn, close_lp)

            if sheet is not None:
                sheet.setCustomView(sheet_root)
                sheet.show()
            else:
                from ui.alert import AlertDialogBuilder
                AlertDialogBuilder(ctx).setTitle(_t(plugin, "О плагине Omniscient Reborn", "About Omniscient Reborn")).setMessage(
                    _t(
                        plugin,
                        f"Omniscient Reborn {ver_str}\n\nАвтономный комплекс отслеживания онлайна, прочтений и набора текста контактов в реальном времени с 24-часовой аналитикой.\n\nКанал: @neo_plugin\nРазработчик: @mrneoner",
                        f"Omniscient Reborn {ver_str}\n\nAutonomous real-time tracking suite for online status, typing, and message reads with 24h analytics.\n\nChannel: @neo_plugin\nDeveloper: @mrneoner"
                    )
                ).setPositiveButton("OK", None).show()
        except Exception as e:
            log(f"[Omniscient Reborn] Error showing about sheet: {e}")

    @staticmethod
    def show_quick_start_sheet(plugin, ctx):
        if ctx is None or LinearLayout is None:
            return

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            sheet = None
            if BottomSheet is not None:
                try:
                    sheet = BottomSheet(ctx, True)
                except Exception:
                    sheet = None

            sheet_root = LinearLayout(ctx)
            sheet_root.setOrientation(LinearLayout.VERTICAL)
            sheet_root.setPadding(dp(20), dp(14), dp(20), dp(18))
            sheet_bg_color = 0xFF141C2B if dark else 0xFFFFFFFF
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

            badge_row = LinearLayout(ctx)
            badge_row.setOrientation(LinearLayout.HORIZONTAL)
            badge_row.setGravity(Gravity.CENTER_VERTICAL)

            badge_pill = TextView(ctx)
            badge_pill.setText(_t(plugin, "🚀 СТАРТ РАБОТЫ", "🚀 GETTING STARTED"))
            badge_pill.setTextSize(1, 9.5)
            badge_pill.setTextColor(c(0xFF38BDF8 if dark else 0xFF0284C7))
            try:
                badge_pill.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            bp_bg = GradientDrawable()
            bp_bg.setCornerRadius(float(dp(6)))
            bp_bg.setColor(c(0x2038BDF8 if dark else 0x180284C7))
            bp_bg.setStroke(dp(1), c(0x5038BDF8 if dark else 0x350284C7))
            badge_pill.setBackground(bp_bg)
            badge_pill.setPadding(dp(7), dp(2), dp(7), dp(2))
            badge_row.addView(badge_pill, LinearLayout.LayoutParams(-2, -2))
            sheet_root.addView(badge_row, LinearLayout.LayoutParams(-1, -2))

            title_tv = TextView(ctx)
            title_tv.setText(_t(plugin, "Добро пожаловать!", "Welcome!"))
            title_tv.setTextSize(1, 20.0)
            title_tv.setTextColor(c(0xFFFFFFFF if dark else 0xFF0F172A))
            try:
                title_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            t_lp = LinearLayout.LayoutParams(-1, -2)
            t_lp.topMargin = dp(4)
            sheet_root.addView(title_tv, t_lp)

            sub_tv = TextView(ctx)
            sub_tv.setText(_t(plugin, "Краткая памятка по работе с плагином:", "Quick guide to get the most out of Omniscient:"))
            sub_tv.setTextSize(1, 12.5)
            sub_tv.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
            s_lp = LinearLayout.LayoutParams(-1, -2)
            s_lp.topMargin = dp(2)
            s_lp.bottomMargin = dp(12)
            sheet_root.addView(sub_tv, s_lp)

            scroll = ScrollView(ctx)
            scroll_content = LinearLayout(ctx)
            scroll_content.setOrientation(LinearLayout.VERTICAL)

            ver = getattr(plugin, "__version__", "2.0.0")

            cards_data = [
                (
                    "💡 " + _t(plugin, "Как вернуться на экран приветствия", "How to reopen welcome screen"),
                    _t(plugin, f"Если вы захотите снова увидеть приветствие или описание функций — просто зажмите строку версии (v{ver}) в самом низу настроек.", f"If you ever need this screen again — simply long-press the version number (v{ver}) at the very bottom of settings."),
                    0xFF00E5FF if dark else 0xFF0284C7
                ),
                (
                    "➕ " + _t(plugin, "Добавление контактов", "Adding Contacts"),
                    _t(plugin, "• Из профиля: откройте профиль пользователя -> меню (3 точки) -> «Отслеживать активность».\n• По ID: в настройках плагина нажмите кнопку «+ Добавить контакт» и введите User ID.", "• From profile: open user profile -> 3-dots menu -> 'Track Activity'.\n• By ID: in settings tap '+ Add Contact' and enter User ID."),
                    0xFF38BDF8 if dark else 0xFF0284C7
                ),
                (
                    "📊 " + _t(plugin, "Инфографика и хроника", "Infographics & Chronicle"),
                    _t(plugin, "Нажмите на контакт в списке настроек для просмотра подробных сессий или генерации суточного 24ч графика в галерею.", "Tap any contact in the tracked list to inspect session events or render a 24-hour visual infographic."),
                    0xFFA855F7 if dark else 0xFF7C3AED
                ),
                (
                    "⚡ " + _t(plugin, "Фоновый режим (WakeLock)", "Background Mode (WakeLock)"),
                    _t(plugin, "Включите WakeLock в разделе «Логи и хранилище», чтобы мониторинг работал непрерывно даже при выключенном экране.", "Enable WakeLock under 'Logs & Storage' in settings if you need active tracking with screen turned off."),
                    0xFFF59E0B if dark else 0xFFD97706
                )
            ]

            for c_title, c_desc, c_col in cards_data:
                item_card = LinearLayout(ctx)
                item_card.setOrientation(LinearLayout.VERTICAL)
                ic_bg = GradientDrawable()
                ic_bg.setColor(c(0x221E293B if dark else 0x08000000))
                ic_bg.setCornerRadius(float(dp(12)))
                ic_bg.setStroke(dp(1), c(0x2538BDF8 if dark else 0x15000000))
                item_card.setBackground(ic_bg)
                item_card.setPadding(dp(12), dp(10), dp(12), dp(10))

                ic_lp = LinearLayout.LayoutParams(-1, -2)
                ic_lp.bottomMargin = dp(8)

                it_tv = TextView(ctx)
                it_tv.setText(c_title)
                it_tv.setTextSize(1, 13.0)
                it_tv.setTextColor(c(c_col))
                try:
                    it_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                item_card.addView(it_tv)

                id_tv = TextView(ctx)
                id_tv.setText(c_desc)
                id_tv.setTextSize(1, 11.5)
                id_tv.setTextColor(c(0xFFCBD5E1 if dark else 0xFF334155))
                id_lp = LinearLayout.LayoutParams(-1, -2)
                id_lp.topMargin = dp(4)
                item_card.addView(id_tv, id_lp)

                scroll_content.addView(item_card, ic_lp)

            scroll.addView(scroll_content, FrameLayout.LayoutParams(-1, -2))
            sheet_root.addView(scroll, LinearLayout.LayoutParams(-1, dp(280)))

            ok_btn = TextView(ctx)
            ok_btn.setText(_t(plugin, "Понятно, приступить к работе", "Got it, let's start"))
            ok_btn.setTextSize(1, 14.5)
            ok_btn.setGravity(Gravity.CENTER)
            ok_btn.setTextColor(c(0xFFFFFFFF))
            try:
                ok_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            ok_shape = GradientDrawable()
            ok_shape.setCornerRadius(float(dp(12)))
            ok_shape.setColor(c(0xFF0284C7 if dark else 0xFF0F172A))
            ok_btn.setBackground(ok_shape)
            ok_btn.setClickable(True)
            ok_btn.setFocusable(True)
            if sheet is not None and OnClickListener:
                ok_btn.setOnClickListener(OnClickListener(lambda *a: sheet.dismiss()))

            ok_lp = LinearLayout.LayoutParams(-1, dp(46))
            ok_lp.topMargin = dp(12)
            sheet_root.addView(ok_btn, ok_lp)

            if sheet is not None:
                sheet.setCustomView(sheet_root)
                sheet.show()
            else:
                from ui.alert import AlertDialogBuilder
                builder = AlertDialogBuilder(ctx)
                builder.set_title(_t(plugin, "Добро пожаловать в Omniscient Reborn!", "Welcome to Omniscient Reborn!"))
                msg = "\n\n".join([f"{t}\n{d}" for t, d, _ in cards_data])
                builder.set_message(msg)
                builder.set_positive_button(_t(plugin, "Понятно", "Got it"), lambda d, w: None)
                builder.show()
        except Exception as e:
            log(f"[OmniWelcomeUI] Error showing quick start sheet: {e}")

    @staticmethod
    def show_changelog_sheet(plugin, ctx):
        if ctx is None or LinearLayout is None:
            return

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            sheet = None
            if BottomSheet is not None:
                try:
                    sheet = BottomSheet(ctx, True)
                except Exception:
                    sheet = None

            sheet_root = LinearLayout(ctx)
            sheet_root.setOrientation(LinearLayout.VERTICAL)
            sheet_root.setPadding(dp(20), dp(16), dp(20), dp(20))
            sheet_bg_color = 0xFF141C2B if dark else 0xFFFFFFFF
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
            g_lp.bottomMargin = dp(14)
            sheet_root.addView(grabber, g_lp)

            title_tv = TextView(ctx)
            title_tv.setText(_t(plugin, "История изменений", "Changelog"))
            title_tv.setTextSize(1, 20.0)
            title_tv.setTextColor(c(0xFFFFFFFF if dark else 0xFF0F172A))
            try:
                title_tv.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            sheet_root.addView(title_tv, LinearLayout.LayoutParams(-1, -2))

            sub_tv = TextView(ctx)
            sub_tv.setText(_t(plugin, "Список обновлений и нововведений Omniscient Reborn", "Updates and new features of Omniscient Reborn"))
            sub_tv.setTextSize(1, 13.0)
            sub_tv.setTextColor(c(0xFF9AA4B2))
            sub_lp = LinearLayout.LayoutParams(-1, -2)
            sub_lp.topMargin = dp(4)
            sub_lp.bottomMargin = dp(16)
            sheet_root.addView(sub_tv, sub_lp)

            empty_card = LinearLayout(ctx)
            empty_card.setOrientation(LinearLayout.VERTICAL)
            empty_card.setGravity(Gravity.CENTER)
            c_bg = GradientDrawable()
            c_bg.setColor(c(0x221E293B if dark else 0x08000000))
            c_bg.setCornerRadius(float(dp(16)))
            c_bg.setStroke(dp(1), c(0x2538BDF8 if dark else 0x15000000))
            empty_card.setBackground(c_bg)
            empty_card.setPadding(dp(20), dp(28), dp(20), dp(28))

            ic = ImageView(ctx)
            ic_id = get_telegram_drawable_id(ctx, "msg_info", "msg_retry")
            if ic_id != 0:
                try:
                    ic.setImageResource(ic_id)
                    ic.setColorFilter(c(0xFF38BDF8 if dark else 0xFF0284C7))
                except Exception:
                    pass
            empty_card.addView(ic, LinearLayout.LayoutParams(dp(36), dp(36)))

            e_title = TextView(ctx)
            e_title.setText(_t(plugin, "История изменений пока пуста", "Changelog is currently empty"))
            e_title.setTextSize(1, 15.5)
            e_title.setTextColor(c(0xFFFFFFFF if dark else 0xFF0F172A))
            try:
                e_title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            e_title_lp = LinearLayout.LayoutParams(-2, -2)
            e_title_lp.topMargin = dp(12)
            empty_card.addView(e_title, e_title_lp)

            e_sub = TextView(ctx)
            e_sub.setText(_t(
                plugin,
                "Подробный список изменений и новых возможностей будет публиковаться вместе с официальными релизами в канале плагина и на GitHub.",
                "Detailed list of changes and new features will be published with official releases in the channel and on GitHub."
            ))
            e_sub.setTextSize(1, 12.5)
            e_sub.setTextColor(c(0xFF94A3B8 if dark else 0xFF64748B))
            e_sub.setGravity(Gravity.CENTER)
            e_sub_lp = LinearLayout.LayoutParams(-1, -2)
            e_sub_lp.topMargin = dp(6)
            empty_card.addView(e_sub, e_sub_lp)

            sheet_root.addView(empty_card, LinearLayout.LayoutParams(-1, -2))

            try:
                from loader import OmniGitHubLoader
                gh_btn = TextView(ctx)
                gh_btn.setText(_t(plugin, "Загрузчик версий", "Version Loader"))
                gh_btn.setTextSize(1, 13.5)
                gh_btn.setGravity(Gravity.CENTER)
                gh_btn.setTextColor(c(0xFF00E5FF if dark else 0xFF0284C7))
                try:
                    gh_btn.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                gh_shape = GradientDrawable()
                gh_shape.setCornerRadius(float(dp(12)))
                gh_shape.setColor(c(0x2000E5FF if dark else 0x180284C7))
                gh_shape.setStroke(dp(1), c(0x5000E5FF if dark else 0x400284C7))
                gh_btn.setBackground(gh_shape)
                gh_btn.setClickable(True)
                gh_btn.setFocusable(True)
                if OnClickListener:
                    def _open_loader(*a):
                        if sheet is not None:
                            try:
                                sheet.dismiss()
                            except Exception:
                                pass
                        OmniGitHubLoader.show_releases_dialog(plugin, ctx)
                    gh_btn.setOnClickListener(OnClickListener(_open_loader))
                gh_lp = LinearLayout.LayoutParams(-1, dp(42))
                gh_lp.topMargin = dp(14)
                sheet_root.addView(gh_btn, gh_lp)
            except Exception:
                pass

            back_btn = TextView(ctx)
            back_btn.setText(_t(plugin, "Закрыть", "Close"))
            back_btn.setTextSize(1, 15.0)
            back_btn.setGravity(Gravity.CENTER)
            back_btn.setTextColor(c(0xFFFFFFFF))
            try:
                back_btn.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            btn_shape = GradientDrawable()
            btn_shape.setCornerRadius(float(dp(12)))
            btn_shape.setColor(c(0xFF0284C7 if dark else 0xFF0F172A))
            back_btn.setBackground(btn_shape)
            back_btn.setClickable(True)
            back_btn.setFocusable(True)
            if sheet is not None and OnClickListener:
                back_btn.setOnClickListener(OnClickListener(lambda *a: sheet.dismiss()))

            btn_lp = LinearLayout.LayoutParams(-1, dp(46))
            btn_lp.topMargin = dp(8)
            sheet_root.addView(back_btn, btn_lp)

            if sheet is not None:
                sheet.setCustomView(sheet_root)
                sheet.show()
            else:
                from ui.alert import AlertDialogBuilder
                AlertDialogBuilder(ctx).setTitle(_t(plugin, "История изменений", "Changelog")).setMessage(
                    _t(
                        plugin,
                        "История изменений пока пуста.\n\nЗаписи будут публиковаться вместе с официальными релизами.",
                        "Changelog is currently empty.\n\nRelease notes will be published with official releases."
                    )
                ).setPositiveButton(_t(plugin, "Закрыть", "Close"), None).show()
        except Exception as e:
            log(f"[Omniscient Reborn] Error showing changelog sheet: {e}")

    @staticmethod
    def open_github_loader(plugin, ctx):
        try:
            import sys
            f_val = globals().get("__file__")
            curr_dir = os.path.dirname(os.path.abspath(f_val)) if f_val else ""
            for base_dir in [
                curr_dir,
                os.path.dirname(curr_dir) if curr_dir else "",
                os.path.dirname(os.path.dirname(curr_dir)) if curr_dir else ""
            ]:
                if base_dir and base_dir not in sys.path:
                    sys.path.insert(0, base_dir)

            loader_mod = None
            try:
                import loader as loader_mod
            except Exception:
                try:
                    from . import loader as loader_mod
                except Exception:
                    try:
                        from .. import loader as loader_mod
                    except Exception:
                        pass

            if loader_mod and hasattr(loader_mod, "OmniGitHubLoader"):
                loader_mod.OmniGitHubLoader.show_releases_dialog(plugin, ctx)
                return

            from loader import OmniGitHubLoader
            OmniGitHubLoader.show_releases_dialog(plugin, ctx)
        except Exception as e:
            try:
                from android_utils import log
                log(f"[OmniWelcomeUI] Error opening loader: {e}")
            except Exception:
                pass

    open_beta_loader = open_github_loader

    @staticmethod
    def create_welcome_view(plugin, ctx, on_continue_click=None):
        if ctx is None or LinearLayout is None or FrameLayout is None:
            return None

        try:
            dark = plugin._is_dark_theme() if hasattr(plugin, "_is_dark_theme") else True
            dp = lambda val: AndroidUtilities.dp(float(val)) if AndroidUtilities else int(val * 2)

            is_beta = getattr(plugin, "is_beta", False)
            if not is_beta and hasattr(plugin, "version"):
                if "beta" in str(plugin.version).lower():
                    is_beta = True

            def open_link(target):
                if hasattr(plugin, "open_tg_link"):
                    try:
                        plugin.open_tg_link(target)
                    except Exception:
                        pass

            root = LinearLayout(ctx)
            root.setOrientation(LinearLayout.VERTICAL)
            root.setGravity(Gravity.CENTER_HORIZONTAL)
            root.setPadding(0, 0, 0, dp(32))

            if hasattr(plugin, "_get_bool") and plugin._get_bool("auto_check_updates", True):
                try:
                    from loader import OmniGitHubLoader
                    OmniGitHubLoader.check_for_updates(plugin, ctx, notify_if_latest=False)
                except Exception:
                    pass

            bg_container = FrameLayout(ctx)
            cbg = GradientDrawable()
            cbg.setShape(GradientDrawable.RECTANGLE)
            cbg.setCornerRadius(float(dp(16)))
            cbg.setColor(c(0xFF000000))
            bg_container.setBackground(cbg)
            try:
                bg_container.setClipToOutline(True)
            except Exception:
                pass

            bg_view = ImageView(ctx)
            bg_view.setScaleType(ImageView.ScaleType.CENTER_CROP)
            banner_files = [
                "welcome_bgdark.png" if dark else "welcome_bg.png",
                "banner_bgdark.png" if dark else "banner_bg.png",
                "welcome_bg.png",
                "banner_bg.png"
            ]
            OmniWelcomeUI.set_image_from_res(plugin, bg_view, banner_files)

            prefix = "https://raw.githubusercontent.com/MrNeoner/OmniscientReborn/refs/heads/main/assets/"
            banner_urls = [
                f"{prefix}{'welcome_bgdark.png' if dark else 'welcome_bg.png'}",
                f"{prefix}{'banner_bgdark.png' if dark else 'banner_bg.png'}",
                f"{prefix}welcome_bg.png",
                f"{prefix}banner_bg.png"
            ]
            if hasattr(plugin, "_get_str"):
                custom_b_url = plugin._get_str("welcome_web_banner_url", "")
                if custom_b_url and custom_b_url.strip():
                    banner_urls.insert(0, custom_b_url.strip())
            OmniWelcomeUI.load_web_banner(bg_view, bg_container, dp, banner_urls)

            bg_container.addView(bg_view, FrameLayout.LayoutParams(-1, -1))
            bg_lp = LinearLayout.LayoutParams(-1, dp(120))
            bg_lp.setMargins(dp(14), dp(10), dp(14), dp(8))
            root.addView(bg_container, bg_lp)

            profile_card = LinearLayout(ctx)
            profile_card.setOrientation(LinearLayout.HORIZONTAL)
            profile_card.setGravity(Gravity.CENTER_VERTICAL)
            profile_card.setPadding(dp(14), dp(12), dp(14), dp(12))

            p_bg = GradientDrawable()
            p_bg.setShape(GradientDrawable.RECTANGLE)
            p_bg.setCornerRadius(float(dp(18)))
            p_bg.setColor(c(0x201E293B if dark else 0x08000000))
            p_bg.setStroke(dp(1), c(0x3538BDF8 if dark else 0x18000000))
            profile_card.setBackground(p_bg)

            avatar_holder = FrameLayout(ctx)
            av_cutout = GradientDrawable()
            av_cutout.setShape(GradientDrawable.OVAL)
            av_cutout.setColor(c(0xFF10192A if dark else 0xFFFFFFFF))
            av_stroke_color = 0xFF38BDF8 if dark else 0xFF0284C7
            av_cutout.setStroke(dp(2), c(av_stroke_color))
            avatar_holder.setBackground(av_cutout)
            avatar_holder.setPadding(dp(3), dp(3), dp(3), dp(3))
            try:
                avatar_holder.setClipToOutline(True)
            except Exception:
                pass

            avatar_inner = FrameLayout(ctx)
            av_inner_shape = GradientDrawable()
            av_inner_shape.setShape(GradientDrawable.OVAL)
            av_inner_shape.setColor(c(0xFF10192A if dark else 0xFFFFFFFF))
            avatar_inner.setBackground(av_inner_shape)
            try:
                avatar_inner.setClipToOutline(True)
            except Exception:
                pass

            icon = ImageView(ctx)
            try:
                icon.setScaleType(ImageView.ScaleType.FIT_CENTER)
                icon.setAdjustViewBounds(True)
                icon.setClipToOutline(True)
            except Exception:
                pass

            avatar_files = ["icon.png"]
            av_loaded = OmniWelcomeUI.set_image_from_res(plugin, icon, avatar_files)
            if not av_loaded:
                ic_id = get_telegram_drawable_id(ctx, "msg_tone_on_solar", "msg_info", "msg_channel")
                if ic_id != 0:
                    try:
                        icon.setImageResource(ic_id)
                        icon.setColorFilter(c(av_stroke_color))
                    except Exception:
                        pass

            web_av_url = "https://github.com/MrNeoner.png"
            if hasattr(plugin, "_get_str"):
                custom_url = plugin._get_str("welcome_web_avatar_url", "")
                if custom_url and custom_url.strip():
                    web_av_url = custom_url.strip()
            OmniWelcomeUI.load_web_avatar(icon, avatar_inner, dp, web_av_url)

            avatar_inner.addView(icon, FrameLayout.LayoutParams(-1, -1, Gravity.CENTER))
            avatar_holder.addView(avatar_inner, FrameLayout.LayoutParams(-1, -1))

            def _open_github(*_):
                OmniWelcomeUI.open_url(ctx, "https://github.com/MrNeoner")

            avatar_holder.setClickable(True)
            avatar_inner.setClickable(True)
            icon.setClickable(True)
            if OnClickListener:
                avatar_holder.setOnClickListener(OnClickListener(_open_github))
                avatar_inner.setOnClickListener(OnClickListener(_open_github))
                icon.setOnClickListener(OnClickListener(_open_github))

            profile_card.addView(avatar_holder, LinearLayout.LayoutParams(dp(58), dp(58)))

            info_col = LinearLayout(ctx)
            info_col.setOrientation(LinearLayout.VERTICAL)
            info_col.setGravity(Gravity.CENTER_VERTICAL)
            info_lp = LinearLayout.LayoutParams(0, -2, 1.0)
            info_lp.leftMargin = dp(12)

            title_row = LinearLayout(ctx)
            title_row.setOrientation(LinearLayout.HORIZONTAL)
            title_row.setGravity(Gravity.CENTER_VERTICAL)

            title = TextView(ctx)
            title.setText("Omniscient Reborn")
            title.setTextSize(1, 18.0)
            title.setTextColor(c(0xFFFFFFFF if dark else 0xFF151A21))
            try:
                title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            title_row.addView(title, LinearLayout.LayoutParams(-2, -2))

            ver_chip = LinearLayout(ctx)
            ver_chip.setOrientation(LinearLayout.HORIZONTAL)
            ver_chip.setGravity(Gravity.CENTER)
            v_bg = GradientDrawable()
            v_bg.setColor(c(0x2500E5FF if dark else 0x180284C7))
            v_bg.setCornerRadius(float(dp(10)))
            v_bg.setStroke(dp(1), c(0x6000E5FF if dark else 0x400284C7))
            ver_chip.setBackground(v_bg)
            ver_chip.setPadding(dp(7), dp(2), dp(7), dp(2))
            ver_chip.setClickable(True)
            ver_chip.setFocusable(True)
            if OnClickListener:
                ver_chip.setOnClickListener(OnClickListener(lambda *a: OmniWelcomeUI.show_changelog_sheet(plugin, ctx)))

            v_dot = View(ctx)
            v_dot_bg = GradientDrawable()
            v_dot_bg.setShape(GradientDrawable.OVAL)
            v_dot_bg.setColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            v_dot.setBackground(v_dot_bg)
            v_dot_lp = LinearLayout.LayoutParams(dp(6), dp(6))
            v_dot_lp.gravity = Gravity.CENTER_VERTICAL
            v_dot_lp.rightMargin = dp(4)
            ver_chip.addView(v_dot, v_dot_lp)

            v_txt = TextView(ctx)
            v_txt.setText("v2.0 Beta" if is_beta else "v2.0")
            v_txt.setTextSize(1, 10.5)
            v_txt.setTextColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            try:
                v_txt.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            ver_chip.addView(v_txt)

            v_lp = LinearLayout.LayoutParams(-2, -2)
            v_lp.leftMargin = dp(8)
            title_row.addView(ver_chip, v_lp)
            info_col.addView(title_row, LinearLayout.LayoutParams(-1, -2))

            subtitle = TextView(ctx)
            subtitle.setText(_t(plugin, "Автономный мониторинг активности контактов", "Autonomous contact activity monitoring"))
            subtitle.setTextSize(1, 12.0)
            subtitle.setTextColor(c(0xFF9AA4B2))
            sub_lp = LinearLayout.LayoutParams(-1, -2)
            sub_lp.topMargin = dp(2)
            info_col.addView(subtitle, sub_lp)

            chips_container = LinearLayout(ctx)
            chips_container.setOrientation(LinearLayout.HORIZONTAL)
            chips_container.setGravity(Gravity.CENTER_VERTICAL)
            c_row_lp = LinearLayout.LayoutParams(-1, -2)
            c_row_lp.topMargin = dp(8)

            chip_color = 0x1AFFFFFF if dark else 0x0C000000
            chip_tint = 0xFF9AA4B2 if dark else 0xFF334155

            chan_chip = LinearLayout(ctx)
            chan_chip.setOrientation(LinearLayout.HORIZONTAL)
            chan_chip.setGravity(Gravity.CENTER_VERTICAL)
            ch_bg = GradientDrawable()
            ch_bg.setColor(c(chip_color))
            ch_bg.setCornerRadius(float(dp(12)))
            chan_chip.setBackground(ch_bg)
            chan_chip.setPadding(dp(8), dp(4), dp(8), dp(4))
            chan_chip.setClickable(True)
            chan_chip.setFocusable(True)
            if OnClickListener:
                chan_chip.setOnClickListener(OnClickListener(lambda *a: open_link("neo_plugin")))
            chan_icon = ImageView(ctx)
            chan_id = get_telegram_drawable_id(ctx, "msg_channel", "msg_send")
            if chan_id != 0:
                try:
                    chan_icon.setImageResource(chan_id)
                    chan_icon.setColorFilter(c(chip_tint))
                except Exception:
                    pass
            chan_chip.addView(chan_icon, LinearLayout.LayoutParams(dp(14), dp(14)))
            chan_tv = TextView(ctx)
            chan_tv.setText("@neo_plugin")
            chan_tv.setTextSize(1, 11.5)
            chan_tv.setTextColor(c(chip_tint))
            chan_tv.setSingleLine(True)
            chan_tv.setPadding(dp(5), 0, 0, 0)
            chan_chip.addView(chan_tv)
            chips_container.addView(chan_chip, LinearLayout.LayoutParams(-2, -2))

            info_btn = LinearLayout(ctx)
            info_btn.setOrientation(LinearLayout.HORIZONTAL)
            info_btn.setGravity(Gravity.CENTER_VERTICAL)
            ib_bg = GradientDrawable()
            ib_bg.setColor(c(chip_color))
            ib_bg.setCornerRadius(float(dp(12)))
            info_btn.setBackground(ib_bg)
            info_btn.setPadding(dp(8), dp(4), dp(8), dp(4))
            info_btn.setClickable(True)
            info_btn.setFocusable(True)
            if OnClickListener:
                info_btn.setOnClickListener(OnClickListener(lambda *a: OmniWelcomeUI.show_about_sheet(plugin, ctx)))
            info_ic = ImageView(ctx)
            info_ic_id = get_telegram_drawable_id(ctx, "msg_info", "menu_about")
            if info_ic_id != 0:
                try:
                    info_ic.setImageResource(info_ic_id)
                    info_ic.setColorFilter(c(chip_tint))
                except Exception:
                    pass
            info_btn.addView(info_ic, LinearLayout.LayoutParams(dp(14), dp(14)))
            info_tv = TextView(ctx)
            info_tv.setText(_t(plugin, "О плагине", "About Plugin"))
            info_tv.setTextSize(1, 11.5)
            info_tv.setTextColor(c(chip_tint))
            info_tv.setSingleLine(True)
            info_tv.setPadding(dp(4), 0, 0, 0)
            info_btn.addView(info_tv)
            ib_lp = LinearLayout.LayoutParams(-2, -2)
            ib_lp.leftMargin = dp(6)
            chips_container.addView(info_btn, ib_lp)

            info_col.addView(chips_container, c_row_lp)
            profile_card.addView(info_col, info_lp)

            p_lp = LinearLayout.LayoutParams(-1, -2)
            p_lp.setMargins(dp(14), 0, dp(14), dp(6))
            root.addView(profile_card, p_lp)

            outer = FrameLayout(ctx)
            outer.setPadding(dp(10), dp(16), dp(10), dp(10))

            card = LinearLayout(ctx)
            card.setOrientation(LinearLayout.VERTICAL)
            card.setGravity(Gravity.CENTER_HORIZONTAL)
            card.setPadding(dp(14), dp(26), dp(14), dp(22))

            card_bg = 0xFFF7F8FA if dark else 0xFF111820
            primary_text = 0xFF141B24 if dark else 0xFFFFFFFF
            secondary_text = 0xCC141B24 if dark else 0xCCFFFFFF
            btn_bg_color = 0xFF111820 if dark else 0xFFFFFFFF
            btn_text_color = 0xFFFFFFFF if dark else 0xFF111820

            card_shape = GradientDrawable()
            card_shape.setShape(GradientDrawable.RECTANGLE)
            card_shape.setCornerRadius(float(dp(24)))
            card_shape.setColor(c(card_bg))
            card.setBackground(card_shape)

            card_title = TextView(ctx)
            card_title.setText(_t(plugin, "Мониторинг активности контактов", "Contact Activity Monitoring"))
            card_title.setTextSize(1, 23.0)
            card_title.setTextColor(c(primary_text))
            card_title.setGravity(Gravity.CENTER)
            try:
                card_title.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            ct_lp = LinearLayout.LayoutParams(-1, -2)
            ct_lp.setMargins(dp(4), 0, dp(4), 0)
            card.addView(card_title, ct_lp)

            card_body = TextView(ctx)
            desc_str = _t(
                plugin,
                "Omniscient Reborn фиксирует сессии онлайна, прочтения сообщений и набор текста "
                "в реальном времени с автоматическим построением 24ч инфографики.\n\n"
                "Все данные и история сохраняются локально на вашем устройстве в зашифрованном виде.",
                "Omniscient Reborn tracks online sessions, message reads, and typing events "
                "in real time with automatic 24h infographic generation.\n\n"
                "All data and history are stored locally on your device in encrypted form."
            )
            card_body.setText(desc_str)
            card_body.setTextSize(1, 14.0)
            card_body.setTextColor(c(secondary_text))
            card_body.setGravity(Gravity.CENTER)
            card_body.setLineSpacing(float(dp(2)), 1.15)
            cb_lp = LinearLayout.LayoutParams(-1, -2)
            cb_lp.setMargins(dp(4), dp(16), dp(4), 0)
            card.addView(card_body, cb_lp)

            pills_row = LinearLayout(ctx)
            pills_row.setOrientation(LinearLayout.HORIZONTAL)
            pills_row.setGravity(Gravity.CENTER)
            pills_lp = LinearLayout.LayoutParams(-1, -2)
            pills_lp.setMargins(0, dp(18), 0, 0)

            features = [
                _t(plugin, "Сессии\u00A024ч", "24h\u00A0Sessions"),
                _t(plugin, "100%\u00A0Локально", "100%\u00A0Local"),
                _t(plugin, "Шифрование", "Encrypted")
            ]

            for label_str in features:
                fpill = LinearLayout(ctx)
                fpill.setOrientation(LinearLayout.HORIZONTAL)
                fpill.setGravity(Gravity.CENTER)
                fp_bg = GradientDrawable()
                fp_bg.setCornerRadius(float(dp(11)))
                fp_bg.setColor(c(0x0C000000 if dark else 0x18FFFFFF))
                fpill.setBackground(fp_bg)
                fpill.setPadding(dp(4), 0, dp(4), 0)

                ft_tv = TextView(ctx)
                ft_tv.setText(label_str)
                ft_tv.setTextSize(1, 10.2)
                ft_tv.setSingleLine(True)
                ft_tv.setMaxLines(1)
                ft_tv.setGravity(Gravity.CENTER)
                ft_tv.setTextColor(c(primary_text))
                try:
                    ft_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                fpill.addView(ft_tv, LinearLayout.LayoutParams(-1, -2))

                fp_lp = LinearLayout.LayoutParams(0, dp(34), 1.0)
                fp_lp.setMargins(dp(2.5), 0, dp(2.5), 0)
                pills_row.addView(fpill, fp_lp)

            card.addView(pills_row, pills_lp)

            loader_btn = LinearLayout(ctx)
            loader_btn.setOrientation(LinearLayout.HORIZONTAL)
            loader_btn.setGravity(Gravity.CENTER)
            loader_btn.setPadding(dp(16), 0, dp(16), 0)
            loader_shape = GradientDrawable()
            loader_shape.setShape(GradientDrawable.RECTANGLE)
            loader_shape.setCornerRadius(float(dp(28)))
            loader_shape.setColor(c(0x2200E5FF if dark else 0x180284C7))
            loader_shape.setStroke(dp(1.5), c(0xFF00E5FF if dark else 0xFF0284C7))
            loader_btn.setBackground(loader_shape)
            loader_btn.setClickable(True)
            loader_btn.setFocusable(True)
            if OnClickListener:
                loader_btn.setOnClickListener(OnClickListener(lambda *a: OmniWelcomeUI.open_github_loader(plugin, ctx)))

            b_icon = ImageView(ctx)
            b_ic_id = get_telegram_drawable_id(ctx, "menu_download_round", "msg_download", "msg_retry")
            if b_ic_id != 0:
                try:
                    b_icon.setImageResource(b_ic_id)
                    b_icon.setColorFilter(c(0xFF00E5FF if dark else 0xFF0284C7))
                except Exception:
                    pass
            loader_btn.addView(b_icon, LinearLayout.LayoutParams(dp(20), dp(20)))

            b_label = TextView(ctx)
            b_label.setText(_t(plugin, "Загрузчик версий", "Version Loader"))
            b_label.setTextSize(1, 14.5)
            b_label.setTextColor(c(0xFF00E5FF if dark else 0xFF0284C7))
            try:
                b_label.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            blabel_lp = LinearLayout.LayoutParams(-2, -2)
            blabel_lp.leftMargin = dp(10)
            loader_btn.addView(b_label, blabel_lp)

            loader_lp = LinearLayout.LayoutParams(-1, dp(48))
            loader_lp.setMargins(dp(10), dp(18), dp(10), 0)
            card.addView(loader_btn, loader_lp)

            button = LinearLayout(ctx)
            button.setOrientation(LinearLayout.HORIZONTAL)
            button.setGravity(Gravity.CENTER)
            button.setPadding(dp(18), 0, dp(18), 0)
            b_shape = GradientDrawable()
            b_shape.setShape(GradientDrawable.RECTANGLE)
            b_shape.setCornerRadius(float(dp(28)))
            b_shape.setColor(c(btn_bg_color))
            button.setBackground(b_shape)
            button.setClickable(True)
            button.setFocusable(True)
            if on_continue_click and OnClickListener:
                button.setOnClickListener(OnClickListener(lambda *a: on_continue_click()))

            button_icon = ImageView(ctx)
            btn_ic_id = get_telegram_drawable_id(ctx, "msg_check", "menu_download_round", "msg_download")
            if btn_ic_id != 0:
                try:
                    button_icon.setImageResource(btn_ic_id)
                    button_icon.setColorFilter(c(btn_text_color))
                except Exception:
                    pass
            button.addView(button_icon, LinearLayout.LayoutParams(dp(22), dp(22)))

            button_label = TextView(ctx)
            button_label.setText(_t(plugin, "Принять и продолжить", "Accept and Continue"))
            button_label.setTextSize(1, 16.5)
            button_label.setTextColor(c(btn_text_color))
            try:
                button_label.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            blp = LinearLayout.LayoutParams(-2, -2)
            blp.leftMargin = dp(12)
            button.addView(button_label, blp)

            button_lp = LinearLayout.LayoutParams(-1, dp(56))
            button_lp.setMargins(dp(10), dp(14), dp(10), 0)
            card.addView(button, button_lp)

            safe = LinearLayout(ctx)
            safe.setOrientation(LinearLayout.HORIZONTAL)
            safe.setGravity(Gravity.CENTER)
            safe_icon = ImageView(ctx)
            safe_ic_id = get_telegram_drawable_id(ctx, "verified_profile", "msg_secret", "shield")
            if safe_ic_id != 0:
                try:
                    safe_icon.setImageResource(safe_ic_id)
                    safe_icon.setColorFilter(c(0xFF00C853 if dark else 0xFF22C55E))
                except Exception:
                    pass
            safe.addView(safe_icon, LinearLayout.LayoutParams(dp(18), dp(18)))

            safe_text = TextView(ctx)
            safe_text.setText(_t(plugin, "Безопасно • Без отправки на серверы", "Secure • No external server uploads"))
            safe_text.setTextSize(1, 13.0)
            safe_text.setTextColor(c(secondary_text))
            slp = LinearLayout.LayoutParams(-2, -2)
            slp.leftMargin = dp(8)
            safe.addView(safe_text, slp)

            safe_lp = LinearLayout.LayoutParams(-1, -2)
            safe_lp.setMargins(0, dp(18), 0, 0)
            card.addView(safe, safe_lp)

            outer.addView(card, FrameLayout.LayoutParams(-1, -2, Gravity.CENTER))
            root.addView(outer, LinearLayout.LayoutParams(-1, -2))

            footer = LinearLayout(ctx)
            footer.setOrientation(LinearLayout.VERTICAL)
            footer.setGravity(Gravity.CENTER_HORIZONTAL)
            footer.setPadding(0, dp(12), 0, dp(12))

            row1 = LinearLayout(ctx)
            row1.setOrientation(LinearLayout.HORIZONTAL)
            row1.setGravity(Gravity.CENTER)

            t1 = TextView(ctx)
            t1.setText("Designed by ")
            t1.setTextSize(1, 13.0)
            t1.setTextColor(c(0xFF9AA4B2))
            row1.addView(t1)

            t2 = TextView(ctx)
            t2.setText("@mrneoner & @neo_plugin")
            t2.setTextSize(1, 13.0)
            t2.setTextColor(c(0xFFFFFFFF if dark else 0xFF1D1F24))
            try:
                t2.setTypeface(Typeface.DEFAULT_BOLD)
            except Exception:
                pass
            row1.addView(t2)
            footer.addView(row1, LinearLayout.LayoutParams(-2, -2))

            v_text = TextView(ctx)
            v_text.setText(f"Omniscient Reborn v{getattr(plugin, 'version', '2.0.0')}")
            v_text.setTextSize(1, 11.0)
            v_text.setTextColor(c(0xFF9AA4B2))
            vlp = LinearLayout.LayoutParams(-2, -2)
            vlp.topMargin = dp(4)
            footer.addView(v_text, vlp)

            chip = TextView(ctx)
            chip.setText("Powered by ElyxCore")
            chip.setTextSize(1, 10.0)
            chip.setPadding(dp(8), dp(2), dp(8), dp(2))
            chip.setTextColor(c(0xFF9AA4B2))
            c_bg = GradientDrawable()
            c_bg.setColor(c(0x0FFFFFFF if dark else 0x0F000000))
            c_bg.setCornerRadius(float(dp(12)))
            chip.setBackground(c_bg)
            clp = LinearLayout.LayoutParams(-2, -2)
            clp.topMargin = dp(12)
            footer.addView(chip, clp)

            root.addView(footer, LinearLayout.LayoutParams(-1, -2))

            return root
        except Exception as e:
            log(f"[Omniscient Reborn] Error creating welcome view: {e}")
            return None
