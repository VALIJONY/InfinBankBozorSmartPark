import os

os.system("ruff check . --exclude smartpark/apps.py --fix && ruff format")
