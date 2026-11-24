> [가상 자료] 이 자료의 기관·인물·지구·업체·수치·연락처는 모두 실습용 가상 정보입니다. 실제 사실이 아니며 실무에 사용할 수 없습니다.

# 실행 기록

- 실행 명령: `python scripts/aggregate.py --complaints inputs/m4/G-M4-02_민원대장_week2.csv --budget none --outdir outputs/m4`
- 규칙: `rules/aggregation_rules.md`

## 민원대장 — `inputs/m4/G-M4-02_민원대장_week2.csv`

- 원본 데이터 행 수: 42행 → 유효 민원 41건
- 제외: 중복 1행
- 수정 행: 3행
  - G-M4-02 13행: 신청방법 정규화 '홈페이지' → '온라인'
  - G-M4-02 28행: 신청방법 정규화 '전화' → '콜센터'
  - G-M4-02 39행: 신청방법 정규화 '내방' → '방문'

- 결과: `outputs/m4/summary.csv`(16행), `outputs/m4/excluded_rows.csv`(1행)

## 재실행 기록(규칙 보강)

- 보강 전 비교 실행: `METHOD_MAP = {}` 상태로 스크래치에서 실행 — 신청방법 콜센터 21, 온라인 14, 방문 3, 홈페이지 1, 전화 1, 내방 1(산출물로 쓰지 않음)
- 보강: `rules/aggregation_rules.md` 2.3절 대응표, `CLAUDE.md` 2절 한 문장, `scripts/aggregate.py`(대응표에 없는 표기는 멈춤)
- 보강 후 실행: 위 실행 명령 — 콜센터 22, 온라인 15, 방문 4, 수정 행 3(13·28·39행). 다른 값은 같음. 비교는 `check.md` 2-1절
