"""docs/demo_sample.csv 의 접수건수 합계를 구해 docs/sum_demo_result.md 에 저장한다.

사용 예:
    python3 scripts/sum_demo.py                       # 전체 합계
    python3 scripts/sum_demo.py --지구 행복2지구        # 조건 지정
    python3 scripts/sum_demo.py --신청방법 방문 --시작 2026-11-09 --끝 2026-11-13
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "demo_sample.csv"
OUT = ROOT / "docs" / "sum_demo_result.md"


def main():
    p = argparse.ArgumentParser(description="demo_sample.csv 접수건수 합계")
    p.add_argument("--지구", dest="district")
    p.add_argument("--신청방법", dest="method")
    p.add_argument("--시작", dest="start", help="접수일 시작 (YYYY-MM-DD, 포함)")
    p.add_argument("--끝", dest="end", help="접수일 끝 (YYYY-MM-DD, 포함)")
    a = p.parse_args()

    with SRC.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    picked = [
        r for r in rows
        if (not a.district or r["지구"] == a.district)
        and (not a.method or r["신청방법"] == a.method)
        and (not a.start or r["접수일"] >= a.start)
        and (not a.end or r["접수일"] <= a.end)
    ]
    total = sum(int(r["접수건수"]) for r in picked)

    conds = [f"{k}={v}" for k, v in
             [("지구", a.district), ("신청방법", a.method), ("시작", a.start), ("끝", a.end)] if v]
    cond_text = ", ".join(conds) if conds else "없음 (전체)"

    lines = [
        "# demo_sample.csv 접수건수 합계",
        "",
        f"- 원본: `docs/demo_sample.csv` (전체 {len(rows)}행)",
        f"- 조건: {cond_text}",
        f"- 대상 행 수: {len(picked)}",
        f"- **접수건수 합계: {total:,}건**",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 실행 명령: `python3 scripts/sum_demo.py{''.join(f' --{c.replace("=", " ")}' for c in conds)}`",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"조건: {cond_text} / 대상 {len(picked)}행 / 합계 {total:,}건 → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
