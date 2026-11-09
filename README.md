# 그룹 3 — Agent 1 · 2 · 4

이 문서는 그룹 3 담당 개발분인 **Agent 1 Retrieval, Agent 2 Common References, Agent 4 Writer**를 설명합니다.

## 담당 기능

| 에이전트 | 구현 내용 |
|---|---|
| Agent 1 Retrieval | 관련 논문 검색, 관련성·최신성 순위화, 원문 다운로드, 섹션·참고문헌 구조화, 저장. 수집 결과에 따라 제한된 검색 재계획 또는 중단. |
| Agent 2 Common References | 선정 논문 중 두 편 이상이 인용한 문헌 식별, 서로 다른 인용 논문 수 집계, 불확실한 식별과 누락에 대한 검토 요청. |
| Agent 4 Writer | 제공된 분석·원문 근거를 사용한 문장 생성, 인용·수치 검사와 모델 근거 검토, Markdown 출력, 피드백에 따른 최대 한 번의 Coverage 재작성. |

기본 논문 선정 목표는 8편, 최소 7편이며 설정으로 변경할 수 있습니다. 선정 기준은 관련성 우선, 최신성 차순위입니다.

## 파일 구성

```text
group3/
  agents/retrieval/    Agent 1
  agents/references/   Agent 2
  agents/writer/       Agent 4
  common/             세 에이전트의 스키마·설정·도구 인터페이스
  cli.py              Agent 1 독립 실행
  analysis_cli.py     Agent 2·4 독립 실행
  services.py         독립 실행을 위한 구성
tests/                담당 에이전트 테스트
examples/             Writer 시험 입력과 Markdown 보고서 예시
scripts/              시험 입력 생성 및 스키마 내보내기
docs/contracts/       담당 에이전트 입출력 스키마
```

## 설치와 환경 설정

Python 3.12 이상을 사용합니다. Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
Copy-Item .env.example .env
```

Groq 사용 시 `.env`의 `GROQ_API_KEY`를 설정합니다. 실제 키는 코드나 Git에 저장하지 않습니다. Writer의 `extractive` 모드는 모델 없이 입력 claim을 렌더링하며, `groq` 모드는 모델로 문장을 생성하고 검토합니다.

## 독립 실행

```powershell
# Agent 1: 첫 수집은 실제 논문 3편으로 확인합니다.
.\.venv\Scripts\python.exe -m group3.cli --topic "multi agent large language models" --target 3 --minimum 3 --task-id demo3 --result data/retrieval.json

# Agent 1이 completed인지 확인한 뒤 해당 run_id로 Agent 2를 실행합니다.
$retrieval = Get-Content data/retrieval.json -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe -m group3.analysis_cli references --task-id demo3 --run-id $retrieval.run_id --output data/references.json

# Agent 4: 예시 입력으로 API Key 없이 출력 구조를 확인합니다.
.\.venv\Scripts\python.exe -m group3.analysis_cli write --input examples/writer-input.json --mode extractive --result data/writer.json

# Agent 4: 실제 Groq 생성·검토를 실행합니다.
.\.venv\Scripts\python.exe -m group3.analysis_cli write --input examples/writer-input.json --mode groq --result data/writer-groq.json
```

Groq 실행에는 API 사용량이 발생하며 제공자 한도에 따라 수분 걸릴 수 있습니다. Writer 입력 예시는 실제 원문 발췌로 구성한 시험용 자료이며 완성된 분석 결과가 아닙니다. 다운로드 원문 파일은 포함하지 않았으므로 저장된 파일을 직접 읽는 기능은 새 수집이 필요합니다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live" -q
.\.venv\Scripts\python.exe -m scripts.export_group3_schemas
```

담당 범위로 정리한 코드에서 오프라인 테스트 **106개 통과**, 실제 연동 테스트 2개 제외를 확인했습니다. 외부 서비스 테스트는 기본 실행에서 제외합니다. 테스트의 Mock 응답은 실제 논문 분석 결과로 사용하지 않습니다. 생성 문장이 근거 검토를 통과해도 최종 사실 검증 완료를 의미하지 않습니다. `coverage_incomplete`는 필수 입력 또는 작성 근거가 부족함을 나타냅니다.

## 보완할 항목

- 논문별 Future Work 전용 입력과 Writer 반영. Future Work는 저자가 제시한 향후 연구이며 종합 Research Gaps와 구분합니다.
- 보고서에서 논문별 한계와 공통 참고문헌 목록을 더 명확하게 표시.
- 입력·출력 스키마의 팀 합의 반영. 현재 v0.1은 임시 계약입니다.

공통 참고문헌 식별·집계는 Agent 2가, 보고서의 논문별 표시는 Agent 4가 담당합니다. [검증 기록](docs/group3-status.md)에 현재 실행 결과와 제한을 정리합니다.
