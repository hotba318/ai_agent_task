# 실제 Groq 연동 검증

실행일: 2026-11-05 (Asia/Seoul). 실제 응답 이후 기록 시각은 `2026-11-05T01:30:29.367970+00:00`(UTC), 한국 시각 10:30:29다.

사용자가 `.env`에 설정한 Key를 애플리케이션 설정에서 읽어 실제 API를 호출했다. 키 값은 출력·결과 파일·코드에 저장하지 않았다. `.env`는 기존 `.gitignore`의 제외 대상이다.

## 실제 테스트

```powershell
$env:RUN_GROQ_LIVE='1'
.\.runtime\python.exe -m pytest tests/test_groq_live.py -q -p no:cacheprovider --junitxml=docs/test-results/groq-live.xml
Remove-Item Env:RUN_GROQ_LIVE
```

결과: **1 passed (2.52초)**. Mock이 아닌 실제 `api.groq.com` 호출이다.

| 확인 항목 | 결과 |
|---|---|
| Key 로딩 | 성공 (값 출력 안 함) |
| Writer 설정 | groq |
| 실제 모델 | openai/gpt-oss-20b |
| Structured Outputs | 실제 응답 JSON 검증 성공 |
| 근거 제약 | 제공된 claim ID의 허용 집합·보존 조건 검사 통과 |
| Markdown 생성 | 성공 |
| evidence.json 및 result.json | 저장 성공 |
| 예시 Markdown | examples/groq-report.md |
| 보고서 ID | 9182966975d6434f8d7bdacd780f680a |
| 보고서 상태 | coverage_incomplete |
| 미충족 입력 | 23개 |
| 사실 검증 | evidence_verified=false, Supervisor 검증 대기 |

실행 기록: [groq-live-result.json](groq-live-result.json), [JUnit 결과](groq-live.xml).

보고서: [groq-report.md](../../examples/groq-report.md). 원본 보고서와 증거 연결 파일은 `data/groq-live-reports/9182966975d6434f8d7bdacd780f680a/revision-0/`에 있다. 라이브 테스트가 임시 디렉터리를 사용하던 부분을 변경해 실행 후에도 결과를 검토할 수 있도록 보존했다.

## 성공의 범위

실제 Groq 인증·모델 호출·claim 계획·Markdown 생성이 성공했다. 입력은 기존 실제 논문 8편의 원문 발췌로 만든 **example_fixture**다. Groq는 이미 근거와 연결된 claim ID를 정렬하며 텍스트는 제공된 claim에서 렌더링한다. 실제 그룹 2의 분석을 새로 수행한 것은 아니다.

존재하지 않는 데이터셋/성능 수치/연결 관계/연구 공백을 보완하지 않았으며, 빈 분석 입력 23개가 남아 `coverage_incomplete`를 반환했다. 생성 성공과 연구 내용의 사실 검증/PASS는 구분한다.

## 회귀 테스트

사용자의 `.env`가 groq 모드인 상태에서도 오프라인 테스트가 실제 API를 호출하지 않도록 기존 격리를 유지했다. 결과는 **95 passed, 2 deselected, 1 warning (36.80초)**이며 `groq-enabled-unit.xml`에 기록했다. warning은 기존 SDK의 Starlette deprecated 상수 사용이다. 실제 Groq 성공 1건과 Mock/오프라인 테스트를 별도로 집계한다.

저장한 실행 JSON, JUnit XML, 예시 Markdown에 API Key 값이 포함되지 않았음을 추가 확인했다.

## 남은 외부 의존성

- 실제 그룹 2 Reader/Connections 출력 JSON 또는 서비스 주소·합의된 계약.
- 그룹 1 Supervisor의 실제 연동 및 의미적 Evidence/PASS 검증.
- 운영 GROBID 서버 배치. 공개 데모로 실제 PDF 한 편 처리는 이미 성공했다.

Groq Key와 gpt-oss-20b 실호출은 더 이상 미검증 항목이 아니다. 다른 모델, 대량/장시간 운용, 사용량 정책을 검증한 것은 아니다.
