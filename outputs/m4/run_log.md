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
