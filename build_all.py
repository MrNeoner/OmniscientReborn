import os
import shutil
import subprocess

ROOT_DIR = r"d:\All I Need\Anti\OmniscientRebornV2"
ANTI_DIR = r"d:\All I Need\Anti"

def set_config(name: str, plugin_id: str, version: str, is_beta: bool):
    meta_content = f"""name: {name}
description: 'Расширенные уведомления о статусе, прочтении сообщений, наборе текста и изменении профиля для выбранных пользователей.'
id: {plugin_id}
version: {version}
author: '@mrneoner & @neo_plugin'
app_version: '>=12.0.0'
sdk_version: '>=1.4.0'
elyx_version: '>=0.9.0'
icon: sekaiware/1
compiled: false
"""
    for mpath in [
        os.path.join(ROOT_DIR, "meta.yml"),
        os.path.join(ROOT_DIR, "OmniscientReborn", "meta.yml")
    ]:
        with open(mpath, "w", encoding="utf-8") as f:
            f.write(meta_content)

    main_paths = [
        os.path.join(ROOT_DIR, "OmniscientReborn", "src", "main.py"),
        os.path.join(ROOT_DIR, "src", "main.py"),
        os.path.join(ROOT_DIR, "main.py")
    ]
    for mpath in main_paths:
        if not os.path.exists(mpath):
            continue
        with open(mpath, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        content = re.sub(r'__id__\s*=\s*"[^"]+"', f'__id__ = "{plugin_id}"', content)
        content = re.sub(r'__name__\s*=\s*"[^"]+"', f'__name__ = "{name}"', content)
        content = re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{version}"', content)
        content = re.sub(r'is_beta\s*=\s*(?:True|False)', f'is_beta = {is_beta}', content)

        with open(mpath, "w", encoding="utf-8") as f:
            f.write(content)

def build(target_name: str, out_filename_base: str):
    print(f"=== Building {target_name} ===")
    cmd = ["elyb", "build", "--ast", "-nf", "-v"]
    res = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(res.stdout)
    if res.returncode != 0:
        print("STDERR:", res.stderr)
        raise RuntimeError(f"Build failed with code {res.returncode}")

    src_eaf = os.path.join(ROOT_DIR, "builds", f"{target_name}.eaf")
    if not os.path.exists(src_eaf):
        # Fallback check
        for fn in os.listdir(os.path.join(ROOT_DIR, "builds")):
            if fn.endswith(".eaf") and target_name.split()[0] in fn:
                src_eaf = os.path.join(ROOT_DIR, "builds", fn)
                break

    dst1 = os.path.join(ANTI_DIR, f"{out_filename_base}.eaf")
    dst2 = os.path.join(ROOT_DIR, f"{out_filename_base}.eaf")
    shutil.copy2(src_eaf, dst1)
    shutil.copy2(src_eaf, dst2)
    print(f"-> Saved to {dst1} ({os.path.getsize(dst1)} bytes)")
    print(f"-> Saved to {dst2} ({os.path.getsize(dst2)} bytes)")

def main():
    set_config("Omniscient Reborn", "notifcont", "2.0.0-beta", True)
    build("Omniscient Reborn", "omniscient_reborn")
    print("\nBUILD COMPLETED: omniscient_reborn.eaf")

if __name__ == "__main__":
    main()
