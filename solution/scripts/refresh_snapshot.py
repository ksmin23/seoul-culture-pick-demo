import argparse
from datetime import date

from app.config import load_settings
from app.errors import AppError
from app.seoul_api import fetch_exhibitions
from app.snapshots import save_snapshot


def main():
    parser = argparse.ArgumentParser(description="실제 서울 공공데이터 저장본 갱신")
    parser.add_argument("--sample", action="store_true", help="공식 공개 샘플 5건만 저장")
    parser.add_argument("--reference-date", type=date.fromisoformat)
    args = parser.parse_args()
    settings = load_settings()
    try:
        dataset = fetch_exhibitions(
            "sample" if args.sample else settings.seoul_key, sample=args.sample
        )
        if args.reference_date:
            dataset.metadata.reference_date = args.reference_date
        save_snapshot(dataset, settings.snapshot_path)
        print(f"저장 완료: {len(dataset.rows)}건 / {dataset.metadata.scope}")
        print(f"시연 기준일: {dataset.metadata.reference_date}")
    except AppError as error:
        print(error.message)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
