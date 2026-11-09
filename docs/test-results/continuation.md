# 4~7단계 실행 결과

실행일: 2026-11-04 (Asia/Seoul). Windows x64 / Python 3.12.10. 전체 패키지 버전은 `requirements.lock.txt`.

## 단계별 보고

| 단계 | 구현 | 실행한 검증 | 남은 항목 |
|---|---|---|---|
| 4. Agent 2 | DOI/arXiv 정규화, 전이 매칭·충돌 방지, 불확실 후보 보존, 선정 논문별 중복 제거 집계, 공통 문헌 순위 | Mock/단위 테스트, 기존 실제 3편 저장 자료 및 신규 실제 8편 참고문헌 분석, 독립 CLI·A2A 호출 | 추출 서지 필드가 부족한 문헌의 재현율 개선, 최종 동률/매칭 정책 팀 협의 |
| 5. Agent 4 | 임시 Reader/Connections/Evidence 계약, 근거 검증, Markdown 비교표·각 섹션·Evidence Map, Groq planner 및 extractive 모드, Coverage 1회 ledger | Mock Groq 및 위조 입력 거부, 희소 예시/상충 fixture/재작성·재시작·동시 제한 테스트, 실제 원문 발췌 예시로 `.md` 작성 | 실제 Groq Key 없음 → 실호출 미실행. 실제 그룹 2 출력 및 Supervisor 의미 검증 미연동 |
| 6. A2A | 독립 3개 서비스, SDK Agent Card, JSON-RPC 태스크·artifact, 오류/타임아웃 및 부족 상태 | ASGI 컴포넌트 테스트, 실제 Uvicorn 3개 loopback HTTP, 실제 arXiv 기본 8/7 수집 → Agent 2 → 예시 Writer → revision 1 | 최종 SDK·프로토콜/상태 계약, 인증·공유 배포·취소/중단 복구 팀 협의 |
| 7. 문서 | README 설치·환경변수·독립 실행·A2A 요청/응답·시험 결과·한계, 예시 JSON/Markdown, 설계 변경 이유 | CLI 및 실제 파일 확인, 환경 의존성 검사 | 미완성 외부 통합은 아래와 같이 명시 |

## 오프라인 테스트

1. Agent 2/Writer 초기: **22 passed** (`analysis-unit.xml`).
2. A2A 초기: **10 passed, 1 warning** (`a2a.xml`).
3. 재작성 수정 입력/동시 예약 등 보강 후 전체: **65 passed, 1 deselected, 1 warning (3.95초)**.
4. 참고문헌 제목 위조 거부 및 A2A input-required 태스크 이어쓰기 추가, 테스트 환경 격리 후 최종: **67 passed, 2 deselected, 1 warning (4.72초)** (`all-unit.xml`).

포함한 항목: 1~3단계 기존 28개 회귀 테스트, 인용 문헌 수·2편 조건·중복·빈 결과·식별자 충돌·불확실 제목, Writer 실제 입력 근거 검증, 비교표 Markdown 연속 행, 상충 양측 근거, 누락 입력 보존, Groq 응답 허용 claim ID 제한, Coverage 1회/재시작/동시 호출/수정 입력, A2A discovery·message/send·tasks/get·input-required·오류·timeout.

외부 API는 이 테스트에서 호출하지 않는다. Groq 성공 경로는 Mock HTTP다. SDK가 새 Starlette에서 deprecated HTTP 상수를 사용하는 경고 1개가 있으며, 실패는 아니다. 경고를 숨기지 않았다.

Agent 4 독립 CLI도 실제 실행했다:

```powershell
.\.runtime\python.exe -m group3.analysis_cli write --input examples/group2-example.json --mode extractive --result docs/test-results/writer-cli.json
```

결과: `coverage_incomplete`, revision 0, `.md` 및 evidence 파일 생성. [writer-cli.json](writer-cli.json)에 결과가 있다. CLI help와 `pip check`도 정상 종료했다 (`No broken requirements found.`).

## 실제 로컬 A2A HTTP + arXiv

명령:

```powershell
.\.runtime\python.exe -m scripts.smoke_a2a --retrieve
```

실제 Uvicorn 서버 3개를 loopback 동적 포트에서 실행하고 `httpx`로 Agent Card 및 JSON-RPC를 호출했다. 스크립트 종료 시 서버 스레드를 종료했다. A2A SDK 버전은 개발용 `0.3.22`, 공개한 프로토콜은 `0.3.0`이며 팀 최종 버전으로 확정하지 않았다.

- Agent 1: 실제 arXiv 검색과 **기본 목표 8 / 최소 7 → 8편, completed**.
- 순차 다운로드 간격 15초 정책 적용. 모두 `arxiv_html`, 수집 warning 0 / failure 0. 실제 GROBID는 호출하지 않았다.
- Store task: `a2a-live`; run: `c2fec30f86ac4058a98d385e031e1149`.
- 원문 및 JSON: `data/papers/a2a-live/c2fec30f86ac4058a98d385e031e1149/`. 원문 8개 SHA-256 및 스키마 재확인 성공.
- Agent 2: 실제 8편의 **공통 참고문헌 3건**, 각 2편에서 인용. A2A completed.
- Agent 4: 원문 발췌 기반 `example_fixture`, **extractive** 모드. 보고서 생성 성공. 누락 분석 입력 23개를 `coverage_incomplete`로 남겼고 A2A input-required.
- Coverage 피드백 후 revision 1 생성 성공. 없는 연구 공백/분석 근거를 채우지 않아 상태는 여전히 coverage_incomplete다. 이를 검증 통과 보고서로 표현하지 않는다.
- 전체 응답 및 보고서: [a2a-loopback.json](a2a-loopback.json).
- 검토용 샘플: [report.md](../../examples/report.md), [예시 입력](../../examples/group2-example.json). 이 예시는 실제 그룹 2의 분석 산출물이 아니다.

### 실제 수집 논문

| arXiv | 제목 | 섹션 | 참고문헌 |
|---|---|---:|---:|
| [2609.38327v2](https://arxiv.org/abs/2609.38327v2) | Absorbing State Phase Transitions in Multi-Agent Search | 15 | 59 |
| [2609.29509v1](https://arxiv.org/abs/2609.29509v1) | Delay-of-Gratification as a Multi-Agent Survival Micro-benchmark for Long-Horizon LLMs: Social Exposure, Personas, and Tool Use Budgets | 11 | 40 |
| [2607.01425v2](https://arxiv.org/abs/2607.01425v2) | Agent4cs: A Multi-agent System for Code Summarization in Large Hierarchical Codebases | 16 | 56 |
| [2512.13930v1](https://arxiv.org/abs/2512.13930v1) | Hierarchical Multi-agent Large Language Model Reasoning for Autonomous Functional Materials Discovery | 16 | 58 |
| [2512.06196v1](https://arxiv.org/abs/2512.06196v1) | ARCANE: A Multi-Agent Framework for Interpretable and Configurable Alignment | 16 | 48 |
| [2511.10687v3](https://arxiv.org/abs/2511.10687v3) | Who Gets the Reward & Who Gets the Blame? Evaluation-Aligned Training Signals for Multi-LLM Agents | 9 | 71 |
| [2510.26352v2](https://arxiv.org/abs/2510.26352v2) | The Geometry of Dialogue: Graphing Language Models to Reveal Synergistic Teams for Multi-Agent Collaboration | 16 | 34 |
| [2511.05528v1](https://arxiv.org/abs/2511.05528v1) | SMAGDi: Socratic Multi Agent Interaction Graph Distillation for Efficient High Accuracy Reasoning | 18 | 22 |

표의 개수는 실제 파서 추출 수다. 수식·표 무손실 복원, 주제 의미적 관련성 및 서지 메타데이터 전수 정확성을 검증한 것은 아니다.

### 공통 참고문헌

| 식별자 | 인용한 선정 논문 | 서로 다른 논문 수 |
|---|---|---:|
| arxiv:2308.08155 | arxiv:2510.26352, arxiv:2609.38327 | 2 |
| arxiv:2407.21783 | arxiv:2510.26352, arxiv:2511.05528 | 2 |
| arxiv:2503.19786 | arxiv:2510.26352, arxiv:2607.01425 | 2 |

각 reference occurrence와 원문 위치는 `a2a-loopback.json`의 references에 저장했다. 해당 공통 문헌을 별도로 다운로드하거나 분석한 것은 아니다. 제목을 확인할 수 없으면 원문 서지 문자열을 쓰며 새 제목을 생성하지 않았다.

기존 실제 3편 분석은 [real-common-references.json](real-common-references.json)에 있으며 공통 0건이다. 이는 추출 자료와 보수적 매칭 기준의 결과로, 실제 공통 인용이 전혀 없다는 판정은 아니다.

## 실행하지 않은 외부 통합

- **Groq 실호출**: `GROQ_API_KEY` 미설정. Mock HTTP만 통과. 별도 `RUN_GROQ_LIVE=1` 테스트를 실제 실행해 **1 skipped**를 확인했다 (`groq-live.xml`, 0.47초). API 요청은 하지 않았다. 키를 코드/로그에 저장하지 않았다.
- **실제 PDF/GROBID**: 서버 미기동. HTML 성공으로 실제 대체 경로를 사용하지 않았다. 기존 Mock TEI 테스트와 구분한다.
- **실제 그룹 2 Reader/Connections 및 그룹 1 Supervisor**: 제공/연동되지 않았다. 생성 예시는 `example_fixture`로 명시하며 없는 데이터셋·성능 수치·연구 공백·상충 분석을 만들지 않는다.
- **최종 사실 검증/PASS/LLM Judge**: 미실행. `evidence_verified`는 항상 false이며 구조·quote 검증만 수행했다.

협의 목록과 구현 변경 이유는 [설계 문서](../continuation_plan.md)에 있다.
