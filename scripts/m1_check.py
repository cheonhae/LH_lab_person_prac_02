"""outputs/m1/evidence.md 각 행의 '값'에 든 숫자가 원문에 글자 그대로 있는지 찾는다.

- 표준 라이브러리만 사용. 어떤 파일도 고치지 않고 결과를 화면에만 출력한다.
- 위치가 발언 순번([NN])이면 그 순번 발언에서, 아니면(절·표·행) 출처 파일 전체에서 찾는다.
- 출처·위치가 'A / B'로 여러 개면 짝을 맞춰 각각의 범위를 모두 찾을 범위로 쓴다.
- 값에 숫자가 없으면 '직접 확인'.
- 뜻은 판단하지 않는다(글자 일치만 본다).

실행: python3 scripts/m1_check.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "outputs" / "m1" / "evidence.md"
SOURCES = {
    "전사본": ROOT / "inputs" / "m1" / "G-M1-01_공고개정회의_전사본.md",
    "요약": ROOT / "inputs" / "m1" / "G-M1-02_회의전_민원현황요약.md",
    "명단": ROOT / "inputs" / "m1" / "G-M1-03_회의참석자.csv",
    "발언 처리": ROOT / "outputs" / "m1" / "utterance_table.md",
}

# 숫자 토큰: 날짜 → 시각 → 단위 붙은 수·기타 숫자 순으로 뽑는다.
DATE = r"(?:\d{4}\. )?\d{1,2}\. \d{1,2}\.(?:\([월화수목금토일]\))?"
TIME = r"\d{1,2}:\d{2}"
OTHER = r"\d+(?:[-.]\d+)*%?[가-힣]?"
TOKEN = re.compile(f"{DATE}|{TIME}|{OTHER}")
UTTER = re.compile(r"\[(\d{2})\]")


def read(path):
    return path.read_text(encoding="utf-8-sig")


def utterances(text):
    """전사본에서 {'05': '발언 본문'} 사전을 만든다."""
    out = {}
    for m in re.finditer(r"^\*\*\[(\d{2})\][^*]*\*\*(.*)$", text, re.M):
        out[m.group(1)] = m.group(2)
    return out


def parse_evidence():
    rows = []
    for line in read(EVIDENCE).splitlines():
        if not re.match(r"^\| E\d+ \|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        no, _sentence, value, src, pos = cells[:5]
        rows.append((no, value, src, pos))
    return rows


def scope_text(src, pos, utt):
    """출처·위치 짝마다 찾을 범위 글을 모아 하나로 잇는다."""
    srcs = [s.strip() for s in src.split("/")]
    poss = [p.strip() for p in pos.split("/")]
    if len(poss) != len(srcs):
        poss = [pos] * len(srcs)
    parts = []
    for s, p in zip(srcs, poss):
        path = SOURCES.get(s)
        if path is None:
            parts.append("")
            continue
        nums = UTTER.findall(p)
        if s == "전사본" and nums:
            parts.extend(utt.get(n, "") for n in nums)
        else:
            parts.append(read(path))
    return "\n".join(parts)


def main():
    utt = utterances(read(SOURCES["전사본"]))
    print("| # | 위치 | 값 | 결과 | 못 찾은 글자 |")
    print("|---|---|---|---|---|")
    counts = {"있음": 0, "없음": 0, "직접 확인": 0}
    for no, value, src, pos in parse_evidence():
        tokens = TOKEN.findall(value)
        if not tokens:
            result, missing = "직접 확인", ""
        else:
            text = scope_text(src, pos, utt)
            miss = [t for t in tokens if t not in text]
            result = "없음" if miss else "있음"
            missing = ", ".join(f"`{t}`" for t in miss)
        counts[result] += 1
        print(f"| {no} | {src} {pos} | {value} | {result} | {missing} |")
    print()
    print("합계: " + " · ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
