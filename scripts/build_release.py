"""Build via the pipeline scanner and the same Python as PyInstaller."""
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "store_package.json").read_text(encoding="utf-8"))
app_name = config["app_name"]
tools_root = Path(os.environ.get("SOFTWARE_TOOLS_ROOT",
    str(Path(os.environ.get("OneDrive", str(Path.home() / "OneDrive"))) / ".TOPICS" / ".SOFTWARE" / "_tools")))
scanner = tools_root / "build_exclude_scanner.py"
if not scanner.is_file():
    raise SystemExit("Missing required pipeline scanner: " + str(scanner))
result = subprocess.run([sys.executable, str(scanner), "--project", str(root), "--emit", "json"],
    check=True, capture_output=True, text=True, encoding="utf-8")
print(result.stderr, file=sys.stderr)
report = json.loads(result.stdout)
build_root = Path(os.environ.get("BUILD_ROOT", str(Path("C:/_Local_DEV/codex_build") / app_name.lower())))
build_root.mkdir(parents=True, exist_ok=True)
(build_root / "exclude-report.json").write_text(result.stdout, encoding="utf-8")
env = os.environ.copy()
env["PYINSTALLER_EXCLUDES"] = json.dumps(sorted(set(report["excludes"]) | {"pytest", "ruff", "PyInstaller"}))
subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm",
    "--workpath", str(build_root / "work"), "--distpath", str(root / "dist"),
    str(root / (app_name + ".spec"))], cwd=root, env=env, check=True)
