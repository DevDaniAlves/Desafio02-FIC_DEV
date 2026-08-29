from pathlib import Path
from sqlalchemy.engine.url import make_url
from src.database import resolve_db_url


def test_sqlite_url_is_absolute_and_posix(tmp_path):
    url = resolve_db_url(tmp_path, "sqlite:///database/atendimentos.db")
    parsed = make_url(url)
    path = Path(parsed.database)

    assert parsed.get_backend_name() == "sqlite"
    assert "\\" not in url
    assert path.is_absolute()
    assert path.as_posix() == parsed.database
    assert path.parent.exists()


def test_memory_and_non_sqlite_urls_are_unchanged():
    root = Path(".")
    assert resolve_db_url(root, "sqlite:///:memory:") == "sqlite:///:memory:"
    assert resolve_db_url(root, "postgresql://localhost/app") == "postgresql://localhost/app"
