# 실제 A2A Writer → Groq → 결과 artifact 검증

실행일: 2026-11-05 (Asia/Seoul). 입력은 기존 실제 8편 원문 발췌 기반 example_fixture다. 실제 그룹 1/2 서비스는 호출하지 않았다.

```powershell
.\.runtime\python.exe -m scripts.verify_groq_a2a
```

실제 수행 범위:

1. 로컬 Uvicorn Writer A2A 서버를 loopback 동적 포트에서 기동.
2. 실제 HTTP로 Agent Card를 조회하고 protocol 0.3.0 확인.
3. JSON-RPC message/send → Writer 서비스 → **실제 Groq gpt-oss-20b** 호출.
4. result.json DataPart 및 report.md TextPart 수신.
5. 반환 Markdown artifact와 실제 저장 파일의 내용 일치 확인.
6. tasks/get으로 같은 태스크 상태 조회 확인.
7. 테스트 종료 시 서버 종료, Key가 결과 JSON에 포함되지 않았는지 확인 후 저장.

결과: **성공**. 보고서 ID는 `1cd0f4e232c74517b1b6796080bf1c09`다. 도메인 상태는 coverage_incomplete, A2A 상태는 input-required이며 입력 부족 23개를 그대로 반환했다. `evidence_verified=false`를 유지했다. Writer 모드가 groq가 아니거나 Key가 없으면 명시적으로 실패하고, extractive로 자동 대체하지 않는다.

- [실행 기록 JSON](groq-a2a-live.json)
- [반환 Markdown 샘플](../../examples/groq-a2a-report.md)
- 원본 Markdown/evidence/result: `data/reports/1cd0f4e232c74517b1b6796080bf1c09/revision-0/` (출력 루트는 설정에 따른다).

이 검증은 실제 Groq 단독 호출에 더해 실제 A2A 서비스 바인딩 경로를 확인한 것이다. Supervisor 구현 자체, 실제 그룹 2 분석 결과, 의미적 Evidence/PASS 검증이 완료된 것은 아니다. 기존 회귀 95개는 앞 단계에서 통과했고 이번에는 서비스 코드 변경 없이 새 명시적 라이브 검증 스크립트를 실행했다. SDK의 기존 Starlette deprecated 상수 경고 1건이 발생했다.

다음 사용자 작업은 [팀 통합 요청서](../team_integration_request.md)에 파일 위치와 전달 문구, 받아올 정보, 저장 방법까지 정리했다.
