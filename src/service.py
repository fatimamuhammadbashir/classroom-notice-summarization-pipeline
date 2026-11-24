"""Application service combining pipeline, storage and failure logging."""

from __future__ import annotations

from pathlib import Path

from .config import PROJECT_ROOT, load_config
from .editing import apply_edits
from .pipeline import NoticePipeline
from .storage import ResultStore


class NoticeService:
    def __init__(
        self,
        pipeline: NoticePipeline,
        store: ResultStore,
        config: dict,
    ) -> None:
        self.pipeline = pipeline
        self.store = store
        self.config = config

    def summarize_file(
        self,
        path: str | Path,
        *,
        output_path: str | Path | None = None,
        max_sentences: int | None = None,
        max_words: int | None = None,
    ) -> tuple[dict, Path, Path]:
        result = self.pipeline.process_file(
            path,
            max_sentences=max_sentences,
            max_words=max_words,
        )
        json_path = self.store.save_result(result, output_path)
        markdown_path = self.store.save_markdown(
            result,
            Path(json_path).with_suffix(".md"),
        )
        if result["quality_status"] != "pass":
            self.store.append_failure(result, event="generated")
        return result, json_path, markdown_path

    def summarize_text(
        self,
        text: str,
        *,
        source: str = "pasted-text",
        output_path: str | Path | None = None,
        max_sentences: int | None = None,
        max_words: int | None = None,
    ) -> tuple[dict, Path, Path]:
        result = self.pipeline.process_text(
            text,
            source=source,
            max_sentences=max_sentences,
            max_words=max_words,
        )
        json_path = self.store.save_result(result, output_path)
        markdown_path = self.store.save_markdown(
            result,
            Path(json_path).with_suffix(".md"),
        )
        if result["quality_status"] != "pass":
            self.store.append_failure(result, event="generated")
        return result, json_path, markdown_path

    def edit_result(
        self,
        result_path: str | Path,
        edits: dict,
        *,
        actor: str = "Teacher",
        max_words: int | None = None,
    ) -> tuple[dict, Path, Path]:
        result = self.store.load_result(result_path)
        word_limit = max_words or self.config["summarization"]["max_words"]
        updated = apply_edits(
            result,
            edits,
            actor=actor,
            max_words=word_limit,
        )
        json_path = self.store.save_result(updated, result_path)
        markdown_path = self.store.save_markdown(
            updated,
            Path(json_path).with_suffix(".md"),
        )
        if updated["quality_status"] != "pass":
            self.store.append_failure(
                updated,
                event="edited",
                actor=updated.get("edits", [{}])[-1].get("actor") if updated.get("edits") else None,
            )
        return updated, json_path, markdown_path

    def failures(self, limit: int = 20) -> list[dict]:
        return self.store.read_failures(limit=limit)


def build_service(
    *,
    store_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> NoticeService:
    config = load_config(config_path or PROJECT_ROOT / "config.json")
    pipeline = NoticePipeline(config)
    store = ResultStore(store_root or PROJECT_ROOT / "var")
    return NoticeService(pipeline, store, config)
