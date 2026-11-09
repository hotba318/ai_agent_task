# Agent 1·2·4 발전 내용 (2026-11-09)

담당 범위는 계속 Agent 1 Retrieval, Agent 2 Common References, Agent 4 Writer다. A2A 어댑터·그룹 2 예시·연동 도구는 독립 실행과 계약 시험을 위한 보조 코드다. 다른 그룹의 Supervisor나 Reader를 구현했다고 간주하지 않는다.

## 기능 모듈에서 관찰·판단·행동 흐름으로

| Agent | 이번 변경 | 판단의 경계 |
|---|---|---|
| 1 | 수집 수·새 후보·파싱 실패를 관찰하고 후보 확대/질의 변경/중단을 결정한다. 새 후보를 원래 주제로 다시 순위화한다. | 기본 최대 3회, 설정 1~5회. 관련성 기준은 완화하지 않는다. 최소 확보·서비스 오류·예산 소진 시 중단한다. |
| 2 | 참고문헌 식별 강도·충돌·누락을 평가하고 결과 반환 또는 검토 요청을 결정한다. | 빈도 집계와 식별은 결정론적이다. 불확실한 문헌을 LLM 추측으로 합치지 않는다. |
| 4 | 근거를 읽고 문장을 생성 → 구조/인용/수치 검사 → 모델 근거 검토 → 보류/출력한다. Coverage 요청에는 이전 보고서와 피드백을 전달한다. | 구조 수정 요청 최대 1회. Supervisor Coverage 재작성은 보고서당 최대 1회이며 실패해도 소비된다. 최종 사실 검증은 별도다. |

모든 Agent에 LLM을 넣는 방식은 채택하지 않았다. 검색 부족의 다음 행동과 문헌 종합에는 모델 판단이 도움이 되지만, 참고문헌 개수와 명확한 식별자 일치는 코드로 검증하는 편이 재현 가능하기 때문이다. `[권장 구현]` 변경 이유는 이와 같다. `[확정]`의 관련성 우선, 설정 가능한 기본 8/최소 7편, 다운로드 간격, 근거 추적, Markdown 출력, 최대 1회 Coverage 재작성은 유지한다.

## 읽을 코드

- Agent 1: `group3/agents/retrieval/agent.py`, `planner.py` — 관찰/행동 반복, 규칙·Groq 교체 가능한 정책.
- Agent 2: `group3/agents/references/agent.py` — 품질 판단·검토 요청과 원래의 보수적 문헌 집계.
- Agent 4: `group3/agents/writer/agent.py`, `planner.py`, `draft.py` — 생성·검토·보류·재작성. `state.py`는 재작성 횟수의 영속 제한.
- 테스트: `tests/test_agent_upgrades.py`, `tests/test_synthesis_safety.py`.

`agent.py`는 실행 흐름을 조정하고 실제 작업은 도구 모듈에 맡긴다. 따라서 그 파일 하나에 모든 판단·프롬프트·파싱이 들어 있지는 않다. 무제한 자율 에이전트가 아니라 도구와 행동 범위가 정해진 역할별 에이전트다.

## 설정

키는 기존 `.env`의 `GROQ_API_KEY`를 사용한다. 코드나 발표 자료에 키를 넣지 않는다. 현재 설정된 키는 실제 호출로 확인했으므로 이번 작업을 위해 다시 설정할 필요는 없다.

```dotenv
GROUP3_RETRIEVAL_PLANNER_MODE=auto
GROUP3_MAX_SEARCH_ROUNDS=3
GROUP3_WRITER_MODE=groq
GROUP3_GROQ_MODEL=openai/gpt-oss-20b
```

검색 `auto`는 키가 있으면 부족 상황의 재계획에 Groq를 사용하고, 키가 없으면 규칙 정책을 사용한다. 처음부터 충분히 수집하면 모델을 호출하지 않는다. 모델 실패 시 규칙 정책으로 제한된 후속 행동을 결정하며 기록한다. Writer의 명시적인 `groq` 모드는 실패했다고 자동으로 extractive 성공을 반환하지 않는다.

모델 요청은 생성 최대 2회 및 문장 8개 단위 검토로 제한한다. 제공자가 알리는 토큰 잔량/초기화 시각과 짧은 Retry-After를 따르므로 실제 실행은 수분 걸릴 수 있다. 제한을 넘는 오류는 그대로 실패로 보고한다.

## 직접 보여주는 방법 (PowerShell)

먼저 프로젝트 폴더에서 실행한다.

```powershell
Set-Location -LiteralPath '.'

# 1. 새 논문 3편 검색·수집. 기본 운영은 target 8 / minimum 7.
.\.runtime\python.exe -m group3.cli --topic "multi agent large language models" --target 3 --minimum 3 --task-id evolution-demo --result data/evolution-retrieval.json
$retrieval = Get-Content data/evolution-retrieval.json -Raw | ConvertFrom-Json
Get-Content -LiteralPath $retrieval.decisions_path

# 2. 위 실행이 completed이면 해당 실행의 논문으로 문헌 분석.
.\.runtime\python.exe -m group3.analysis_cli references --task-id evolution-demo --run-id $retrieval.run_id --output data/evolution-references.json
$references = Get-Content data/evolution-references.json -Raw | ConvertFrom-Json
$references | Select-Object review_required,decisions

# 3. 그룹 2 예시로 Writer만 독립 실행 (유료 API 사용량 발생 가능).
.\.runtime\python.exe -m group3.analysis_cli write --input examples/group2-example.json --mode groq --result data/evolution-writer.json
$writer = Get-Content data/evolution-writer.json -Raw | ConvertFrom-Json
notepad $writer.markdown_path
Get-Content -LiteralPath $writer.decisions_path
Get-Content -LiteralPath $writer.review_path
```

Writer 예시는 실제 원문 발췌를 담은 인터페이스 시험 데이터다. 그룹 2가 분석을 완료한 결과가 아니므로 `coverage_incomplete`는 누락을 정확히 알린 결과다. `model_calls`는 실제 HTTP 시도 횟수이며 추론 품질 점수가 아니다. `support-review.json`은 같은 모델의 별도 호출로 얻은 보조 검토이므로 독립적인 사실 판정으로 해석하면 안 된다.

Coverage 재작성을 보려면 위 Writer 실행 후 다음을 실행한다. 기존 생성본이 있으므로 새 논문 다운로드는 하지 않는다.

```powershell
@{
  report_id = $writer.report_id
  feedback = @{
    missing_sections = @('introduction','comparison')
    missing_paper_ids = @()
    note = '원문 근거 범위를 명확히 하고 두 논문의 방법론 차이를 비교하세요. 없는 정보는 채우지 마세요.'
  }
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 data/evolution-revision.json
.\.runtime\python.exe -m group3.analysis_cli revise --input data/evolution-revision.json --mode groq --result data/evolution-revised.json
```

CLI는 PowerShell의 UTF-8 BOM도 허용한다. 재작성은 한 번만 허용되므로 반복 시 같은 보고서를 다시 쓰지 않는다.

## 미확정 사항과 남은 일

그룹 2의 실제 Reader/Connections/Gap 입력, 그룹 1 Supervisor의 Coverage/Evidence 판정, A2A 상태 매핑과 공유 저장소 계약은 여전히 팀 협의 대상이다. `review_required`, 결정 기록과 결과 경로는 교체 가능한 임시 v0.1 필드로 추가했다. 다른 그룹의 서비스를 대신 개발한 것은 아니다.

의미 기반 검색 평가, 한국어 검색어 번역, 장문 입력 분할, 서로 다른 모델/사람을 통한 근거 검토, 실제 여러 그룹 서버 간 통합은 완료하지 않았다. 현재의 모델 검토와 수치 포함 여부 검사만으로 허위 분석을 완전히 차단한다고 주장하지 않는다.

실행 증거와 Mock/실제 구분은 [검증 기록](test-results/agent-evolution.md)을 참고한다. 이전 `continuation_plan.md`와 `groq.md`의 claim 순서 계획 설명은 초기 구현 기록이며 현재 Groq Writer 동작은 이 문서를 따른다.
