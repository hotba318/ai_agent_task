# 사용자 시연 실행의 검색 실패 진단

**후속 해결:** 이후 서버 응답 유형을 더 조사하고, arXiv API 장애 시 독립 DataCite 검색을 사용하도록 개선해 실제 새 논문 3편 수집에 성공했다. 현재 동작과 사용자 실행 방법은 [복구 기록](search-recovery.md)을 따른다. 아래는 당시의 실패와 1차 진단 기록이다.

2026-11-05. 사용자가 직접 실행한 결과:

- Agent 2: Common references 3 / possible duplicates 0 → 실행 성공.
- Writer A2A/Groq: test passed, report_id `955478d0152a436fa689fab5313b2a0a` → 실제 서비스 호출 및 보고서 생성 성공.
- Writer input-required / missing input fields 23 → 그룹 2 예시 입력의 분석 누락을 보존한 상태. Supervisor PASS는 아님.
- StarletteDeprecationWarning → SDK의 폐기 예정 HTTP 상수 안내. 해당 실행에서는 테스트 성공을 막지 않았음.
- Retrieval: run `c735d0283f3a464ca37556058ef8528c`, failed, 0/3 → 이번 새 검색·수집은 실패.

## 실제 재현

동일한 `export.arxiv.org/api/query` 검색 파라미터를 한 번 조회해 확인했다:

| 항목 | 관측 |
|---|---|
| HTTP | **429** |
| Content-Type | text/html |
| Retry-After | 없음 |
| 응답 크기 | 14 bytes |
| Atom feed 수신 | 아니오 |

HTTP 429는 요청 제한 응답이다. [RFC 6585](https://www.rfc-editor.org/rfc/rfc6585.html#section-4). 이 관측은 재현 요청의 결과이며, 기존 실패 시점의 HTTP 상태 코드는 기존 코드가 기록하지 않아 소급해 확정할 수 없다. arXiv 전체 서비스 장애나 특정 사용자/IP의 원인으로 단정하지 않는다. Groq Key 문제와는 다른 요청 경로다.

## 코드 수정

- 재시도 종료 오류에 실제 HTTP 상태 또는 연결/타임아웃 예외 종류를 보존한다.
- 429에 유효한 Retry-After가 없으면 추측한 짧은 간격으로 재시도하지 않고 원인과 안내를 반환한다.
- Retry-After의 초 단위 및 HTTP-date 형식을 처리한다.
- 대기 시간이 60초를 초과하면 오래 막아 두지 않고 서버가 제공한 대기 시간을 오류에 남긴다.
- Agent 1은 `arxiv_rate_limited` 오류 코드와 검색 이전 실패 여부를 기록한다.
- 오류에는 URL의 사용자명/비밀번호/query credential이나 응답 body를 넣지 않는다.
- 다운로드 15초/API 3초 간격 정책은 유지하며, 다른 endpoint로 우회하거나 기존 자료를 새 검색 성공으로 대체하지 않는다.

새 코드에서 같은 종류의 429가 발생하면 `failed / 0편`은 유지되고, 실패 사유가 HTTP 429 및 arxiv_rate_limited로 명시된다. **코드 수정으로 외부 요청 제한이 해제됐다고 주장하지 않는다.** 제한 관측 이후 실제 arXiv 요청을 반복하지 않았다.

## 테스트

초기 관련 테스트: **37 passed (1.20초)** (`arxiv-retry-unit.xml`). 429 무조건 재시도 중지, Retry-After 준수/날짜 파싱, 장시간 대기 반환, HTTP 상태 보존·credential 제외, Agent 오류 매핑 및 기존 Retrieval 회귀를 검증했다.

전체 회귀 결과: **104 passed, 2 deselected, 1 warning (36.06초)** — `arxiv-retry-all-unit.xml`. 기존 SDK의 Starlette deprecated 상수 경고 1건이며 실패는 없다. Mock 기반이며 실제 새 검색 성공과 구분한다. 이번 진단 후 실제 3편 수집 성공은 확인하지 못했다.

## 사용자가 할 일

1. 새 검색 명령의 연속 재실행을 멈추고, 시간을 둔 뒤 한 번 다시 실행한다. Retry-After가 없었으므로 복구 시간을 보장할 수 없다.
2. 다시 실행할 명령은 기존과 같다:

```powershell
.\.runtime\python.exe -m group3.cli --topic "multi agent large language models" --target 3 --minimum 3 --task-id meeting-retrieval --result data/meeting-retrieval.json
```

3. 성공 여부는 `status=completed` 및 `selected_count=3`으로 확인한다. 또 failed이면 실패 JSON을 공유하면 된다. API Key는 다시 만들거나 공유할 필요가 없다.
4. 미팅에서 Agent 2와 Writer 시연은 기존 8편 자료를 사용해 계속 진행할 수 있다. 새 검색은 성공했을 때만 실시간 수집 성공으로 설명한다.
