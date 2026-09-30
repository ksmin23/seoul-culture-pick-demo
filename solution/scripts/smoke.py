import argparse
import json

from app.agent import recommend
from app.config import load_settings
from app.errors import AppError


def main():
    parser = argparse.ArgumentParser(description="실제 모델 호출을 포함하는 Agent smoke test")
    parser.add_argument("--mode", choices=["snapshot", "live"], default="snapshot")
    parser.add_argument("--question", default="이번 주말 종로에서 볼 수 있는 무료 전시 3개 찾아줘.")
    args = parser.parse_args()
    try:
        result = recommend(args.question, args.mode, load_settings())
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except AppError as error:
        print(f"{error.code}: {error.message}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
