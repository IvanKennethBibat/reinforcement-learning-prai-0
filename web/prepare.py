"""Gather what the browser build needs into web/app: ``python web/prepare.py``.

Then build it with ``uvx --python 3.12 pygbag --build web/app``. The output lands
in web/app/build/web, which is the folder to host. The editor and the sprite
baker are left out, since they only make sense on a desktop.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "web" / "app"
DESKTOP_ONLY = ("editor.py", "bake_sprites.py")

MAIN = '''# /// script
# dependencies = [
#   "pygame-ce",
#   "numpy",
# ]
# ///
import asyncio

from ui.__main__ import main

asyncio.run(main())
'''


def prepare(app=APP):
    shutil.rmtree(app, ignore_errors=True)
    app.mkdir(parents=True)
    skip = shutil.ignore_patterns("__pycache__", *DESKTOP_ONLY)
    shutil.copytree(ROOT / "ui", app / "ui", ignore=skip)
    shutil.copytree(ROOT / "battle", app / "battle", ignore=shutil.ignore_patterns("__pycache__", "env.py"))
    (app / "main.py").write_text(MAIN)
    return app


if __name__ == "__main__":
    print(f"Ready: {prepare()}")
