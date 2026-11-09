# 새 논문 검색 장애 조사 및 실제 수집 복구

실행일: 2026-11-05 (Asia/Seoul). 앞선 “사용자가 반복 실행해서 제한되었을 수 있다”는 설명은 근거가 부족했다. 사용자 반복 실행을 원인으로 확정하지 않는다.

## 원인 조사

실제 응답과 환경을 확인했다. [진단 JSON](arxiv-origin-diagnostic.json):

- DNS: export.arxiv.org → Fastly. DNS 확인과 HTTPS/TLS 연결 성공.
- HTTP_PROXY / HTTPS_PROXY / ALL_PROXY 등 환경변수: 설정 없음. 이 사실이 모든 네트워크 중간 장비의 부재를 증명하는 것은 아니다.
- HTTP 응답: **429**, body **`Rate exceeded.`**(14 bytes).
- 서버: **Google Frontend**. Via에는 Google 및 Varnish, X-Cache는 MISS 3개.
- Retry-After 없음.
- arXiv 공식 상태 페이지는 export/search Up을 표시했으나 개별 API 응답 성공을 보장하지는 않았다.

[arXiv API 담당자의 동일 오류 설명](https://groups.google.com/a/arxiv.org/g/api/c/pNB3lnxf4mQ)에는 정상적인 소량 사용에서도 서버 전체 용량 때문에 해당 응답이 생길 수 있다고 되어 있다. 관측한 응답은 이 서버 용량 문제 유형과 일치한다. 현재 서버 내부 상태를 직접 확인한 것은 아니므로 근본 원인을 내부 로그 수준으로 확정했다고 주장하지 않는다. 사용자 API Key·명령 문법·프록시 환경변수 문제를 뒷받침하는 증거는 없었다.

## 해결 방식

**arXiv 서버 자체를 복구한 것이 아니라, 그 장애 때문에 새 논문 수집 전체가 중단되는 문제를 해결했다.**

1. 기본 `auto`는 기존 arXiv API를 먼저 한 번 호출한다.
2. 429/5xx/연결 오류/타임아웃이면 **별도 서비스인 DataCite 공식 공개 API**에서 실제 arXiv DOI 등록 자료를 검색한다. IP/프록시 교체, bot 위장, arXiv API 제한 우회는 사용하지 않는다.
3. DOI prefix `10.48550`, arXiv DOI 구조, publisher=arXiv, landing page ID 일치를 확인한다.
4. 버전과 v1/현재 버전의 **Submitted** 날짜가 확인되는 문헌만 사용한다. DataCite 등록일·생성일을 arXiv 최초 제출일로 바꾸어 쓰지 않는다. 수정일은 최신 버전의 제출일을 사용하며 DataCite 메타데이터 수정 시각과 구분한다.
5. 기존 관련성 그룹 우선 → 최초 제출일 차순위 및 중복 제거 로직을 적용한다.
6. HTML/PDF 원문은 실제 arXiv에서 새로 다운로드한다. 15초 다운로드 간격을 유지한다.
7. 각 논문에 `metadata_source`와 `metadata_url`, 실행 결과 warning에 대체 검색 사실을 기록한다.

DataCite는 API Key가 필요 없는 독립적인 DOI 메타데이터 서비스다. [공식 Public API 안내](https://support.datacite.org/docs/rest-api), [검색·필터·관련성 정렬](https://support.datacite.org/docs/api-queries). arXiv API와 검색 색인/순위/수록 범위가 동일하다는 보장은 없다. 두 서비스가 모두 실패하면 failed를 반환하며 과거 수집 결과를 새 검색 성공으로 반환하지 않는다.

권장 구현 변경 이유: arXiv API 의존성을 제거하는 대신 기존 경로를 보존하고 가용성 장애에만 독립 메타데이터 소스를 추가했다. 잘못된 입력·파서 오류를 감추기 위한 자동 대체는 하지 않는다. `--search-provider arxiv`로 기존 API만 쓰도록 지정할 수 있다. 메타데이터 출처 optional 필드 2개는 임시 스키마 v0.1에 추가했으며 팀 통합 시 함께 확인해야 한다.

## 실제 새 수집 성공

실행한 명령:

```powershell
.\.runtime\python.exe -m group3.cli --topic "multi agent large language models" --target 3 --minimum 3 --task-id retrieval-repaired --result data/retrieval-repaired.json
```

결과: **completed, requested_count=3, selected_count=3, failures=[]**. arXiv API 429 후 DataCite 실시간 검색 사용 경고 1개. 애플리케이션의 저장된 검색 결과나 기존 8편을 사용하지 않았다.

| 새로 수집한 실제 논문 | 최초 제출일 | 섹션 | 참고문헌 |
|---|---|---:|---:|
| [2601.11327v2 — Can Small Agents Collaborate to Beat a Single Large Language Model?](https://arxiv.org/abs/2601.11327v2) | 2026-01-16 | 19 | 23 |
| [2511.19405v3 — Learning Robust Social Strategies with Large Language Models](https://arxiv.org/abs/2511.19405v3) | 2025-11-24 | 15 | 53 |
| [2509.11656v3 — MALLM: Multi-Agent Large Language Models Framework](https://arxiv.org/abs/2509.11656v3) | 2025-09-15 | 20 | 55 |

모두 arxiv_html이며 원문 SHA-256·파일 존재·구조화 스키마를 검증했다. 추출 수는 파서 산출 수이며 의미적 분석 정확도를 뜻하지 않는다. 각 DataCite 메타데이터 URL과 최초/최신 제출일도 저장했다.

- 검증 결과: [retrieval-repaired.json](retrieval-repaired.json).
- 실제 저장: `data/papers/retrieval-repaired/e699beaa990248a09802732df38f6afa/`.
- 이전 실패 기록은 덮어쓰지 않았다.

## 테스트

새로운 DataCite/가용성 대체 및 HTTP 정책 관련 테스트: **27 passed (0.73초)** — `resilient-search-unit.xml`. DOI/원문 ID 불일치, 제출일/버전 누락, 생성일 오용 방지, malformed record 제외, 주 API 우선, 가용성 오류에만 대체, 두 서비스 실패 시 원인 구분을 검증했다.

전체 회귀: **122 passed, 2 deselected, 1 warning (35.76초)** — `resilient-search-all-unit.xml`. 경고는 기존 SDK의 Starlette deprecated 상수 사용이며 실패는 없다. 공통 JSON Schema도 재생성했다. Mock 테스트와 위 실제 새 3편 수집은 구분한다. API 색인 차이·DataCite 데이터 누락 가능성 때문에 모든 검색 주제/논문 수의 가용성을 보장하지 않는다.

## 사용자 실행 방법

**추가 설정 없이 이전 명령을 그대로 실행할 수 있다.** 기본 search_provider=auto다.

```powershell
.\.runtime\python.exe -m group3.cli --topic "multi agent large language models" --target 3 --minimum 3 --task-id meeting-retrieval --result data/meeting-retrieval.json
```

성공 판단은 `status=completed`, `selected_count=3`이다. DataCite 사용 warning은 새 수집 실패가 아니라 검색 출처 안내다. 기존 arXiv API 자체만 시험하려면 `--search-provider arxiv`, DataCite를 직접 쓰려면 `--search-provider datacite`를 추가한다.
