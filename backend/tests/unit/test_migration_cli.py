import os
import subprocess
import sys
from pathlib import Path


def test_alembic_offline_upgrade_runs_from_repository_root():
    repository_root = Path(__file__).resolve().parents[3]
    config_path = repository_root / "backend" / "alembic.ini"
    env = os.environ.copy()
    database_url = "postgresql+psycopg://unused:unused@localhost/unused"
    env.update(DATABASE_URL=database_url, DATABASE_URL_DIRECT=database_url)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(config_path),
            "upgrade",
            "head",
            "--sql",
        ],
        cwd=repository_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "CREATE EXTENSION IF NOT EXISTS vector" in result.stdout
    assert "0004_notes_tags_shares" in result.stdout
