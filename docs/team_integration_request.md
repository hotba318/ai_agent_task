# 그룹 1/2 실제 통합 요청서 — 그대로 전달할 문구와 사용자 작업 순서

현재 그룹 3의 Agent 1/2/4, 실제 arXiv 8편 수집, 공개 PDF/GROBID, Groq, 로컬 A2A 서비스 호출은 검증했다. 실제 그룹 1/2 서비스·분석 데이터는 아직 받지 않았다. 아래 계약은 **임시 v0.1**이며, 그룹 1/2의 기존 구현에 맞춰 어댑터로 조정할 수 있다. 최종 규격을 이 문서만으로 확정하지 않는다.

## 사용자님이 지금 할 일

1. 그룹 2 담당자에게 이 요청서와 `data/handoff-cli/paper-store.zip`, `docs/templates/group2-output.template.json`을 전달한다. 아래 그룹 2 요청 문구를 복사해서 보내면 된다. API Key는 이 전달 작업에 필요 없다.
2. 그룹 2가 분석 JSON을 주면 프로젝트의 `data/incoming/` 폴더에 `group2-output.real.json`이라는 이름으로 저장한다. 파일명은 달라도 된다. 받은 내용을 예시 데이터에서 추측해 직접 채울 필요는 없다.
3. 이 대화에 **“그룹 2 파일을 data/incoming/group2-output.real.json에 저장했어”**라고 알려준다. 그러면 저장소 대조·근거 검증 → 실제 Groq 보고서 → 오류/누락 확인 순으로 진행한다.
4. 그룹 1 담당자에게 아래 그룹 1 요청 문구를 보내고, 회신받은 SDK/protocol 버전·서비스 주소·호출 예시를 이 대화에 전달한다.

그룹 2가 JSON 대신 서비스 주소만 제공해도 괜찮다. 그 경우 주소뿐 아니라 요청/응답 JSON 예시와 필요한 인증 방식도 받아오면 된다. Key/토큰 값은 코드나 이 문서에 적지 않고 환경변수로 설정한다.

## 그룹 2 담당자에게 복사해 보낼 문구

> 그룹 3의 Retrieval/Common References/Writer 구현과 실제 Groq 호출은 완료했습니다. 첨부한 ZIP의 실제 선정 논문 8편을 Reader 및 Connections로 분석해 주세요.
>
> 먼저 1편으로 입출력 호환성을 확인해도 되고, 최종 통합은 8편 전체 기준입니다. 첨부한 JSON template는 아직 분석이 없는 입력 양식이며, 논문/섹션 ID는 ZIP의 bundle.json에 있는 값을 사용해 주세요.
>
> 반환 형식은 아래 임시 Group2Output 계약을 제안합니다. 기존에 다른 스키마가 구현되어 있다면 변경을 강제하지 않겠습니다. 기존 출력 JSON 예시와 필드 설명을 보내주시면 그룹 3에서 변환하겠습니다.
>
> 각 분석 문장은 claim_id/text/evidence_ids를 포함하고, evidence에는 paper_id/section_id/원문 quote가 필요합니다. quote는 해당 섹션 텍스트에서 그대로 찾을 수 있어야 합니다. 방법론/데이터셋/결과/한계, 논문 간 공통점·차이·실제 상충점과 각 출처를 보내주세요. 제공할 근거가 없는 항목은 빈 목록으로 두거나 부재 사유를 함께 설명해 주세요. 상충점이 없으면 만들어낼 필요는 없습니다.
>
> 실제 분석을 채운 파일의 data_provenance는 group2로 표기해 주세요. 연구 공백을 제공할 수 있다면 출처와 함께 전달하고, 없으면 빈 목록으로 남겨 주세요. 최종 형식과 해당 없음/미입력 구분은 함께 협의하겠습니다.

### 읽을 자료

- ZIP: `paper-store.zip`.
- 내부 `bundle.json`의 `papers[]`: 메타데이터, 원문 링크, `sections[]`, `references[]`.
- `sections[]`: 실제 `section_id`, `title`, `text`, `source_locator`, `source_url`.
- `documents/`: 공개 논문의 실제 HTML 원문. 논문 분석·quote는 동일 run의 섹션 자료와 연결한다.
- task_id: `a2a-live`.
- run_id: `c2fec30f86ac4058a98d385e031e1149`.
- 논문 ID 8개와 빈 Reader 양식은 별도 `group2-output.template.json`에 이미 채워 두었다. **이 양식은 실제 분석 결과가 아니며 provenance=example_fixture**다.

### 임시 JSON 계약

최상위 필드:

```text
schema_version: "0.1"
task_id: 위의 task_id
run_id: 위의 run_id
paper_ids: 분석한 선정 논문 ID 목록 (빈 배열이면 해당 run 전체)
reader_results: ReaderResult 목록
evidence: Evidence 목록
connections: Connection 목록
research_gaps: Claim 목록
data_provenance: 실제 분석은 "group2", 양식/시험 자료는 "example_fixture"
```

하위 구조:

```text
ReaderResult:
  paper_id: 선정 논문 ID
  overview: Claim[]
  methods: Claim[]
  datasets: Claim[]
  results: Claim[]
  limitations: Claim[]

Claim:
  claim_id: 전체 입력에서 중복되지 않는 문자열
  text: 근거에 기반한 분석 문장
  evidence_ids: 연결되는 evidence_id 문자열 목록 (1개 이상)

Evidence:
  evidence_id: 전체 입력에서 중복되지 않는 문자열
  paper_id: 선정 논문 ID
  section_id: 해당 run에 실제 존재하는 section_id
  quote: 해당 section.text 안에 그대로 존재하는 비어 있지 않은 문자열

Connection:
  connection_id: 문자열
  kind: "similarity" | "difference" | "conflict"
  claims: Claim[] (conflict는 서로 다른 논문 2편 이상의 양측 claim과 근거 필요)
```

각 Reader의 claim은 그 Reader의 paper_id에 해당하는 evidence를 사용한다. 공통 참고문헌 집계는 그룹 3 Agent 2가 수행하므로 별도 횟수를 새로 입력할 필요는 없다. 전체 기계 판독 스키마는 그룹 3 프로젝트의 `docs/contracts/Group2Output.schema.json`이다.

## 그룹 1 담당자에게 복사해 보낼 문구

> 그룹 3의 Agent 1 Retrieval, Agent 2 Common References, Agent 4 Writer를 독립 A2A 서비스로 구현했습니다. 개발용 고정 버전은 a2a-sdk 0.3.22 / protocol 0.3.0이며, 최종 팀 규격은 미확정입니다. 그룹 1의 SDK/protocol 버전, Supervisor 서비스 주소, 요청/응답 예시를 보내주세요.
>
> 현재 Agent Card는 /.well-known/agent-card.json, JSON-RPC는 / 경로입니다. message/send와 tasks/get, result.json DataPart 및 Writer report.md TextPart를 검증했습니다. 실제 로컬 A2A Writer에서 실제 Groq gpt-oss-20b 호출까지 성공했습니다.
>
> domain task_id와 SDK task.id는 별도입니다. 부분 수집/coverage_incomplete의 input-required 매핑, Coverage 1회 이후 처리, Evidence 최대 2회 Reader 재검증 및 PASS/CONFLICT 판단 책임을 합의하고 싶습니다. Writer 산출물은 evidence_verified=false이며 완료 응답을 Supervisor PASS로 취급하지 않습니다.
>
> 호출/상태 규격이 다르면 해당 부분을 어댑터로 바꾸겠습니다. 현재 출력 예시와 Group 2 출력 입력 방식도 함께 맞춰 주세요.

그룹 1의 테스트 클라이언트와 같은 PC에서 서버를 실행할 경우 PowerShell 창 3개를 각각 열고 아래 명령을 한 개씩 실행한다. 주소/공유 네트워크가 정해지기 전에는 기본 loopback 설정을 사용한다.

```powershell
# PowerShell 창마다 먼저 실행
Set-Location -LiteralPath '.'

# 첫 번째 창
.\.runtime\python.exe -m group3.a2a.server --agent retrieval --port 8001

# 두 번째 창
.\.runtime\python.exe -m group3.a2a.server --agent references --port 8002

# 세 번째 창
.\.runtime\python.exe -m group3.a2a.server --agent writer --port 8004
```

각 서버는 창을 열어 둔 동안 실행되며, 종료하려면 해당 창에서 `Ctrl+C`를 누른다. 다른 PC의 팀원은 이 PC의 127.0.0.1 주소에 접근할 수 없으므로, 실제 배치 주소와 접근 방식은 그룹 1과 함께 정한다. 제가 검증용으로 띄운 서버는 테스트 종료 후 종료했다.

## 파일을 받은 뒤의 처리

사용자님은 파일을 저장하고 경로만 알려주면 된다. 제가 수행할 명령은 다음과 같다:

```powershell
.\.runtime\python.exe -m group3.integration.cli assemble-writer --input data/incoming/group2-output.real.json --topic "Multi-agent large language models" --output data/writer-ready.real.json
.\.runtime\python.exe -m group3.analysis_cli write --input data/writer-ready.real.json --mode groq --result data/writer-result.real.json
```

이 두 명령은 **실제 파일을 받기 전에는 실행하지 않았다.** 스키마가 다르면 임의로 원문/분석 내용을 채우지 않고 매핑할 필드와 누락된 근거를 확인한다. 그룹 1/2로 메시지를 자동 전송하지 않았으며, 위 문구는 사용자님이 검토해 전달할 초안이다.
