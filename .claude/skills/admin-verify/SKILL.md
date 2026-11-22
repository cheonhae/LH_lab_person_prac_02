---
name: admin-verify
description: 공고·민원 자료(회의 전사본·민원대장·정정 메모)를 받으면 근거·집계·정합 검증 절차로 처리한다. "검증 절차로 처리해 줘", "다음 주 자료 처리해 줘"라고 할 때 쓴다.
---

> [가상 자료] 이 자료의 기관·인물·지구·업체·수치·연락처는 모두 실습용 가상 정보입니다. 실제 사실이 아니며 실무에 사용할 수 없습니다.

# 행정 자료 검증 절차

## 1. 언제 쓰나
- 공고 개정 회의 전사본, 민원대장 CSV, 정정 메모를 한 번에 받아 회의록·집계·연결 문서를 만들 때 쓴다.
- 새 주차 자료(`inputs/m4/` 등)를 처음부터 같은 기준으로 다시 처리할 때 쓴다.

## 2. 입력
- 회의 전사본(`*_전사본.md`, 발언 순번 `[01]`부터)
- 민원대장 CSV(`접수번호,접수일,신청방법,민원유형,적용공고,처리상태`)
- 정정 메모(`*_정정메모*.md`)
- 기준 파일: `CLAUDE.md`, `rules/aggregation_rules.md`, `ledger/ledger.csv`
## 3. 절차
1. **근거:** 전사본으로 `utterance_table.md`·`minutes.md`·`evidence.md`를 만든다. `python3 scripts/m1_check.py` 결과와 원문을 직접 연 대조 결과를 `evidence_check.md`에 남긴다.
2. **집계:** `rules/aggregation_rules.md` 기준으로 `python3 scripts/aggregate.py`를 실행해 `summary.csv`·`excluded_rows.csv`·`run_log.md`를 만든다. `check.md`에서 기대값·두 번째 방법과 대조한다.
3. **정합:** 정정 메모로 바뀌는 대장 값은 `impact_list.md`를 만들어 승인받은 뒤, 대장과 승인한 위치만 한꺼번에 고친다. `python3 scripts/consistency_check.py`로 불일치 0건을 확인한다.
## 4. 확인 체크
- [ ] `git status inputs/`에 변경이 없다(원본을 고치거나 지우지 않았다).
- [ ] 회의록의 모든 수치·결정·기한에 `[E번호]`와 근거표 행이 있고, `m1_check.py`의 '없음'·'직접 확인' 행은 원문을 열어 대조했다.
- [ ] 집계 결과가 기대값·두 번째 방법 결과와 모두 같고, 제외한 행은 `excluded_rows.csv`에 사유와 함께 있다.
- [ ] 영향 목록을 승인받기 전에 대장·문서를 고치지 않았고, `consistency_report.md`의 고친 뒤 불일치가 0건이다.
- [ ] 남은 `{확인 필요}` 항목을 모두 모아 요약에 적었다.
## 5. 하지 않는 것
- `inputs/` 원본 파일을 고치거나 지우지 않는다.
- 계산을 말로 하지 않는다. 숫자는 스크립트 실행 결과만 쓴다.
- 자격·당첨·보상을 확정하는 문장을 쓰지 않는다. "담당 검토 후 확정" 또는 `{확인 필요: 항목}`으로 쓴다.
- 대외 발송·게시를 하지 않는다. 초안까지만 만든다.

## 6. 출력
| 단계 | 출력 |
|---|---|
| 근거 | `outputs/m{n}/utterance_table.md`, `minutes.md`, `evidence.md`, `evidence_check.md` |
| 집계 | `outputs/m{n}/summary.csv`, `excluded_rows.csv`, `run_log.md`, `check.md` |
| 정합 | `ledger/ledger.csv` 갱신(단일 기준), `outputs/m{n}/impact_list.md`, `consistency_report.md` |
| 요약 | 단계별 결과와 남은 `{확인 필요}` 목록 |

## 7. 예시
- 입력: "inputs/m4 자료를 검증 절차로 처리해 줘"
- 결과: 회의록·근거표 → 집계 3종 → 대장 갱신·정합 검사 순으로 만들고, 마지막에 남은 확인 필요 항목을 표로 보여 준다.
