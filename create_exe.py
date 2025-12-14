import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_exe() -> None:
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    dist_dir = project_root / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    # Common data to include (templates, static, config)
    datas = [
        (project_root / "templates", "templates"),
        (project_root / "static", "static"),
        (project_root / "staticfiles", "staticfiles"),
        (project_root / "config", "config"),
        (project_root / "smartpark", "smartpark"),
        (project_root / ".env", "."),
    ]

    # Build --add-data args
    add_data_args = []
    for src, tgt in datas:
        if Path(src).exists():
            add_data_args += ["--add-data", f"{src}{os.pathsep}{tgt}"]

    # Hidden imports often needed for Django, Channels, async libs
    hidden_imports = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "asgiref",
        "channels",
        "channels.layers",
        "channels.auth",
        "channels.generic.websocket",
        "channels_redis.core",
        "daphne.server",
        "psycopg2",
        "jinja2",  # occasionally required by Django templates backend
        # pywin32 printing stack
        "win32print",
        "win32api",
        "win32timezone",
        "pywintypes",
        "pythoncom",
        # openpyxl for Excel export
        "openpyxl",
        "openpyxl.workbook",
        "openpyxl.styles",
        "openpyxl.utils",
        "openpyxl.writer.excel",
        "openpyxl.reader.excel",
        # Additional Django modules
        "django.templatetags.static",
        "django.core.serializers.json",
        "django.db.backends.sqlite3",
        "sqlite3",
        # JSON and other utilities
        "json",
        "datetime",
        "io",
    ]
    hidden_args = []
    for imp in hidden_imports:
        hidden_args += ["--hidden-import", imp]

    # Entry point: run.py starts the server
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        "smartpark",
        "--collect-all",
        "channels",
        "--collect-all",
        "channels_redis",
        # ensure pywin32 binaries and submodules are bundled
        "--collect-all",
        "pywin32",
        "--collect-submodules",
        "pywin32",
        "--collect-binaries",
        "pywin32",
        # collect openpyxl data
        "--collect-all",
        "openpyxl",
        *add_data_args,
        *hidden_args,
        "run.py",
    ]

    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)

    # Move artifact to build/smartpark
    exe = project_root / "dist" / ("smartpark.exe" if os.name == "nt" else "smartpark")
    if exe.exists():
        print("Built:", exe)
    else:
        print("Executable not found in dist/")


if __name__ == "__main__":
    build_exe()
