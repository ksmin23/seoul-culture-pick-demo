import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://data.seoul.go.kr/dataList/OA-15486/A/1/datasetView.do"


@dataclass(frozen=True)
class Settings:
    openai_key: str = field(default="", repr=False)
    seoul_key: str = field(default="", repr=False)
    model: str = "gpt-5.6-luna"
    snapshot_path: Path = ROOT / "data/snapshots/exhibitions.json"


def load_settings() -> Settings:
    # 로컬 파일을 매번 읽어 키를 추가한 후 서버 재시작 없이 재시도할 수 있다.
    values = {**dotenv_values(ROOT / ".env.local"), **os.environ}
    return Settings(
        openai_key=(values.get("OPENAI_API_KEY") or "").strip(),
        seoul_key=(values.get("SEOUL_API_KEY") or "").strip(),
        model=(values.get("OPENAI_MODEL") or "gpt-5.6-luna").strip(),
    )
