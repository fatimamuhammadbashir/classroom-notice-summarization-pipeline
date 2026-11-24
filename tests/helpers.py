"""Shared test helpers."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.pipeline import NoticePipeline
from src.service import NoticeService
from src.storage import ResultStore

DATA_DIR = PROJECT_ROOT / "data"
NOTICES_DIR = DATA_DIR / "notices"
FIXED_NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


def config() -> dict:
    return load_config(PROJECT_ROOT / "config.json")


def make_service(store_root: str | Path) -> NoticeService:
    active_config = config()
    return NoticeService(NoticePipeline(active_config), ResultStore(store_root), active_config)


def process_notice(service: NoticeService, name: str):
    return service.summarize_file(NOTICES_DIR / name)


def read_sample(name: str) -> str:
    return (NOTICES_DIR / name).read_text(encoding="utf-8")
