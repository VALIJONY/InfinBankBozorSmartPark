import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def main() -> None:
    # Handle both development and PyInstaller frozen environments
    if getattr(sys, "frozen", False):
        # PyInstaller frozen exe
        project_root = Path(os.getcwd())
        # Add the exe directory to Python path for imports
        exe_dir = Path(sys.executable).parent
        if str(exe_dir) not in sys.path:
            sys.path.insert(0, str(exe_dir))
    else:
        # Development environment
        project_root = Path(__file__).resolve().parent

    os.chdir(project_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    port = os.getenv("PORT", "8000")
    host = os.getenv("HOST", "0.0.0.0")

    # Open browser shortly after the server starts
    def open_browser() -> None:
        time.sleep(1.5)
        try:
            # Always open local browser on loopback
            webbrowser.open(f"http://127.0.0.1:{port}/home/")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    from django.core.management import execute_from_command_line

    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        # Disable Django autoreload under PyInstaller onefile to avoid argv issues
        argv = ["manage.py", "runserver", "--noreload", f"{host}:{port}"]
        # Ensure sys.argv has at least one element
        if not sys.argv:
            sys.argv = ["smartpark"]
    else:
        argv = ["manage.py", "runserver", f"{host}:{port}"]

    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
