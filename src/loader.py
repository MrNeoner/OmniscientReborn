import os
import sys
import json
import threading
import ssl
import urllib.request
import shutil
import zipfile

try:
    from file_utils import get_documents_dir
except Exception:
    def get_documents_dir():
        return "/sdcard/Download"

try:
    from android.view import Gravity, View
    from android.widget import FrameLayout, LinearLayout, TextView, ScrollView, ProgressBar
    from android.graphics.drawable import GradientDrawable
    from android.graphics import Typeface
    from org.telegram.messenger import AndroidUtilities, ApplicationLoader
    from org.telegram.ui.ActionBar import Theme, BottomSheet
    from ui.bulletin import BulletinHelper
    from ui.alert import AlertDialogBuilder
    from android_utils import OnClickListener, run_on_ui_thread, log
except Exception:
    Gravity = View = FrameLayout = LinearLayout = TextView = ScrollView = ProgressBar = None
    GradientDrawable = Typeface = AndroidUtilities = ApplicationLoader = Theme = BottomSheet = None
    BulletinHelper = AlertDialogBuilder = OnClickListener = run_on_ui_thread = None
    def log(m): print(m)
    def run_on_ui_thread(fn): fn()

DEFAULT_REPO = "MrNeoner/OmniscientReborn"

def _c(val):
    if isinstance(val, int):
        val = val & 0xFFFFFFFF
        if val > 0x7FFFFFFF:
            return val - 0x100000000
        return val
    return 0

def is_newer_version(latest_tag: str, current_version: str) -> bool:
    def parse_ver(v_str):
        v = str(v_str).strip().lstrip("v").split("-")[0]
        parts = []
        for x in v.split("."):
            try:
                parts.append(int(x))
            except ValueError:
                parts.append(0)
        return parts
    try:
        latest_parts = parse_ver(latest_tag)
        current_parts = parse_ver(current_version)
        while len(latest_parts) < len(current_parts):
            latest_parts.append(0)
        while len(current_parts) < len(latest_parts):
            current_parts.append(0)
        return latest_parts > current_parts
    except Exception:
        return False

class OmniGitHubLoader:
    @staticmethod
    def get_repo(plugin=None) -> str:
        return DEFAULT_REPO

    @staticmethod
    def set_repo(plugin, repo: str):
        pass

    @staticmethod
    def fetch_releases(repo: str):
        repo_clean = str(repo).strip().replace("https://github.com/", "").strip("/")
        if not repo_clean:
            repo_clean = DEFAULT_REPO

        url = f"https://api.github.com/repos/{repo_clean}/releases"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "OmniscientReborn-Loader/2.0",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        releases = []
        for item in data:
            if not isinstance(item, dict):
                continue
            tag = item.get("tag_name", "")
            title = item.get("name") or tag
            body = item.get("body", "")
            date = item.get("published_at", "")[:10]
            prerelease = bool(item.get("prerelease", False))

            eaf_assets = []
            for asset in item.get("assets", []):
                aname = asset.get("name", "")
                if aname.endswith(".eaf") or aname.endswith(".zip"):
                    eaf_assets.append({
                        "name": aname,
                        "size": asset.get("size", 0),
                        "download_url": asset.get("browser_download_url", "")
                    })

            releases.append({
                "tag": tag,
                "title": title,
                "body": body,
                "date": date,
                "prerelease": prerelease,
                "assets": eaf_assets
            })

        return releases

    @staticmethod
    def download_asset(url: str, dest_path: str, on_progress=None, on_done=None, on_error=None):
        def _worker():
            try:
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "OmniscientReborn-Loader/2.0"}
                )

                with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as response:
                    total_size = int(response.headers.get("Content-Length", 0))
                    downloaded = 0
                    block_size = 16384
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    with open(dest_path, "wb") as f:
                        while True:
                            chunk = response.read(block_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0 and on_progress:
                                pct = int((downloaded / total_size) * 100)
                                if run_on_ui_thread:
                                    run_on_ui_thread(lambda p=pct: on_progress(p))

                if on_done and run_on_ui_thread:
                    run_on_ui_thread(lambda: on_done(dest_path))
            except Exception as e:
                log(f"[OmniGitHubLoader] Download error: {e}")
                if on_error and run_on_ui_thread:
                    run_on_ui_thread(lambda err=e: on_error(err))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    @staticmethod
    def restart_app():
        try:
            if ApplicationLoader is not None:
                ctx = ApplicationLoader.applicationContext
                if ctx is not None:
                    mgr = ctx.getPackageManager()
                    intent = mgr.getLaunchIntentForPackage(ctx.getPackageName())
                    if intent is not None:
                        from android.content import Intent
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK)
                        ctx.startActivity(intent)
            from java.lang import System
            System.exit(0)
        except Exception as e:
            log(f"[OmniGitHubLoader] restart_app error: {e}")
            try:
                import sys
                sys.exit(0)
            except Exception:
                pass

    @staticmethod
    def show_restart_dialog(ctx, tag=""):
        try:
            if ctx is None:
                return

            def on_restart(bld=None, which=0):
                if bld and hasattr(bld, "dismiss"):
                    try:
                        bld.dismiss()
                    except Exception:
                        pass
                OmniGitHubLoader.restart_app()

            def on_cancel(bld=None, which=0):
                if bld and hasattr(bld, "dismiss"):
                    try:
                        bld.dismiss()
                    except Exception:
                        pass

            title = "Обновление установлено!"
            msg = (
                f"Версия {tag} успешно заменена в файлах плагина!\n\n"
                "Чтобы изменения вступили в силу, необходимо перезапустить Telegram."
            )

            if AlertDialogBuilder is not None:
                builder = AlertDialogBuilder(ctx)
                if hasattr(builder, "set_title"):
                    builder.set_title(title)
                    builder.set_message(msg)
                    builder.set_positive_button("⚡ Перезапустить", on_restart)
                    builder.set_negative_button("Позже", on_cancel)
                elif hasattr(builder, "setTitle"):
                    builder.setTitle(title)
                    builder.setMessage(msg)
                    builder.setPositiveButton("⚡ Перезапустить", on_restart)
                    builder.setNegativeButton("Позже", on_cancel)
                builder.show()
        except Exception as e:
            log(f"[OmniGitHubLoader] show_restart_dialog error: {e}")

    @staticmethod
    def show_update_available_dialog(plugin, ctx, rel):
        try:
            if ctx is None:
                return

            tag = rel.get("tag", "")
            body = rel.get("body", "").strip()
            if len(body) > 280:
                body = body[:277] + "..."

            assets = rel.get("assets", [])
            target_asset = None
            for a in assets:
                if a.get("name", "").endswith(".eaf"):
                    target_asset = a
                    break
            if not target_asset and assets:
                target_asset = assets[0]

            def on_update_now(bld=None, which=0):
                if bld and hasattr(bld, "dismiss"):
                    try:
                        bld.dismiss()
                    except Exception:
                        pass

                if not target_asset:
                    OmniGitHubLoader.show_releases_dialog(plugin, ctx)
                    return

                cache_dir = ""
                try:
                    if ApplicationLoader is not None:
                        fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
                        cache_dir = os.path.join(fdir, "cache", "omniscient_loader")
                        os.makedirs(cache_dir, exist_ok=True)
                except Exception:
                    pass
                if not cache_dir:
                    cache_dir = get_documents_dir()

                fname = target_asset.get("name", "omniscient_reborn.eaf")
                temp_dest = os.path.join(cache_dir, fname)

                if BulletinHelper is not None:
                    try:
                        BulletinHelper.show_info(f"Загрузка обновления {tag}...")
                    except Exception:
                        pass

                def on_done(path):
                    def replace_worker():
                        ok = OmniGitHubLoader.replace_installed_plugin(path)
                        def on_ui():
                            if ok:
                                if BulletinHelper is not None:
                                    try:
                                        BulletinHelper.show_success(f"Версия {tag} установлена!")
                                    except Exception:
                                        pass
                                OmniGitHubLoader.show_restart_dialog(ctx, tag)
                            else:
                                if BulletinHelper is not None:
                                    try:
                                        BulletinHelper.show_error("Ошибка автозамены файлов.")
                                    except Exception:
                                        pass
                        if run_on_ui_thread:
                            run_on_ui_thread(on_ui)
                    t_repl = threading.Thread(target=replace_worker, daemon=True)
                    t_repl.start()

                def on_err(e):
                    if BulletinHelper is not None:
                        try:
                            BulletinHelper.show_error(f"Ошибка загрузки: {e}")
                        except Exception:
                            pass

                OmniGitHubLoader.download_asset(target_asset.get("download_url", ""), temp_dest, None, on_done, on_err)

            def on_details(bld=None, which=0):
                if bld and hasattr(bld, "dismiss"):
                    try:
                        bld.dismiss()
                    except Exception:
                        pass
                OmniGitHubLoader.show_releases_dialog(plugin, ctx)

            def on_later(bld=None, which=0):
                if bld and hasattr(bld, "dismiss"):
                    try:
                        bld.dismiss()
                    except Exception:
                        pass

            title = f"⚡ Доступно обновление {tag}"
            msg = f"Вышла новая версия Omniscient Reborn ({tag})!\n\n"
            if body:
                msg += f"Что нового:\n{body}\n\n"
            msg += "Установить обновление сейчас в один клик?"

            if AlertDialogBuilder is not None:
                b = AlertDialogBuilder(ctx)
                if hasattr(b, "set_title"):
                    b.set_title(title)
                    b.set_message(msg)
                    b.set_positive_button("⚡ Обновить сейчас", on_update_now)
                    b.set_neutral_button("Все релизы", on_details)
                    b.set_negative_button("Позже", on_later)
                elif hasattr(b, "setTitle"):
                    b.setTitle(title)
                    b.setMessage(msg)
                    b.setPositiveButton("⚡ Обновить сейчас", on_update_now)
                    b.setNeutralButton("Все релизы", on_details)
                    b.setNegativeButton("Позже", on_later)
                b.show()
        except Exception as e:
            log(f"[OmniGitHubLoader] show_update_available_dialog error: {e}")

    @staticmethod
    def check_for_updates(plugin, ctx=None, notify_if_latest=False):
        def _worker():
            try:
                releases = OmniGitHubLoader.fetch_releases(DEFAULT_REPO)
                if not releases:
                    if notify_if_latest and run_on_ui_thread:
                        run_on_ui_thread(lambda: BulletinHelper.show_info("Релизов не найдено") if BulletinHelper else None)
                    return

                latest = releases[0]
                latest_tag = latest.get("tag", "")
                curr_ver = getattr(plugin, "__version__", "2.0.0") if plugin else "2.0.0"

                if is_newer_version(latest_tag, curr_ver):
                    def _show_upd():
                        if BulletinHelper is not None:
                            try:
                                BulletinHelper.show_info(f"Доступно обновление Omniscient {latest_tag}!")
                            except Exception:
                                pass
                        if ctx is not None:
                            OmniGitHubLoader.show_update_available_dialog(plugin, ctx, latest)
                    if run_on_ui_thread:
                        run_on_ui_thread(_show_upd)
                else:
                    if notify_if_latest and run_on_ui_thread:
                        def _show_ok():
                            if BulletinHelper is not None:
                                try:
                                    BulletinHelper.show_success(f"Установлена актуальная версия ({curr_ver})")
                                except Exception:
                                    pass
                        run_on_ui_thread(_show_ok)
            except Exception as e:
                log(f"[OmniGitHubLoader] check_for_updates error: {e}")
                if notify_if_latest and run_on_ui_thread:
                    run_on_ui_thread(lambda: BulletinHelper.show_error(f"Ошибка проверки: {e}") if BulletinHelper else None)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    @staticmethod
    def replace_installed_plugin(downloaded_file: str) -> bool:
        if not downloaded_file or not os.path.exists(downloaded_file):
            log(f"[OmniGitHubLoader] replace: file does not exist: {downloaded_file}")
            return False

        if not zipfile.is_zipfile(downloaded_file):
            log(f"[OmniGitHubLoader] replace: not a valid zip: {downloaded_file}")
            return False

        target_dirs = set()
        target_eafs = set()

        try:
            f_val = globals().get("__file__")
            if f_val:
                curr = os.path.dirname(os.path.abspath(f_val))
                while curr and len(curr) > 3:
                    if os.path.exists(os.path.join(curr, "config.yml")) or (os.path.exists(os.path.join(curr, "main.py")) and os.path.exists(os.path.join(curr, "src"))):
                        target_dirs.add(curr)
                        parent = os.path.dirname(curr)
                        if os.path.exists(parent):
                            for fn in os.listdir(parent):
                                if fn.endswith(".eaf") and any(k in fn.lower() for k in ("omniscient", "reborn")):
                                    target_eafs.add(os.path.join(parent, fn))
                        break
                    curr = os.path.dirname(curr)
        except Exception as e:
            log(f"[OmniGitHubLoader] detect from __file__ error: {e}")

        fdir = ""
        try:
            if ApplicationLoader is not None:
                fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
                plugins_dir = os.path.join(fdir, "plugins")
                if os.path.exists(plugins_dir):
                    for root_dir, dirnames, filenames in os.walk(plugins_dir):
                        for fn in filenames:
                            if fn.endswith((".eaf", ".zip")) and any(k in fn.lower() for k in ("omniscient", "reborn")):
                                target_eafs.add(os.path.join(root_dir, fn))
                        for dn in dirnames:
                            if any(k in dn.lower() for k in ("omniscient", "reborn")):
                                cand_d = os.path.join(root_dir, dn)
                                if os.path.exists(os.path.join(cand_d, "main.py")) or os.path.exists(os.path.join(cand_d, "config.yml")):
                                    target_dirs.add(cand_d)
        except Exception as e:
            log(f"[OmniGitHubLoader] detect from ApplicationLoader error: {e}")

        if not target_eafs and fdir:
            for cand_eaf in [
                os.path.join(fdir, "plugins", "ElyxPlugins", "omniscient_reborn.eaf"),
                os.path.join(fdir, "plugins", "omniscient_reborn.eaf"),
                os.path.join(fdir, "plugins", "ElyxPlugins", "omniscient_reborn_beta.eaf"),
                os.path.join(fdir, "plugins", "omniscient_reborn_beta.eaf"),
            ]:
                if os.path.exists(os.path.dirname(cand_eaf)):
                    target_eafs.add(cand_eaf)

        if not target_dirs and fdir:
            for cand_dir in [
                os.path.join(fdir, "plugins", "ElyxPlugins", "omniscient_reborn"),
                os.path.join(fdir, "plugins", "omniscient_reborn"),
            ]:
                if os.path.exists(os.path.dirname(cand_dir)):
                    target_dirs.add(cand_dir)

        success = False

        for eaf_path in target_eafs:
            try:
                if os.path.abspath(downloaded_file) != os.path.abspath(eaf_path):
                    os.makedirs(os.path.dirname(eaf_path), exist_ok=True)
                    shutil.copyfile(downloaded_file, eaf_path)
                    log(f"[OmniGitHubLoader] Replaced .eaf at: {eaf_path}")
                    success = True
            except Exception as e:
                log(f"[OmniGitHubLoader] Failed to copy eaf to {eaf_path}: {e}")

        for t_dir in target_dirs:
            try:
                os.makedirs(t_dir, exist_ok=True)
                with zipfile.ZipFile(downloaded_file, 'r') as zf:
                    zf.extractall(t_dir)
                log(f"[OmniGitHubLoader] Extracted release into: {t_dir}")
                success = True

                for root_c, dirs_c, files_c in os.walk(t_dir):
                    for d_c in dirs_c:
                        if d_c == "__pycache__":
                            shutil.rmtree(os.path.join(root_c, d_c), ignore_errors=True)
                    for f_c in files_c:
                        if f_c.endswith(".pyc"):
                            try:
                                os.remove(os.path.join(root_c, f_c))
                            except Exception:
                                pass
            except Exception as e:
                log(f"[OmniGitHubLoader] Failed to extract to {t_dir}: {e}")

        if success:
            try:
                if os.path.exists(downloaded_file) and os.path.abspath(downloaded_file) not in [os.path.abspath(p) for p in target_eafs]:
                    os.remove(downloaded_file)
                    log(f"[OmniGitHubLoader] Cleaned up temporary download: {downloaded_file}")
            except Exception:
                pass

        return success

    @staticmethod
    def show_releases_dialog(plugin, ctx):
        if ctx is None or LinearLayout is None:
            return

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
        sheet_root.setPadding(dp(18), dp(14), dp(18), dp(18))
        sheet_bg_color = 0xFF141C2B if dark else 0xFFFFFFFF
        sheet_shape = GradientDrawable()
        sheet_shape.setColor(_c(sheet_bg_color))
        sheet_root.setBackground(sheet_shape)

        grabber = View(ctx)
        g_bg = GradientDrawable()
        g_bg.setColor(_c(0x35FFFFFF if dark else 0x20000000))
        g_bg.setCornerRadius(float(dp(3)))
        grabber.setBackground(g_bg)
        g_lp = LinearLayout.LayoutParams(dp(36), dp(4))
        g_lp.gravity = Gravity.CENTER_HORIZONTAL
        g_lp.bottomMargin = dp(12)
        sheet_root.addView(grabber, g_lp)

        title_tv = TextView(ctx)
        title_tv.setText("Загрузчик версий")
        title_tv.setTextSize(1, 19.0)
        title_tv.setTextColor(_c(0xFFFFFFFF if dark else 0xFF0F172A))
        try:
            title_tv.setTypeface(Typeface.DEFAULT_BOLD)
        except Exception:
            pass
        sheet_root.addView(title_tv, LinearLayout.LayoutParams(-1, -2))

        repo_name = OmniGitHubLoader.get_repo(plugin)
        sub_tv = TextView(ctx)
        sub_tv.setText(f"Репозиторий: {repo_name}")
        sub_tv.setTextSize(1, 12.5)
        sub_tv.setTextColor(_c(0xFF9AA4B2))
        sub_lp = LinearLayout.LayoutParams(-1, -2)
        sub_lp.topMargin = dp(4)
        sub_lp.bottomMargin = dp(10)
        sheet_root.addView(sub_tv, sub_lp)

        status_tv = TextView(ctx)
        status_tv.setText("Получение списка релизов...")
        status_tv.setTextSize(1, 13.0)
        status_tv.setTextColor(_c(0xFF00E5FF if dark else 0xFF0284C7))
        status_lp = LinearLayout.LayoutParams(-1, -2)
        status_lp.bottomMargin = dp(10)
        sheet_root.addView(status_tv, status_lp)

        scroll = ScrollView(ctx)
        releases_container = LinearLayout(ctx)
        releases_container.setOrientation(LinearLayout.VERTICAL)
        scroll.addView(releases_container, FrameLayout.LayoutParams(-1, -2))
        scroll_lp = LinearLayout.LayoutParams(-1, dp(320))
        sheet_root.addView(scroll, scroll_lp)

        close_btn = TextView(ctx)
        close_btn.setText("Закрыть")
        close_btn.setTextSize(1, 14.5)
        close_btn.setGravity(Gravity.CENTER)
        close_btn.setTextColor(_c(0xFFFFFFFF))
        try:
            close_btn.setTypeface(Typeface.DEFAULT_BOLD)
        except Exception:
            pass
        c_shape = GradientDrawable()
        c_shape.setCornerRadius(float(dp(12)))
        c_shape.setColor(_c(0xFF0284C7 if dark else 0xFF0F172A))
        close_btn.setBackground(c_shape)
        close_btn.setClickable(True)
        close_btn.setFocusable(True)
        if sheet is not None and OnClickListener:
            close_btn.setOnClickListener(OnClickListener(lambda *a: sheet.dismiss()))

        c_lp = LinearLayout.LayoutParams(-1, dp(44))
        c_lp.topMargin = dp(12)
        sheet_root.addView(close_btn, c_lp)

        def populate_releases(releases):
            releases_container.removeAllViews()
            if not releases:
                empty_tv = TextView(ctx)
                empty_tv.setText(
                    f"В репозитории '{repo_name}' пока нет опубликованных .eaf релизов.\n\n"
                    "💡 Как настроить обновления через GitHub:\n"
                    "1. Зайдите в ваш репозиторий на GitHub (например: mrneoner/OmniscientReborn)\n"
                    "2. Откройте вкладку 'Releases' -> 'Draft a new release'\n"
                    "3. Укажите версию (тег), например: v2.1.0\n"
                    "4. В поле Attach binaries прикрепите собранный файл .eaf\n"
                    "5. Нажмите 'Publish release'\n\n"
                    "После этого релиз мгновенно появится в этом загрузчике и будет доступен для скачивания в 1 клик!"
                )
                empty_tv.setTextSize(1, 13.0)
                empty_tv.setTextColor(_c(0xFF9AA4B2))
                empty_tv.setPadding(dp(8), dp(16), dp(8), dp(16))
                empty_tv.setLineSpacing(float(dp(2)), 1.15)
                releases_container.addView(empty_tv, LinearLayout.LayoutParams(-1, -2))
                status_tv.setText("Готово • Ожидание релизов на GitHub")
                return

            status_tv.setText(f"Найдено релизов: {len(releases)}")

            for rel in releases:
                card = LinearLayout(ctx)
                card.setOrientation(LinearLayout.VERTICAL)
                c_bg = GradientDrawable()
                c_bg.setColor(_c(0x221E293B if dark else 0x08000000))
                c_bg.setCornerRadius(float(dp(12)))
                c_bg.setStroke(dp(1), _c(0x2500E5FF if dark else 0x15000000))
                card.setBackground(c_bg)
                card.setPadding(dp(12), dp(10), dp(12), dp(10))

                h_row = LinearLayout(ctx)
                h_row.setOrientation(LinearLayout.HORIZONTAL)
                h_row.setGravity(Gravity.CENTER_VERTICAL)

                v_tv = TextView(ctx)
                v_tv.setText(rel["tag"])
                v_tv.setTextSize(1, 15.0)
                v_tv.setTextColor(_c(0xFFFFFFFF if dark else 0xFF0F172A))
                try:
                    v_tv.setTypeface(Typeface.DEFAULT_BOLD)
                except Exception:
                    pass
                h_row.addView(v_tv)

                if rel["prerelease"]:
                    pre_badge = TextView(ctx)
                    pre_badge.setText("Pre-release")
                    pre_badge.setTextSize(1, 10.0)
                    pre_badge.setTextColor(_c(0xFFFFB74D))
                    pre_lp = LinearLayout.LayoutParams(-2, -2)
                    pre_lp.leftMargin = dp(8)
                    h_row.addView(pre_badge, pre_lp)

                d_tv = TextView(ctx)
                d_tv.setText(rel["date"])
                d_tv.setTextSize(1, 11.5)
                d_tv.setTextColor(_c(0xFF64748B))
                d_tv.setGravity(Gravity.RIGHT)
                d_lp = LinearLayout.LayoutParams(0, -2, 1.0)
                h_row.addView(d_tv, d_lp)

                card.addView(h_row, LinearLayout.LayoutParams(-1, -2))

                if rel["body"]:
                    b_tv = TextView(ctx)
                    b_tv.setText(rel["body"][:200] + ("..." if len(rel["body"]) > 200 else ""))
                    b_tv.setTextSize(1, 12.0)
                    b_tv.setTextColor(_c(0xFF94A3B8))
                    b_lp = LinearLayout.LayoutParams(-1, -2)
                    b_lp.topMargin = dp(4)
                    b_lp.bottomMargin = dp(6)
                    card.addView(b_tv, b_lp)

                curr_ver = getattr(plugin, "__version__", "2.0.0") if plugin else "2.0.0"
                rel_tag = rel.get("tag", "")
                is_update = is_newer_version(rel_tag, curr_ver)

                for asset in rel["assets"]:
                    dl_btn = TextView(ctx)
                    size_kb = int(asset["size"] / 1024) if asset["size"] else 0
                    if is_update:
                        dl_btn.setText(f"⚡ Установить {asset['name']} ({size_kb} KB)")
                    else:
                        dl_btn.setText(f"Установлена последняя версия ({rel_tag})")
                    dl_btn.setTextSize(1, 12.0)
                    dl_btn.setGravity(Gravity.CENTER)
                    try:
                        dl_btn.setTypeface(Typeface.DEFAULT_BOLD)
                    except Exception:
                        pass

                    dl_bg = GradientDrawable()
                    dl_bg.setCornerRadius(float(dp(8)))
                    if is_update:
                        dl_btn.setTextColor(_c(0xFFFFFFFF))
                        dl_bg.setColor(_c(0xFF0284C7 if dark else 0xFF1D2733))
                    else:
                        dl_btn.setTextColor(_c(0xFF94A3B8 if dark else 0xFF64748B))
                        dl_bg.setColor(_c(0x1838BDF8 if dark else 0x12000000))
                        dl_bg.setStroke(dp(1), _c(0x3038BDF8 if dark else 0x18000000))
                    dl_btn.setBackground(dl_bg)
                    dl_btn.setClickable(True)
                    dl_btn.setFocusable(True)

                    def start_dl(btn=dl_btn, url=asset["download_url"], fname=asset["name"], r_tag=rel_tag, can_dl=is_update):
                        if not can_dl:
                            if BulletinHelper is not None:
                                try:
                                    BulletinHelper.show_info(f"У вас уже установлена последняя версия ({curr_ver})")
                                except Exception:
                                    pass
                            return

                        cache_dir = ""
                        try:
                            if ApplicationLoader is not None:
                                fdir = str(ApplicationLoader.getFilesDirFixed().getAbsolutePath())
                                cache_dir = os.path.join(fdir, "cache", "omniscient_loader")
                                os.makedirs(cache_dir, exist_ok=True)
                        except Exception:
                            pass
                        if not cache_dir:
                            cache_dir = get_documents_dir()

                        temp_dest = os.path.join(cache_dir, fname)
                        btn.setText("Скачивание...")
                        status_tv.setText(f"Скачивается {fname}...")

                        def on_prog(pct):
                            btn.setText(f"Скачивание {pct}%...")
                            status_tv.setText(f"Загрузка {fname}: {pct}%")

                        def on_done(path):
                            btn.setText("Установка...")
                            status_tv.setText("Замена текущей версии плагина...")

                            def replace_worker():
                                ok = OmniGitHubLoader.replace_installed_plugin(path)
                                def update_ui():
                                    if ok:
                                        btn.setText("Установлено! ⚡")
                                        status_tv.setText(f"Версия {r_tag} установлена! Требуется перезапуск.")
                                        if BulletinHelper:
                                            try:
                                                BulletinHelper.show_success(f"Версия {r_tag} успешно установлена!")
                                            except Exception:
                                                pass
                                        OmniGitHubLoader.show_restart_dialog(ctx, r_tag)
                                    else:
                                        btn.setText("Ошибка замены")
                                        status_tv.setText("Не удалось автоматически заменить файлы.")
                                        if BulletinHelper:
                                            try:
                                                BulletinHelper.show_error("Ошибка установки версии.")
                                            except Exception:
                                                pass
                                if run_on_ui_thread:
                                    run_on_ui_thread(update_ui)

                            t_repl = threading.Thread(target=replace_worker, daemon=True)
                            t_repl.start()

                        def on_err(e):
                            btn.setText("Ошибка скачивания")
                            status_tv.setText(f"Ошибка: {e}")
                            if BulletinHelper:
                                try:
                                    BulletinHelper.show_error(f"Ошибка: {e}")
                                except Exception:
                                    pass

                        OmniGitHubLoader.download_asset(url, temp_dest, on_prog, on_done, on_err)

                    if OnClickListener:
                        dl_btn.setOnClickListener(OnClickListener(lambda *a, s=start_dl: s()))

                    card.addView(dl_btn, LinearLayout.LayoutParams(-1, dp(36)))

                card_lp = LinearLayout.LayoutParams(-1, -2)
                card_lp.bottomMargin = dp(10)
                releases_container.addView(card, card_lp)

        def fetch_worker():
            try:
                rels = OmniGitHubLoader.fetch_releases(repo_name)
                if run_on_ui_thread:
                    run_on_ui_thread(lambda: populate_releases(rels))
            except Exception as e:
                err_msg = str(e)
                log(f"[OmniGitHubLoader] Fetch failed: {e}")
                if run_on_ui_thread:
                    def show_err():
                        status_tv.setText(f"Ошибка подключения к GitHub: {err_msg}")
                        err_tv = TextView(ctx)
                        err_tv.setText(
                            f"Не удалось получить релизы репозитория '{repo_name}'.\n\n"
                            "Проверьте правильность репозитория (например: mrneoner/OmniscientReborn) "
                            "и наличие интернета."
                        )
                        err_tv.setTextSize(1, 13.0)
                        err_tv.setTextColor(_c(0xFFFF5252))
                        err_tv.setPadding(dp(8), dp(16), dp(8), dp(16))
                        releases_container.removeAllViews()
                        releases_container.addView(err_tv, LinearLayout.LayoutParams(-1, -2))
                    run_on_ui_thread(show_err)

        t = threading.Thread(target=fetch_worker, daemon=True)
        t.start()

        if sheet is not None:
            sheet.setCustomView(sheet_root)
            sheet.show()
        elif AlertDialogBuilder:
            AlertDialogBuilder(ctx).setTitle("Загрузчик версий").setMessage(
                "Загрузчик версий запущен в фоновом режиме."
            ).setPositiveButton("OK", None).show()

OmniGitHubLoader.show_loader_sheet = OmniGitHubLoader.show_releases_dialog
