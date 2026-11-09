# Agent 발전 검증 기록 — 2026-11-09

## 실행 구분

| 검증 | 입력/외부 연결 | 결과 및 근거 |
|---|---|---|
| 오프라인 전체 테스트 | 가짜 응답과 합성 fixture, 외부 요청 없음 | 147 passed, 실제 연동 2건 제외. JUnit: `agent-upgrade-all-unit.xml` |
| Retrieval 새 3편 수집 | 실제 arXiv 검색·원문 다운로드 | completed, selected 3, 실패/경고 0. `agent-evolution-retrieval.json` |
| Writer 생성·근거 검토 | 실제 Groq, 원문 발췌를 담은 그룹 2 예시 8편 | 실제 연동 pytest 1건 통과. `agent-upgrade-groq-live.xml`, `groq-live-result.json` |
| Coverage 재작성 | 실제 Groq, 이전 생성본과 피드백 | revision 1 생성, 내용 변경, 두 번째 요청 차단. `agent-evolution-live-final.json` |
| 참고문헌 품질 판단 | 저장된 실제 논문 8편, 외부 API 없음 | 참고문헌 388개, 공통 3개. `agent-evolution-live.json` |
| 새 수집본의 Agent 2 CLI | 새 실제 논문 3편, 외부 API 없음 | 참고문헌 162개, 공통 0개, possible duplicates 0. `agent-evolution-references-fresh.json` |
| 검색 모델의 부족 상황 판단 | 실제 Groq + 의도적으로 구성한 부족 관찰값 | 실제 실패한 검색에서 발생한 관찰이 아님. 제안 질의의 후속 검색도 실행하지 않음. |

## 최종 Writer 실제 생성

보고서 `e226b5dd03b94941902fb380ecc50a88`, revision 0. 실제 HTTP 호출 4회(초안 2회, 검토 2회), 실행 약 132초. 제공자 토큰 예산 초기화 대기 3회가 포함됐다. 첫 초안의 잘못된 limitation 인용 범주를 검사에서 거부했고 수정 초안은 통과했다. 생성 문장 12개를 별도 호출로 검토했으며 이 실행의 모델 검토에서는 모두 supported로 반환됐다.

- 보고서: `examples/groq-report.md`.
- 초안/검토/결정 파일 경로: `groq-live-result.json`의 result 내 `draft_path`, `review_path`, `decisions_path`.
- `coverage_incomplete`: 그룹 2 예시에 필수 분석 필드가 없고 일부 보고서 영역을 작성할 근거가 부족하기 때문이다. 실행 실패나 완성된 최종 보고서로 해석하지 않는다.
- `evidence_verified=false`: 모델 supported 판정이 원문의 함의를 완벽히 검증했다고 주장하지 않는다. 사람/Supervisor의 사실 검증이 남아 있다.

## 관찰·중단·보류 테스트

Mock 테스트로 후보 부족 시 확대, 새 후보 재순위화, 동일 후보 재다운로드 방지, 검색 횟수 제한, 관련성 유지, 알려진 서비스 장애 반복 호출 방지, 주제 이탈 질의 거부, 부족 상황에서 더 엄격한 AND 질의 거부를 확인했다. 실제 새 3편 검색은 첫 회에 충분했으므로 실제 검색 중 재계획이 일어났다고 주장하지 않는다.

Writer는 없는 claim ID, 다른 논문의 요약 근거, 근거 없는 수치, 상충 한쪽만 인용, 검토 누락을 검사한다. 모델이 수정 후에도 근거 없는 수치를 생성하는 Mock 사례에서는 해당 문장만 제외하고 이유·원문을 decisions에 남기며 coverage 미충족을 반환한다. 부정확한 출처 ID나 유효하지 않은 구조를 조용히 성공 처리하지 않는다.

Agent 2는 실제 입력에서 강한 식별자 없는 인용 158개와 식별 그룹 385개를 기록했다. 미해결 후보가 없다는 것은 모든 서지 항목의 사실 검증이 끝났다는 의미가 아니다. 충돌 ID를 넣은 Mock에서는 임의 통합하지 않고 review_required를 반환하는 것을 확인했다.

새 수집 3편에는 공통 문헌이 검출되지 않았다. 이전 8편의 공통 3개와 입력이 다르므로 모순이 아니다. 공통 문헌 수를 맞추기 위해 없는 문헌을 추가하지 않는다.

Coverage 테스트는 이전 보고서와 피드백 전달, 내용 변경, SQLite에 기록된 최대 1회 제한, 두 번째 요청의 API 호출 전 거부를 확인한다. 구조 수정 재시도와 Supervisor Coverage 재작성 횟수는 별도다.

최종 재작성은 보고서 `e226b5dd03b94941902fb380ecc50a88`에 실제 Groq 5회(초안 2회/검토 3회)를 호출했다. 첫 초안의 근거 없는 수치 19200을 거부했고, 수정 후 18문장을 검토해 17개를 채택하고 1개를 보류했다. 이전 보고서를 전달했고 내용이 변경됐으며 두 번째 Coverage 요청은 차단됐다. `examples/agent-evolution-report.md`가 해당 revision 1이다. 필수 입력 23개와 일부 생성 영역/검토 누락이 남아 최종 상태는 coverage_incomplete다.

같은 검증 스크립트의 통제된 부족 관찰에서 실제 검색 모델은 expand_search를 선택했다. 실제 적용 행동은 원래 질의를 유지하고 후보 수를 9에서 18로 늘리는 것이다. 모델의 사유 문구에는 키워드 추가가 언급되지만 이 행동에서 질의는 변경되지 않는다. 제안의 후속 검색은 실행하지 않았다. 초기 기록 `agent-evolution-live.json`은 이전 구현의 성공 기록으로 보존하며 최종 판단은 `agent-evolution-live-final.json`을 따른다.

## 개발 중 실제로 발생한 실패

초기 실험에서 API 요청 크기 제한(413), JSON 생성 오류(400), 토큰 한도(429), 잘못된 수치/인용 범주 생성과 보고서 출력 코드 오류가 있었다. 중복 원문 payload 제거, 출력 길이 제한, 제공자 초기화 대기, 제한된 수정 요청, 수치 문장 보류, 출력 메서드 수정 후 다시 실행했다. 실패한 실행을 성공으로 합산하지 않는다. 최종 pytest XML과 개별 JSON만 해당 성공 실행의 근거다.

오프라인 실행의 Starlette 413 상수 폐기 경고 1건은 외부 A2A SDK에서 발생하며 테스트 실패가 아니다. 로컬 GROBID, 타 그룹 서버, 실제 그룹 2 분석, Supervisor 최종 Evidence 판정은 이번 변경에서 실제 연동 검증하지 않았다.
