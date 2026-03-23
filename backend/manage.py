#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import re
import sys
from pathlib import Path

# Read DJANGO_SETTINGS_MODULE from .env before setdefault, without requiring
# the dotenv package to be installed at this point.
# Production .env sets: DJANGO_SETTINGS_MODULE=config.settings.production
_env_file = Path(__file__).resolve().parent.parent / '.env'
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _m = re.match(r'^DJANGO_SETTINGS_MODULE\s*=\s*(\S+)', _line)
            if _m:
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', _m.group(1))
                break


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
