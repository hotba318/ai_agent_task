# Group 3: Multi-Agent 논문 분석 시스템

담당 개발 범위는 **Agent 1 Retrieval, Agent 2 Common References, Agent 4 Writer**입니다. A2A와 integration은 독립 실행 및 임시 팀 계약을 확인하기 위한 보조 코드입니다. 다른 그룹의 Reader 또는 Supervisor 서버를 구현한 것은 아닙니다.

## 설치

Python 3.12 이상을 사용합니다. Windows PowerShell에서 다음을 실행하세요.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
Copy-Item .env.example .env
```

Groq를 사용하려면 `.env`의 `GROQ_API_KEY`에 키를 입력합니다. 실제 키와 `.env`는 Git에 올리지 않습니다. 키가 없는 `extractive` 모드는 입력 claim을 그대로 렌더링하는 비생성 모드입니다.

## 에이전트별 동작

| 에이전트 | 역할 |
|---|---|
| Agent 1 Retrieval | 논문 검색·수집·구조화·저장. 결과를 관찰하고 제한된 범위에서 검색 확대·질의 변경·중단을 결정합니다. |
| Agent 2 Common References | 두 편 이상이 인용한 공통 문헌을 식별하고, 서로 다른 인용 논문 수를 집계합니다. 식별 충돌과 누락은 검토 대상으로 표시합니다. |
| Agent 4 Writer | 원문 근거로 문장을 생성하고 검사·모델 검토·보류를 거쳐 Markdown 보고서를 작성합니다. Coverage 재작성은 최대 한 번입니다. |

논문 선정은 관련성 우선, 최신성 차순위입니다. 기본 목표는 8편이며 최소 7편입니다. 설정으로 논문 수를 변경할 수 있습니다.

## 독립 실행

아래 명령은 가상환경의 Python을 사용합니다.

```powershell
# Agent 1: 첫 실행은 실제 논문 3편으로 확인합니다.
.\.venv\Scripts\python.exe -m group3.cli --topic "multi agent large language models" --target 3 --minimum 3 --task-id demo3 --result data/retrieval.json

# Agent 2: 위 결과에 기록된 run_id를 사용합니다.
$retrieval = Get-Content data/retrieval.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -m group3.analysis_cli references --task-id demo3 --run-id $retrieval.run_id --output data/references.json

# Agent 4: 키 없는 비생성 모드입니다.
.\.venv\Scripts\python.exe -m group3.analysis_cli write --input examples/group2-example.json --mode extractive --result data/writer.json

# Agent 4: Groq를 사용하는 생성·검토 모드입니다.
.\.venv\Scripts\python.exe -m group3.analysis_cli write --input examples/group2-example.json --mode groq --result data/writer-groq.json
```

Agent 1이 성공적으로 수집을 완료했는지 확인한 뒤 Agent 2를 실행합니다. Groq 호출에는 API 사용량이 발생하며, 제공자의 토큰 한도에 따라 수분이 걸릴 수 있습니다.

Writer 예시는 실제 원문 발췌를 사용하는 인터페이스 시험용 입력으로, 실제 그룹 2 분석 결과가 아닙니다. 예시의 원문 경로는 상대 경로로 정리했으며 다운로드 원문 자체는 포함하지 않습니다. 파일 저장소를 읽는 기능은 새로운 Retrieval 실행이 필요합니다.

## 테스트와 검증 상태

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live" -q
```

- 업로드용 복사본에서 오프라인 테스트 **147개 통과**, 실제 연동 테스트 2개 제외.
- 이전 로컬 실제 실행에서 새 논문 3편 수집 및 Groq 생성·Coverage 재작성 성공.
- 업로드 작업에서는 외부 API 테스트를 다시 실행하지 않았습니다.
- 외부 A2A SDK의 폐기 예정 상수 경고 1건이 있으며 테스트 실패는 아닙니다.

`coverage_incomplete`는 입력이나 근거가 부족한 부분 보고서 상태입니다. 최종 사실 검증은 Supervisor 대기 상태이며, 같은 모델의 별도 근거 검토가 최종 사실 판정을 의미하지는 않습니다.

## 미팅 요구와 남은 작업

보고서에는 각 논문의 내용, 한계, **Future Work**, 공통 참고문헌을 식별할 수 있어야 합니다. Future Work는 논문 저자가 제시한 향후 연구로, 여러 논문을 비교해 도출하는 Research Gaps와 구분합니다.

논문별 Future Work 전용 입력, 논문별 한계·공통 참고문헌 표시 강화, 실제 그룹 2 및 Supervisor 통합은 남은 작업입니다. 계약 v0.1은 팀 합의 전의 임시 인터페이스입니다.

## 문서

- [코드 구조와 에이전트 동작](docs/agent_evolution.md)
- [검증 결과와 Mock·실제 연동 구분](docs/test-results/agent-evolution.md)
- [Future Work 미팅 요구와 미완성 항목](docs/meeting_future_work.md)
- [공유 범위와 제외 파일](docs/github_sharing.md)
- [팀 협의용 스키마](docs/contracts/README.md)
- [개발 가이드](Group3_MultiAgent_Development_Guide.md)

과거 실행 기록에 등장하는 로컬 run ID와 상세 로그 파일은 이 저장소에 포함하지 않았습니다. 새 환경에서 재실행할 때는 새로 생성된 ID를 사용하세요.
