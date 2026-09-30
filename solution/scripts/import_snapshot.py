"""서울열린데이터광장 JSON 내려받기 파일을 데모 저장본으로 변환한다."""
import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import load_settings
from app.schemas import Dataset, DatasetMeta
from app.search import normalize
from app.snapshots import save_snapshot

KST = ZoneInfo("Asia/Seoul")
SOURCE = "https://data.seoul.go.kr/dataList/OA-15486/S/1/datasetView.do"


def build_snapshot(payload: dict, reference: date, limit: int = 1000) -> Dataset:
    if limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")
    rows = []
    total = 0
    for raw in payload["DATA"]:
        row = {key.upper(): value for key, value in raw.items()}
        if row.get("CODENAME") != "전시/미술":
            continue
        total += 1
        for key in ("STRTDATE", "END_DATE"):
            value = row[key]
            if isinstance(value, (int, float)) or str(value).isdigit():
                row[key] = datetime.fromtimestamp(int(value) / 1000, KST).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        # 날짜 역전·빈 제목 등은 추천 대상에서 제외한다.
        try:
            normalize(row)
        except (ValueError, TypeError):
            continue
        rows.append(row)
    rows.sort(key=lambda r: (r.get("RGSTDATE", ""), r["STRTDATE"], r["TITLE"]), reverse=True)
    selected, seen = [], set()
    for row in rows:
        identity = normalize(row).id
        if identity not in seen:
            seen.add(identity)
            selected.append(row)
        if len(selected) == limit:
            break
    if not selected:
        raise ValueError("전시 데이터가 없습니다.")
    return Dataset(
        metadata=DatasetMeta(
            source_url=SOURCE,
            collected_at=datetime.now(KST),
            reference_date=reference,
            scope=f"공식 JSON 전시 {total:,}건 중 최근 등록 {len(selected):,}건 — 서울 전체 검색이 아닙니다",
            complete=False,
            source_total=total,
            row_count=len(selected),
        ),
        rows=selected,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--reference-date", type=date.fromisoformat, required=True)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    payload = json.loads(raw)
    dataset = build_snapshot(payload, args.reference_date, args.limit)
    path = load_settings().snapshot_path
    save_snapshot(dataset, path)
    provenance = {
        "source_url": SOURCE,
        "license": "서울특별시 · 공공누리 제1유형 출처표시",
        "source_file": args.input.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_all_categories": len(payload["DATA"]),
        "source_exhibitions": dataset.metadata.source_total,
        "selected_rows": len(dataset.rows),
        "selection": "전시/미술만 선택; 신청일, 시작일, 제목 내림차순; 앱 전시 ID 중복 제거 후 상위 limit건",
        "validation": "날짜 역전 또는 정규화 후 빈 제목은 제외; 원본 파일에서 확인 가능",
        "date_conversion": "Unix epoch milliseconds → Asia/Seoul; 행사 기간 변경 없음",
        "collected_at": dataset.metadata.collected_at.isoformat(),
        "reference_date": args.reference_date.isoformat(),
    }
    path.with_name("provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(dataset.metadata.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
