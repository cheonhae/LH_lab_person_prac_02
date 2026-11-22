"""rules/aggregation_rules.md 기준으로 inputs/m2 CSV 두 개를 집계한다.

- 표준 라이브러리만 사용한다. 원본 CSV는 읽기만 한다.
- 결과: outputs/m2/summary.csv, outputs/m2/excluded_rows.csv, outputs/m2/run_log.md
- 행 번호는 머리행을 빼고 1부터 센다.

실행: python3 scripts/aggregate.py
"""
import csv
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "inputs" / "m2" / "G-M2-01_민원대장_week1.csv"
BUDGET = ROOT / "inputs" / "m2" / "G-M2-02_홍보예산_집행현황.csv"
OUT = ROOT / "outputs" / "m2"
RULES = "rules/aggregation_rules.md"

LEDGER_ID = "G-M2-01"
BUDGET_ID = "G-M2-02"
MONEY = ("예산", "집행", "잔액")

# 민원대장 열별 허용 값(README 열 설명 기준). 이 밖의 값은 '그 밖의 계산 불가 행'.
ALLOWED = {
    "신청방법": {"콜센터", "온라인", "방문"},
    "민원유형": {"자격·소득", "접수 기간·방법", "제출 서류", "임대 조건", "기타"},
    "적용공고": {"v1", "v2"},
    "처리상태": {"접수", "처리중", "답변완료"},
}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def raw(row, fields):
    return ",".join(row[k] for k in fields)


def to_int(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def fmt(n):
    return f"{n:,}"


# ---------------------------------------------------------------- 민원대장
def process_ledger(fields, rows, excluded, log):
    seen = {}
    kept = []
    for i, r in enumerate(rows, 1):
        key = f"{LEDGER_ID}:{i}"
        # 그 밖의 계산 불가 행: 빈칸 또는 허용 값 밖
        blank = [k for k in fields if not (r.get(k) or "").strip()]
        odd = [k for k, ok in ALLOWED.items() if r.get(k) not in ok]
        # 2. 중복 행: 접수번호가 같고 모든 열이 같음
        sig = tuple(r[k] for k in fields)
        if r["접수번호"] in seen and seen[r["접수번호"]][1] == sig:
            first = seen[r["접수번호"]][0]
            excluded.append((key, f"중복 행: {first}행과 접수번호·모든 열이 같음", raw(r, fields)))
            log["rule"]["2. 중복 행"] += 1
            continue
        if blank or odd:
            why = "빈칸 " + ",".join(blank) if blank else "허용 값 밖 " + ",".join(odd)
            excluded.append((key, f"그 밖의 계산 불가 행({why}): 담당 확인 필요", raw(r, fields)))
            log["rule"]["그 밖의 계산 불가 행"] += 1
            continue
        seen.setdefault(r["접수번호"], (i, sig))
        kept.append(r)
    return kept


# ---------------------------------------------------------------- 홍보예산
def process_budget(fields, rows, excluded, log):
    kept, reference, total_row = [], [], None
    for i, r in enumerate(rows, 1):
        key = f"{BUDGET_ID}:{i}"
        # 1. 합계 행: 대조용으로 유지(집계에 더하지 않음)
        if r["항목코드"].strip() == "합계" or not r["항목명"].strip():
            total_row = (i, r)
            log["rule"]["1. 합계 행(대조용 유지)"] += 1
            continue
        # 2. 중복 행: 홍보예산에는 접수번호가 없어 해당 없음(rules 4절)
        vals = {k: to_int(r[k]) for k in MONEY}
        if any(v is None for v in vals.values()) or r["단위"] not in ("원", "천원"):
            excluded.append((key, "그 밖의 계산 불가 행(금액·단위 표기): 담당 확인 필요", raw(r, fields)))
            log["rule"]["그 밖의 계산 불가 행"] += 1
            continue
        # 3. 단위 섞임: 천원 → 원
        if r["단위"] == "천원":
            before = {k: vals[k] for k in MONEY}
            vals = {k: v * 1000 for k, v in vals.items()}
            log["fixed"].append((key, r["항목명"], "3. 단위 섞임",
                                 " / ".join(f"{k} {fmt(before[k])}천원" for k in MONEY),
                                 " / ".join(f"{k} {fmt(vals[k])}원" for k in MONEY)))
        # 4. 음수·0 정정 행: 분리해 참고값으로만
        if vals["예산"] == 0 or vals["집행"] < 0:
            excluded.append((key, "음수·0 정정 행: 정상 기준 합계에서 분리, 담당 확인 필요(참고값으로만 냄)", raw(r, fields)))
            log["rule"]["4. 음수·0 정정 행"] += 1
            reference.append((i, r["항목명"], vals))
            continue
        # 5. 잔액 불일치: 예산 − 집행으로 다시 계산
        calc = vals["예산"] - vals["집행"]
        if calc != vals["잔액"]:
            log["fixed"].append((key, r["항목명"], "5. 잔액 불일치",
                                 f"잔액 {fmt(vals['잔액'])}원", f"잔액 {fmt(calc)}원(예산 − 집행)"))
            vals["잔액"] = calc
        kept.append((i, r["항목명"], vals))
    return kept, reference, total_row


def rate(executed, budget):
    """집행률(%) — 마지막에 한 번만 소수 1자리로 반올림(0.5 올림)."""
    if not budget:
        return ""
    return str((Decimal(executed) * 100 / Decimal(budget)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    excluded = []
    log = {"rule": Counter(), "fixed": []}

    l_fields, l_rows = read_rows(LEDGER)
    b_fields, b_rows = read_rows(BUDGET)

    ledger = process_ledger(l_fields, l_rows, excluded, log)
    budget, reference, total_row = process_budget(b_fields, b_rows, excluded, log)

    # ---------------- summary.csv
    s = []
    s.append(("민원대장", "집계 포함 행 수", len(ledger), "건", ""))
    for col in ("민원유형", "처리상태", "신청방법", "적용공고"):
        for k, v in sorted(Counter(r[col] for r in ledger).items(), key=lambda x: (-x[1], x[0])):
            s.append(("민원대장", f"{col}: {k}", v, "건", ""))
    unresolved = sum(1 for r in ledger if r["처리상태"] in ("접수", "처리중"))
    s.append(("민원대장", "미처리(접수·처리중)", unresolved, "건", ""))

    tb = sum(v["예산"] for _, _, v in budget)
    te = sum(v["집행"] for _, _, v in budget)
    tr = sum(v["잔액"] for _, _, v in budget)
    s.append(("홍보예산", "집계 포함 행 수", len(budget), "행", "정상 기준"))
    s.append(("홍보예산", "예산 합계", tb, "원", "정상 기준"))
    s.append(("홍보예산", "집행 합계", te, "원", "정상 기준"))
    s.append(("홍보예산", "잔액 합계", tr, "원", "정상 기준(잔액은 예산 − 집행으로 재계산)"))
    s.append(("홍보예산", "집행률", rate(te, tb), "%", "정상 기준, 최종 단계에서 한 번만 반올림(소수 1자리, 0.5 올림)"))
    for i, name, v in reference:
        for k in MONEY:
            s.append(("홍보예산(참고)", f"{name}({BUDGET_ID}:{i}) {k}", v[k], "원", "담당 확인 필요 — 정상 기준 합계에 미포함"))
        rb, re_ = tb + v["예산"], te + v["집행"]
        s.append(("홍보예산(참고)", f"{name} 반영 시 집행률", rate(re_, rb), "%", "담당 확인 필요 — 참고값"))

    with (OUT / "summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["자료", "항목", "값", "단위", "비고"])
        w.writerows(s)

    # ---------------- excluded_rows.csv
    with (OUT / "excluded_rows.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["원본행", "사유", "원본값"])
        w.writerows(excluded)

    # ---------------- run_log.md
    ex_l = sum(1 for k, _, _ in excluded if k.startswith(LEDGER_ID))
    ex_b = sum(1 for k, _, _ in excluded if k.startswith(BUDGET_ID))
    total_kept_b = 1 if total_row else 0
    lines = [
        "> [가상 자료] 이 자료의 기관·인물·지구·업체·수치·연락처는 모두 실습용 가상 정보입니다. 실제 사실이 아니며 실무에 사용할 수 없습니다.",
        "",
        "# 집계 실행 기록",
        "",
        f"- 실행 명령: `python3 scripts/{Path(sys.argv[0]).name}`",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 집계 기준: `{RULES}`",
        "- 행 번호: 머리행 제외, 1부터",
        "",
        "## 1. 입력 파일",
        "",
        "| 파일 | 데이터 행 수 |",
        "|---|---|",
        f"| `{LEDGER.relative_to(ROOT)}` | {len(l_rows)} |",
        f"| `{BUDGET.relative_to(ROOT)}` | {len(b_rows)} |",
        "",
        "## 2. 행 수 전후",
        "",
        "| 자료 | 처리 전 | 제외 | 대조용 유지(집계 미포함) | 집계 포함 |",
        "|---|---|---|---|---|",
        f"| 민원대장 | {len(l_rows)} | {ex_l} | 0 | {len(ledger)} |",
        f"| 홍보예산 | {len(b_rows)} | {ex_b} | {total_kept_b} | {len(budget)} |",
        "",
        "## 3. 규칙별 건수",
        "",
        "| 규칙 | 건수 | 처리 |",
        "|---|---|---|",
    ]
    rule_rows = [
        ("1. 합계 행(대조용 유지)", "집계 미포함, 5절 대조"),
        ("2. 중복 행", "제외"),
        ("3. 단위 섞임", "고쳐서 포함"),
        ("4. 음수·0 정정 행", "제외(참고값으로만)"),
        ("5. 잔액 불일치", "고쳐서 포함"),
        ("그 밖의 계산 불가 행", "제외"),
    ]
    fixed_count = Counter(rule for _, _, rule, _, _ in log["fixed"])
    for name, how in rule_rows:
        n = fixed_count[name] if name in ("3. 단위 섞임", "5. 잔액 불일치") else log["rule"][name]
        lines.append(f"| {name} | {n} | {how} |")
    lines += [
        "",
        "제외한 행의 사유와 원본값은 `outputs/m2/excluded_rows.csv`에 있다.",
        "",
        "## 4. 고쳐서 포함한 행",
        "",
        "| 원본행 | 항목 | 규칙 | 고치기 전 | 고친 값 |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {k} | {n} | {rule} | {b} | {a} |" for k, n, rule, b, a in log["fixed"]]
    if total_row:
        i, r = total_row
        lines += [
            "",
            "## 5. 합계 행 대조 (대조용 유지)",
            "",
            f"원본 `{BUDGET_ID}:{i}` 합계 행과 재계산 정상 기준 합계를 나란히 적는다.",
            "",
            "| 항목 | 원본 합계 행 | 재계산(정상 기준) | 차이 |",
            "|---|---|---|---|",
        ]
        for k, v in zip(MONEY, (tb, te, tr)):
            o = to_int(r[k])
            lines.append(f"| {k} | {fmt(o)} {r['단위']} | {fmt(v)} 원 | {fmt(o - v)} |")
    lines.append("")
    (OUT / "run_log.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"민원대장 {len(l_rows)}행 → 포함 {len(ledger)} / 제외 {ex_l}")
    print(f"홍보예산 {len(b_rows)}행 → 포함 {len(budget)} / 제외 {ex_b} / 합계 행 대조용 {total_kept_b}")
    print(f"홍보예산 정상 기준: 예산 {fmt(tb)}원, 집행 {fmt(te)}원, 집행률 {rate(te, tb)}%")
    print(f"결과: {OUT.relative_to(ROOT)}/summary.csv, excluded_rows.csv, run_log.md")


if __name__ == "__main__":
    main()
