"""ledger/ledger.csv와 문서의 수치·날짜를 대조해 outputs/m3/consistency_report.md에 쓴다.

- 표준 라이브러리만 사용한다. 문서와 대장은 읽기만 한다.
- 고치기 전: inputs/m3 초안(G-M3-01·02·04), 회의록은 main(origin/master)의 outputs/m1/minutes.md
- 고친 뒤: outputs/m3/doc_G-M3-01·02·04.md, 작업 중인 outputs/m1/minutes.md
- 대조 방식: 문장 속 표현(예: '접수 기간 … ~ …', '접수 마감(…)', '설명회(…)')으로 대장 항목을 찾아
  값이 대장과 같은지만 본다. 대장 항목과 연결되지 않는 날짜는 대조하지 않는다.
- 날짜에 요일이 붙어 있으면 2026년 달력과 맞는지도 본다.

실행: python3 scripts/consistency_check.py
"""
import csv
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ledger" / "ledger.csv"
REPORT = ROOT / "outputs" / "m3" / "consistency_report.md"
MAIN_REF = "origin/master"
MINUTES = "outputs/m1/minutes.md"

DOCS = [  # (문서 이름, 고치기 전, 고친 뒤)
    ("G-M3-01 자료제출요청 공문", ("file", "inputs/m3/G-M3-01_자료제출요청_공문_초안.md"), ("file", "outputs/m3/doc_G-M3-01.md")),
    ("G-M3-02 주간민원보고", ("file", "inputs/m3/G-M3-02_주간민원보고_초안.md"), ("file", "outputs/m3/doc_G-M3-02.md")),
    ("G-M3-04 지침 신구대비표", ("file", "inputs/m3/G-M3-04_지침_신구대비표_초안.md"), ("file", "outputs/m3/doc_G-M3-04.md")),
    ("회의록", ("git", MINUTES), ("file", MINUTES)),
]
# 대조에서 빼는 절: 회의록 2·3·4절은 회의 당시 기록이라 대조 대상이 아님
SKIP_SECTIONS = {"회의록": ("2.", "3.", "4.")}

WEEK = "월화수목금토일"
DATE = r"(?:(\d{4})\. )?(\d{1,2})\. (\d{1,2})\.(?:\(([월화수목금토일])\))?"
DATE_RE = re.compile(DATE)
RANGE_RE = re.compile(DATE + r"\s*~\s*" + DATE)

# 날짜 하나를 대장 항목에 연결하는 표현: (바로 뒤에 날짜가 오는 앞 표현, 미사용, 항목ID, 날짜 뒤 10자 안에 있어야 할 말)
SINGLE = [
    (re.compile(r"접수 마감\("), 0, "G-L03", None),
    (re.compile(r"설명회[ (]"), 0, "G-L11", None),
    (re.compile(r"제출 기한[은:]? ?"), 0, "G-L12", None),
    (re.compile(r"정정공고\("), 0, "G-L01", "게시"),
]
# 줄에 이 말이 있으면, 아직 다른 규칙에 쓰이지 않은 날짜를 그 항목과 대조
LINE_RULES = [
    ("집행률", "G-L10"),
    ("송부", "G-L09"),
    ("주간 민원 보고", "G-L09"),
]
COUNTS = [
    (re.compile(r"접수 민원 (\d+)건"), "G-L06"),
    (re.compile(r"자격·소득 (\d+)건"), "G-L07"),
    (re.compile(r"미처리\(접수·처리중\) (\d+)건"), "G-L08"),
]
PERIOD_WORDS = ("집계", "접수분", "지난주")


def load_ledger():
    with LEDGER.open(encoding="utf-8-sig", newline="") as f:
        return {r["항목ID"]: r for r in csv.DictReader(f)}


def read_source(src):
    kind, path = src
    if kind == "git":
        out = subprocess.run(["git", "show", f"{MAIN_REF}:{path}"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        return out.stdout, f"`{path}` ({MAIN_REF})"
    return (ROOT / path).read_text(encoding="utf-8-sig"), f"`{path}`"


def to_date(m, off=0):
    y, mo, d, wd = m.group(1 + off), m.group(2 + off), m.group(3 + off), m.group(4 + off)
    return date(int(y) if y else 2026, int(mo), int(d)), wd


def iso(d):
    return d.isoformat()


def check(text, ledger, skip_sections=()):
    """불일치·요일 오류·대조 제외 목록을 돌려준다."""
    bad, weekday, skipped, checked, ok = [], [], [], 0, []
    section = ""
    old_col = None  # 신구대비표 '현행' 칸 끝 위치
    for no, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            section = line[3:].split(" ")[0]  # 회의록 '## 5. 후속 조치' → '5.'
        if section in skip_sections and not line.startswith("## "):
            if DATE_RE.search(line) or re.search(r"\d+건", line):
                skipped.append((no, line.strip()[:60] + ("…" if len(line.strip()) > 60 else ""),
                                f"회의록 {section[:-1]}절 회의 기록(대조 대상 아님)"))
            continue
        if line.startswith("| 현행 |"):
            old_col = True
        elif not line.startswith("|"):
            old_col = None
        cut = 0
        if old_col and line.startswith("| ") and not line.startswith("|---") and not line.startswith("| 현행"):
            cut = line.index("|", 1)  # 현행 칸 끝
        used = set()

        def note(item, got, where):
            nonlocal checked
            checked += 1
            want = ledger[item]["값"]
            if got != want:
                bad.append((no, section, item, ledger[item]["항목"], got, want, where))
            else:
                ok.append((no, section, item, ledger[item]["항목"], got, want, where))

        # 요일 확인
        for m in DATE_RE.finditer(line):
            d, wd = to_date(m)
            if wd and WEEK[d.weekday()] != wd:
                weekday.append((no, section, m.group(0), WEEK[d.weekday()]))
        # 기간
        for m in RANGE_RE.finditer(line):
            used.update(range(m.start(), m.end()))
            if m.start() < cut:
                skipped.append((no, m.group(0), "신구대비표 현행 칸(개정 전 조문)"))
                continue
            a, _ = to_date(m, 0)
            b, _ = to_date(m, 4)
            if any(w in line for w in PERIOD_WORDS):
                note("G-L04", iso(a), m.group(0)); note("G-L05", iso(b), m.group(0))
            elif "접수" in line or "정정공고" in line:
                note("G-L02", iso(a), m.group(0)); note("G-L03", iso(b), m.group(0))
        # 날짜 하나
        for pat, gap, item, after in SINGLE:
            for k in pat.finditer(line):
                m = DATE_RE.match(line, k.end())
                if not m or m.start() in used or m.start() < cut:
                    continue
                if after and after not in line[m.end():m.end() + 10]:
                    continue
                used.update(range(m.start(), m.end()))
                d, _ = to_date(m)
                note(item, iso(d), line[k.start():m.end()])
        # 줄 단위
        for word, item in LINE_RULES:
            if word not in line:
                continue
            for m in DATE_RE.finditer(line):
                if m.start() in used or m.start() < cut:
                    continue
                used.update(range(m.start(), m.end()))
                d, _ = to_date(m)
                note(item, iso(d), f"'{word}' 줄의 {m.group(0)}")
        # 건수
        for pat, item in COUNTS:
            for m in pat.finditer(line):
                note(item, m.group(1), m.group(0))
    return bad, weekday, skipped, checked, ok


def main():
    ledger = load_ledger()
    results = []
    for name, before, after in DOCS:
        row = [name]
        for src in (before, after):
            text, label = read_source(src)
            row.append((label, *check(text, ledger, SKIP_SECTIONS.get(name, ()))))
        results.append(row)

    L = [
        "> [가상 자료] 이 자료의 기관·인물·지구·업체·수치·연락처는 모두 실습용 가상 정보입니다. 실제 사실이 아니며 실무에 사용할 수 없습니다.",
        "",
        "# 대장 정합 점검 결과",
        "",
        f"- 실행 명령: `python3 scripts/{Path(sys.argv[0]).name}`",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "- 기준: `ledger/ledger.csv` (G-L03 접수 마감일 2026-11-20 반영본)",
        f"- 고치기 전 회의록: main(`{MAIN_REF}`)의 `{MINUTES}`",
        "- 대조 방식: 문장 속 표현으로 대장 항목을 찾아 값이 같은지만 본다. 대장 항목과 연결되지 않는 날짜는 대조하지 않는다.",
        "- 대조 제외: 회의록 2·3·4절(회의 당시 기록). 제외한 줄은 7절에 적는다.",
        "",
        "## 1. 요약",
        "",
        "| 문서 | 고치기 전 대조 수 | 고치기 전 불일치 | 고친 뒤 대조 수 | 고친 뒤 불일치 | 고친 뒤 일치 | 고쳐서 일치된 곳 | 요일 오류(전 → 후) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    def fixed_list(before, after):
        """고치기 전 불일치였다가 고친 뒤 대장과 같아진 곳(같은 줄·같은 항목 기준)."""
        after_ok = {}
        for r in after[5]:
            after_ok.setdefault((r[0], r[2]), []).append(r)
        out = []
        for r in before[1]:
            hit = after_ok.get((r[0], r[2]))
            if hit:
                out.append((r, hit.pop(0)))
        return out

    tb = ta = tok = tfix = 0
    for name, bf, af in results:
        fx = fixed_list(bf, af)
        tb += len(bf[1]); ta += len(af[1]); tok += len(af[5]); tfix += len(fx)
        L.append(f"| {name} | {bf[4]} | {len(bf[1])} | {af[4]} | {len(af[1])} | {len(af[5])} | {len(fx)} | {len(bf[2])} → {len(af[2])} |")
    L.append(f"| **합계** | | **{tb}** | | **{ta}** | **{tok}** | **{tfix}** | |")

    for title, idx in (("2. 고치기 전 불일치", 1), ("3. 고친 뒤 불일치", 2)):
        L += ["", f"## {title}", "", "| 문서 | 줄 | 절 | 대장 항목 | 문서 값 | 대장 값 | 문서 표현 |", "|---|---|---|---|---|---|---|"]
        n = 0
        for r in results:
            label, bad = r[idx][0], r[idx][1]
            for no, sec, item, iname, got, want, where in bad:
                L.append(f"| {label} | {no} | {sec or '—'} | {item} {iname} | {got} | {want} | {where} |")
                n += 1
        if not n:
            L.append("| (없음) | | | | | | |")

    L += ["", "## 4. 고쳐서 일치된 곳 (고치기 전 불일치 → 고친 뒤 일치)", "",
          "| 문서(고친 뒤) | 줄 | 절 | 대장 항목 | 고치기 전 값 | 고친 뒤 값 | 대장 값 | 결과 |",
          "|---|---|---|---|---|---|---|---|"]
    n = 0
    for name, bf, af in results:
        for (no, sec, item, iname, got_b, want, _), (_, _, _, _, got_a, _, where_a) in fixed_list(bf, af):
            L.append(f"| {af[0]} | {no} | {sec or '—'} | {item} {iname} | {got_b} | {got_a} ({where_a}) | {want} | 일치 |")
            n += 1
    if not n:
        L.append("| (없음) | | | | | | | |")

    L += ["", "## 5. 고친 뒤 일치 전체", "", "| 문서 | 줄 | 절 | 대장 항목 | 문서 값 | 대장 값 | 문서 표현 |", "|---|---|---|---|---|---|---|"]
    for name, bf, af in results:
        for no, sec, item, iname, got, want, where in af[5]:
            L.append(f"| {af[0]} | {no} | {sec or '—'} | {item} {iname} | {got} | {want} | {where} |")

    L += ["", "## 6. 요일 오류 (2026년 달력)", "", "| 문서 | 줄 | 절 | 문서 표기 | 실제 요일 |", "|---|---|---|---|---|"]
    n = 0
    for r in results:
        for side in (1, 2):
            label, _, wk = r[side][0], r[side][1], r[side][2]
            for no, sec, txt, real in wk:
                L.append(f"| {label} | {no} | {sec or '—'} | {txt} | {real} |"); n += 1
    if not n:
        L.append("| (없음) | | | | |")

    L += ["", "## 7. 대조에서 뺀 위치", "", "| 문서 | 줄 | 표기 | 사유 |", "|---|---|---|---|"]
    n = 0
    for r in results:
        for side in (1, 2):
            label, sk = r[side][0], r[side][3]
            for no, txt, why in sk:
                L.append(f"| {label} | {no} | {txt} | {why} |"); n += 1
    if not n:
        L.append("| (없음) | | | |")
    L.append("")
    REPORT.write_text("\n".join(L), encoding="utf-8")

    for name, b, a in results:
        print(f"{name}: 고치기 전 불일치 {len(b[1])}건 → 고친 뒤 불일치 {len(a[1])}건, 고쳐서 일치 {len(fixed_list(b, a))}곳")
    print(f"합계: 불일치 {tb}건 → {ta}건, 고쳐서 일치 {tfix}곳, 고친 뒤 일치 전체 {tok}곳 / 결과: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
