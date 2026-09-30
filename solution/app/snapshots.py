import json
from pathlib import Path

from pydantic import ValidationError

from app.errors import AppError
from app.schemas import Dataset


def load_snapshot(path: Path) -> Dataset:
    try:
        dataset = Dataset.model_validate_json(path.read_text(encoding="utf-8"))
        if dataset.metadata.row_count != len(dataset.rows):
            raise ValueError("건수 불일치")
        return dataset
    except (OSError, ValueError, ValidationError):
        raise AppError(
            "snapshot_invalid",
            "저장 데이터가 없거나 손상되었습니다. 저장본 갱신 명령을 실행해 주세요.",
        ) from None


def save_snapshot(dataset: Dataset, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(dataset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
