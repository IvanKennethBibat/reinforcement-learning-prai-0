import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("prepare", ROOT / "web" / "prepare.py")
prepare_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_module)

RUN_ONE_FRAME_LOOP = """
import asyncio, os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame
import ui.__main__ as game

async def run():
    task = asyncio.create_task(game.main())
    await asyncio.sleep(0.3)
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    await task

asyncio.run(run())
loaded = {name.split(".")[0] for name in sys.modules}
print("HEAVY", sorted(loaded & {"gymnasium", "matplotlib", "agents"}))
"""


def test_web_build_leaves_out_desktop_tools_and_runs_on_its_own(tmp_path):
    app = prepare_module.prepare(tmp_path / "app")
    assert (app / "main.py").exists() and (app / "ui" / "assets" / "level.txt").exists()
    assert not (app / "ui" / "editor.py").exists()
    assert not (app / "ui" / "bake_sprites.py").exists()
    assert not (app / "battle" / "env.py").exists()

    result = subprocess.run([sys.executable, "-c", RUN_ONE_FRAME_LOOP], cwd=app, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "HEAVY []" in result.stdout


def test_game_code_parses_on_the_python_the_browser_runs():
    for folder in ("ui", "battle"):
        for path in (ROOT / folder).glob("*.py"):
            ast.parse(path.read_text(), feature_version=(3, 11))
