# GitHub 공유 범위

담당 산출물은 Agent 1 Retrieval, Agent 2 Common References, Agent 4 Writer다. group3/a2a 및 group3/integration은 독립 시험과 임시 계약 확인을 위한 보조 코드이며 다른 그룹의 서버/Reader/Supervisor 구현을 완료했다는 의미가 아니다.

공유 대상은 group3/, tests/, scripts/의 Python 소스, docs/의 Markdown과 docs/contracts/ 스키마, examples/ 예시, 설치·설정 파일이다. 예시의 개인 PC 경로는 공유 복사본에서 상대 경로로 바꾼다. 상세 실행 JSON/XML과 다운로드 원문은 올리지 않고 테스트 요약만 공유한다.

.env, API Key, .runtime/, .venv/, data/, 캐시, SQLite, Python 설치 파일, 개인 이어서 메모는 제외한다. .env.example의 GROQ_API_KEY는 빈 값이어야 한다.

공유 브랜치는 group3/agents-initial-share다. main에 바로 병합하지 않고 PR에서 코드·팀 인터페이스·미완성 요구를 검토한다. 실제 실행 기록은 147개 오프라인 테스트 통과, 실제 새 논문 3편 수집, 실제 Groq 생성·재작성 성공이며 예시 입력과 Supervisor 검증 대기 상태를 구분한다. 원래 PC의 실행 데이터는 공유하지 않으므로 기존 run ID를 사용하는 연동 명령은 새 환경에서 먼저 수집해 새 ID로 교체해야 한다.

Future Work의 미팅 요구와 미완성 항목은 meeting_future_work.md를 참고한다.

공유 복사본은 총 100개 파일, 약 1.1MB이다. 개인 PC 경로를 상대 경로로 치환한 복사본 자체에서 오프라인 테스트를 실행해 147 passed, 2 deselected, 외부 SDK 폐기 경고 1건을 확인했다(약 37초). 이번 공유 작업에서 외부 Groq/arXiv 실제 연동 테스트를 다시 실행하지는 않았다. 이전 실제 실행과 공유 복사본의 오프라인 검증을 구분한다.
