# 4~7단계 계획과 임시 계약

기준은 첨부 가이드의 확정/원본 요구다. 기존 1~3단계 이후 사용자가 다음 단계 진행을 요청하여 Agent 2, Agent 4, A2A 단독 서비스, README 갱신을 구현한다. 팀 협의는 코드 구현과 구분하며 최종 확정하지 않는다.

## Agent 2

- DOI는 대소문자·URL prefix·percent encoding 정규화, arXiv는 버전 제거로 비교한다.
- DOI/arXiv가 양쪽에 연결된 경우 전이 통합한다. 두 DOI 또는 arXiv ID가 충돌하는 컴포넌트는 통합하지 않는다.
- ID가 없으면 정규화 제목+전체 저자 목록+연도 일치 또는 충분히 긴 전체 인용 원문 일치로 보수적으로 통합한다. 표기가 비슷하지만 증거 부족이면 `possible_duplicates`에 남긴다.
- 순위는 서로 다른 선정 논문 수 내림차순, 동률은 canonical ID 사전순인 **임시 정책**이다. 전체 누적 인용 횟수는 사용하지 않는다.
- 실제 저장된 3편 및 이번 실제 A2A 수집 자료를 대상으로 분석한다. 0건은 정상 결과이며 추출 누락과 실제 공통 인용 부재를 구분한다.

## Agent 4

- 임시 Reader/Connections/Evidence 스키마는 `common/analysis_schemas.py`에 두며, 그룹 2 계약이 오면 어댑터에서 변환한다. 실제 그룹 2 산출물은 제공되지 않았다.
- 예시 생성기는 실제 Agent 1 원문 섹션을 발췌해 `example_fixture`로 표시한다. 분석 결과·데이터셋·성능 수치·연구 공백·상충점을 추측하지 않는다. 누락된 필드는 빈 목록 및 `coverage_incomplete`로 남긴다.
- **권장 구현 변경**: 자유 서술 LLM 초안 대신 Groq gpt-oss가 이미 근거와 연결된 claim ID의 순서를 구조화 JSON으로 반환하도록 제한한다. 텍스트는 입력 claim에서 렌더링한다. 이유는 모델이 존재하지 않는 분석/인용을 추가할 경로를 줄이기 위해서다. 모든 claim ID의 보존 및 허용 집합 일치를 검사한다. 향후 의미적 종합 확장은 Supervisor 검증과 함께 협의한다.
- Groq 미설정 시 조용히 대체하지 않는다. 기본 `extractive`는 명시된 오프라인 모드이고, `groq` 모드는 키가 없으면 실패한다. Groq의 실제 호출 여부와 Mock 테스트를 구분한다.
- quote가 해당 paper/section의 입력 텍스트에 존재하는지 검사하고 claim/evidence/reference 식별자를 추적한다. 구조 검증은 주장의 의미적 진실성을 보장하지 않는다. 어떤 결과도 `evidence_verified=true` 또는 Supervisor PASS로 표시하지 않는다.
- Markdown에는 비교표, 공통 참고문헌, 연결·상충, 연구 공백, 한계, 원문 링크 및 evidence map을 렌더링한다. 상충 입력은 최소 두 논문과 두 claim을 요구하며 양쪽 근거를 보존한다.
- Coverage는 로컬 Writer 전용 SQLite ledger에서 report_id당 재작성 **최대 1회**를 원자적으로 예약한다. 재시작에도 유지한다. Supervisor SQLite와 다른 저장소다. revision 0/1 결과를 함께 보존한다. 재시도 중 실패해도 허용 횟수를 소비한다.
- revision은 저장된 원 입력을 사용한다. 선택적으로 새 Group 2 입력을 받되 task/topic/provenance/원문 논문 목록이 같아야 하고 모든 근거를 재검증한다. 재작성 후 입력 부족은 `coverage_incomplete`와 누락 목록으로 반환한다. 이 도메인 상태와 이후 조치는 **팀 협의 전 임시 정책**이다.

## A2A

- A2A Python SDK `0.3.22`, 프로토콜 `0.3.0`을 **개발 검증용으로 고정**했다. 공식 최신 1.0과 API 차이가 있어 무심코 업그레이드하지 않고 교체 가능한 `group3/a2a/server.py`에 격리한다. 최종 버전은 그룹 1과 협의한다.
- Agent별 독립 프로세스, Agent Card discovery, JSON-RPC `message/send`, `tasks/get`, JSON DataPart 및 Markdown TextPart artifact를 제공한다. SSE/push는 광고하지 않는다.
- envelope: `{ "operation": "retrieve|references|write|revise", "payload": { ... } }`. task_id는 업무 ID, A2A task.id는 SDK가 발급하는 별도 전송 ID다.
- 정상 산출물은 A2A completed. 부족/coverage_incomplete는 input-required, 도메인 failed/예외/타임아웃은 failed. **부족 상태 매핑은 임시 정책**이다. Writer completed는 파일 생성 완료이지 Supervisor 검증 통과가 아니다.
- 작업 취소는 TaskNotCancelable로 명시적으로 거절한다. 그룹 1과 취소/중단 복구 책임을 협의한다. SDK task store는 메모리이며 서버 재시작 시 task 조회 정보는 사라진다. Writer revision ledger와 파일 산출물은 남는다.
- 기본 loopback 바인딩이다. 공유 배포의 인증/권한/공유 저장소/공용 rate limiter는 최종 배포 전 협의한다. 단일 Retrieval 서비스 내 작업은 직렬화하고 실행 사이에도 15초 간격을 둔다.

## 검증 구분

1. 오프라인: Agent 2 매칭/집계, Writer 스키마·근거·출력·재작성, Groq Mock, A2A ASGI 라우팅/태스크·오류/타임아웃.
2. 실제 로컬 HTTP: Uvicorn 3개와 SDK JSON-RPC를 loopback socket으로 호출한다.
3. 실제 외부: arXiv 기본 8/7 수집을 A2A로 호출. PDF/GROBID를 사용한 경우만 실제 성공 여부를 기록한다.
4. 제외: 실제 Group 2/Supervisor/LLM Judge와 Groq 실호출(키 없으면 미실행). 전체 실제 종단 간 시스템 검증이라고 주장하지 않는다.

공식 참고: [SDK v0.3.22 소스](https://github.com/a2aproject/a2a-python/tree/v0.3.22), [A2A 1.0 서버 문서](https://a2a-protocol.org/v1.0.0/tutorials/python/5-start-server/), [Groq Structured Outputs](https://console.groq.com/docs/structured-outputs).
