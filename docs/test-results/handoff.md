# 통합 전달 단계 검증

환경: 2026-11-04, Windows x64 / Python 3.12.10. 앞선 4~7단계 이후 실제 그룹 연결을 준비하기 위한 작업이다.

## 구현 및 결과

| 항목 | 구현/검증 | 남은 사항 |
|---|---|---|
| 공통 계약 배포 | JSON Schema 9개 생성; 각 계약에 provisional 표시 | 그룹 1/2 최종 필드·버전 합의 |
| Paper Store 이동 | 원문+구조화 자료 ZIP export/import, 상대 경로·수신측 실제 경로 재설정, 해시/manifest 검증 | 실제 다른 OS/팀 장비 전송 미실행. 공유 저장소 기술 미확정 |
| 그룹 2 입력 조립 | 저장된 논문/근거 확인 후 Reader·Connections 출력과 Agent 2 결과로 WriterRequest 생성 | 실제 그룹 2 데이터 미제공; 발췌 예시로만 검증 |
| 준비 상태 점검 | Groq 키 존재, 실제 GROBID liveness, endpoint 설정, 원문 파일/해시, 예시/실제 출처 표시 | 실제 Groq/그룹 서비스는 연결하지 않음 |

설계 이유: 기존 Paper Store JSON의 Windows 절대 경로는 다른 컴퓨터에서 바로 읽을 수 없다. 공용 저장소 제품을 임의 확정하는 대신, 경로를 재설정할 수 있는 파일 전달 어댑터와 교체 가능한 임시 입력 envelope를 추가했다. Supervisor/Reader 기능을 그룹 3에서 새로 구현하지 않았다.

## 자동 테스트

최종 실행:

```powershell
.\.runtime\python.exe -m pytest -m "not live" -q -p no:cacheprovider --junitxml=docs/test-results/handoff-all-unit.xml
```

**84 passed, 2 deselected, 1 warning (5.89초)**. 기존 67개에 새 테스트 17개를 추가했다. warning은 SDK의 Starlette deprecated HTTP 상수 사용이며 기존과 같다. 외부 API 테스트 2개는 이번에 선택하지 않았다.

새 검증은 다음을 포함한다:

- 다른 저장 루트로 ZIP roundtrip 후 파일/섹션/해시 보존.
- 원문 변조, manifest 불일치, checksum 불일치 거부.
- 경로 이탈·예상하지 않은 ZIP 항목·중복 항목·Windows 대소문자 충돌 거부.
- 기존 ZIP/run 덮어쓰기 거부.
- 그룹 2 원문 없는 quote·미선정 paper·다른 run 거부, 출처 provenance 유지.
- Schema의 필수 paper/run/evidence 계약 확인.
- 준비 점검 중 Groq/그룹 endpoint를 호출하지 않고, 키/URL token이 출력되지 않음.

개별 신규 테스트의 초기 결과는 `handoff-unit.xml`(16 passed), 보강 후 전체 결과는 `handoff-all-unit.xml`에 있다.

## 실제 저장 자료 + 로컬 A2A HTTP

실행한 명령:

```powershell
.\.runtime\python.exe -m scripts.verify_handoff --task-id a2a-live --run-id c2fec30f86ac4058a98d385e031e1149
```

결과:

- 기존에 실제 arXiv에서 수집한 **8편**을 ZIP으로 내보냈다. 새 논문이나 분석 결과를 생성하지 않았다.
- 다른 로컬 저장 경로로 가져와 **8편 원문 SHA-256·스키마·섹션** 검증에 성공했다.
- 옮긴 저장소를 실제 Uvicorn/A2A HTTP로 읽어 공통 참고문헌 **3건**이 유지됨을 확인했다.
- 실제 원문 발췌 기반 `example_fixture` Group2Output을 조립하고 Writer로 전달해 `.md` 생성에 성공했다.
- 예시 입력의 미충족 영역 **23개**를 유지했다. Writer는 `coverage_incomplete`, A2A는 `input-required`, evidence_verified=false다.
- 검증 스크립트 종료 후 서버를 종료했다. 새 arXiv/Groq API 및 실제 다른 그룹 서비스는 호출하지 않았다.

실행 기록: [handoff-loopback.json](handoff-loopback.json). 검증 ZIP은 `data/handoff-runs/77c99b3fac8e49389e95cda0819e86a8/paper-store.zip`에 있다. 같은 PC의 경로 이동 및 loopback HTTP 검증이며 실제 팀 장비 간 통합 성공을 의미하지 않는다.

CLI도 각각 실행했다:

```powershell
python -m group3.integration.cli export-store --task-id a2a-live --run-id c2fec30f86ac4058a98d385e031e1149 --output data/handoff-cli/paper-store.zip
python -m group3.integration.cli import-store --input data/handoff-cli/paper-store.zip --store-root data/handoff-cli/imported-store
python -m group3.integration.cli assemble-writer --input examples/group2-output.example.json --store-root data/handoff-cli/imported-store --topic "Multi-agent large language models" --output data/handoff-cli/writer-ready.json
```

모두 정상 종료. 8편·example_fixture·missing_coverage 23개·evidence_verified=false를 확인했다. 실제 원문이 포함된 ZIP을 외부로 자동 전송하지 않았다.

## 실제 준비 상태 — 외부 연동 미완료

[integration-readiness.json](integration-readiness.json)을 생성한 점검 결과:

| 대상 | 실제 확인 |
|---|---|
| Groq | API Key 미설정. 실호출하지 않음 |
| GROBID | `http://localhost:8070/api/isalive` 실제 접속 거부. 실제 PDF 파싱 미검증 |
| Supervisor/Reader/Connections | endpoint 설정 없음. 호출하지 않음 |
| Paper Store | 실제 8편 파일·해시 검증 성공 |
| 그룹 2 입력 | 실제 분석 결과 없음. example_fixture만 존재 |
| 보고서 입력 coverage | 23개 영역 부족. 임의 보완하지 않음 |

`ready_for_external_attempt=false`, `all_checks_verified=false`. 이 비정상 준비 상태는 성공으로 바꾸어 기록하지 않았다. 실제 연결을 진행하려면 환경변수의 Groq Key, 작동하는 GROBID 주소, 그룹 1/2 계약·서비스 주소 또는 실제 그룹 2 출력 JSON이 필요하다. Key는 환경변수에 설정하며 문서/코드/채팅에 값을 남길 필요가 없다.
