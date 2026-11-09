# 1~3단계 검증 기록

실행일: 2026-11-04 (Asia/Seoul). 환경: Windows x64, 공식 Python 3.12.10 embeddable, 패키지 버전은 `requirements.lock.txt`.

## 단계별 결과

| 단계 | 구현 내용 | 검증 | 미완성/미확정 |
|---|---|---|---|
| 1. 문서 분석 | 확정/원본/권장/팀 협의 분리, 요구사항 추적표 및 계획 | 첨부 MD 전체 읽기와 코드 대응 정리 | PDF/PPTX 원본은 첨부되지 않아 직접 대조하지 않음; 팀 협의 목록 미확정 |
| 2. 프로젝트·공통 스키마 | 설정, 요청·결과·논문·섹션·참고문헌 모델, Protocol 및 로컬 저장 어댑터 | Pydantic 입력 거부, 환경변수, ID, 저장·조회 테스트 | 그룹 1/2와 최종 계약 합의 전, Agent 2/4 출력 계약은 추정 확정하지 않음 |
| 3. Agent 1 | 실제 검색, 관련성·최신성 정렬, 중복 제거, 순차 다운로드·재시도, HTML/TEI 파싱, 원문·JSON·manifest 저장 | 오프라인 테스트 + 실제 arXiv 3편 수집 성공 | 실제 GROBID 및 기본 7~8편 전체 수집 미실행 |

## 오프라인/Mock

`python -m pytest -m "not live" -q --junitxml=docs/test-results/unit.xml`

초기 실행: **24 passed, 1 deselected (1.02초)**. 실패 경로 테스트 추가 후 최종 실행: **28 passed, 1 deselected (0.90초)** (`-p no:cacheprovider`). 기계 판독 결과는 `unit.xml`에 기록했다. 네트워크 없는 단위/컴포넌트 테스트이며, 가상 논문은 fixture로만 사용한다.

검증 범위: 기본값/환경변수, 잘못된 요청, 3·5·8·12편 설정, 7편 허용/6편 부족, 관련성 우선/최신성 차순위/중복, 버전 및 구형 arXiv ID, HTML 중첩 섹션, TEI 참고문헌, 다운로드 간격/재시도/404/타임아웃, 실패 후보 대체, 재실행 격리, manifest 저장/조회, API 오류, GROBID 미접속 및 참고문헌 빈 목록 경고.

**PDF→GROBID 성공 경로는 Mock HTTP/TEI 테스트다. 실제 PDF와 실제 GROBID 서버로 성공시킨 결과가 아니다.**

## 실제 arXiv 연동

`RUN_LIVE=1 python -m pytest tests/test_live.py -q --junitxml=docs/test-results/live.xml`

결과: **1 passed, 1 warning (31.85초)**. 이 한 테스트가 실제 논문 3편을 수집하고 원문 존재·섹션·참고문헌을 검증한다. 경고는 권한이 다른 실행에서 pytest 캐시 디렉터리를 쓰지 못한 `PytestCacheWarning`이며 수집 실패는 없다. 이후 오프라인 검증은 캐시 플러그인 비활성화로 기록한다. 기본 테스트는 `RUN_LIVE` 없으면 이 테스트를 skip한다.

- 주제: `multi agent large language models`
- 목표/최소: `3 / 3`
- 결과: `completed`, 선정 3편, 경고 0, 수집 실패 0
- 실행 ID: `7f3defc438f34e49b66be59ae822bd24`
- 결과: [live-result.json](live-result.json)
- 원문 및 구조화 저장: `data/papers/live-smoke/7f3defc438f34e49b66be59ae822bd24/`

| 실제 논문 | arXiv ID/원문 | 파싱 | 섹션 | 참고문헌 |
|---|---|---|---:|---:|
| Agent4cs: A Multi-agent System for Code Summarization in Large Hierarchical Codebases | [2607.01425v2](https://arxiv.org/abs/2607.01425v2) | arxiv_html | 16 | 56 |
| Hierarchical Multi-agent Large Language Model Reasoning for Autonomous Functional Materials Discovery | [2512.13930v1](https://arxiv.org/abs/2512.13930v1) | arxiv_html | 16 | 58 |
| ARCANE: A Multi-Agent Framework for Interpretable and Configurable Alignment | [2512.06196v1](https://arxiv.org/abs/2512.06196v1) | arxiv_html | 16 | 48 |

개수는 파서가 실제 원문에서 추출한 섹션·참고문헌 항목 수다. 논문 내용에 대한 Reader 분석·사실 검증 결과를 의미하지 않는다. 추출 참고문헌의 서지정보 정확성 및 모든 표/수식의 무손실 복원을 검증한 것은 아니다. 원문과 SHA-256을 보존하며, 섹션 제목·참고문헌 일부를 추가로 확인했다.

## 실행하지 않은 것

- 기본 목표 8편/최소 7편의 **실제** 전체 수집 (수량 로직은 Mock 통과).
- 실제 PDF/GROBID 서버 연동. Docker 명령 없음; 실제 수집은 모두 HTML 성공으로 PDF 경로를 사용하지 않음.
- Agent 2·Agent 4, Groq API, 최종 Markdown 연구 보고서, A2A/Supervisor, 그룹 2 Reader/Connections, LLM Judge.

API Key 부족으로 Agent 1을 Mock으로 대체한 것은 아니다. 실제 arXiv 호출에는 키가 필요하지 않으며, 네트워크 제한 밖에서 실행 승인을 받아 실제 검색·다운로드했다.

추가 실행 확인: `python -m group3.cli --help` 정상 종료, `python -m pip check` → `No broken requirements found.`
