from pathlib import Path

from cuneus import Settings


class AppSettings(Settings):
    project_dir: Path = Path("..")
