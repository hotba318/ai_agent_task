# 그룹 간 실제 통합을 위한 전달 계약 (임시 v0.1)

사용자의 다음 단계 요청에 따라, 기존 Agent 1/2/4를 다른 컴퓨터·그룹과 연결하기 위한 데이터 전달과 입력 검증을 구현했다. 이 문서는 팀 합의서가 아니다. A2A SDK/프로토콜, 공용 저장소 기술, Reader/Connections 최종 출력 형식은 계속 협의 대상이다.

## 그룹 1에 전달할 것

- [독립 A2A 서비스 실행 및 요청 예](../README.md): 개발용 SDK 0.3.22 / protocol 0.3.0. 기본 주소는 8001 Retrieval, 8002 References, 8004 Writer.
- [JSON Schema 모음](contracts/README.md): Python 없이 필드/필수값을 확인할 수 있는 임시 계약 9개.
- 작업의 domain task_id와 SDK transport task.id를 구분한다. 부족/coverage_incomplete는 임시 input-required 정책이며, 최종 매핑은 그룹 1이 합의해야 한다.
- Writer의 needs_review/completed는 Supervisor PASS가 아니다. evidence_verified=false를 유지한다.

## 그룹 2에 전달할 것

`group3.integration.cli export-store`는 한 실행의 전체 선정 논문과 실제 HTML/PDF/TEI 원문을 ZIP으로 저장한다. 논문 ID, 버전이 포함된 원문 URL, section_id, XPath, 원문 텍스트, 참고문헌 및 SHA-256을 보존한다.

ZIP 내부 `bundle.json`의 논문 원문/파싱 파일 경로는 `documents/<filename>` 상대 경로다. 수신측 `import-store`는 실제 새 저장 위치로 경로와 manifest URI를 재설정한다. 원문 위치에 `store://` 같은 가상 URI를 사용하지 않는다. 파일 이전을 위한 개발용 어댑터이며 공용 저장소 제품을 확정한 것은 아니다.

예:

```powershell
# 송신 컴퓨터: 이미 수집한 실제 8편을 내보냄
python -m group3.integration.cli export-store --task-id a2a-live --run-id c2fec30f86ac4058a98d385e031e1149 --output data/transfer/papers.zip

# 수신 컴퓨터: ZIP을 복사해 온 뒤 새 저장 루트로 가져옴
python -m group3.integration.cli import-store --input data/transfer/papers.zip --store-root data/imported-papers
```

내보내기 전 원문 해시·실제 파일·manifest 일치를 검사한다. 가져오기 전에는 버전·경로·파일 목록·SHA-256·중복 항목·대소문자 충돌·심볼릭 링크·압축 해제 크기 상한(200 MiB)을 검사한다. `extractall()`은 쓰지 않는다. 기존 출력 ZIP이나 저장 run을 덮어쓰지 않는다. 임시 디렉터리에서 검증된 자료를 구성한 뒤 최종 위치로 옮긴다.

이 해시는 전송 중 손상 여부를 검사한다. 서명/송신자 인증이나 논문 내용의 사실성 보증은 아니다. 원문 배포·보관 정책은 전체 팀 협의가 필요하며 ZIP을 외부로 자동 전송하지 않는다.

## Reader/Connections 출력 → Writer

그룹 2는 `Group2Output` envelope에 아래 값을 제공할 수 있다:

```json
{
  "schema_version": "0.1",
  "task_id": "a2a-live",
  "run_id": "c2fec30f86ac4058a98d385e031e1149",
  "paper_ids": [],
  "reader_results": [],
  "evidence": [],
  "connections": [],
  "research_gaps": [],
  "data_provenance": "group2"
}
```

빈 paper_ids는 해당 실행의 전체 선정 논문을 뜻한다. 값이 있으면 manifest에 존재하는 논문만 선택한다. 위의 빈 분석 목록은 문법 설명용이며 완성 분석 결과가 아니다. 실제 quote와 claim 필드는 [Group2Output Schema](contracts/Group2Output.schema.json)에 정의한다. 실행 가능한 발췌 예시는 [group2-output.example.json](../examples/group2-output.example.json)이며 **실제 그룹 2의 분석 결과가 아닌 example_fixture**다.

```powershell
python -m group3.integration.cli assemble-writer --input examples/group2-output.example.json --store-root data/imported-papers --topic "Multi-agent large language models" --output data/writer-ready.json
python -m group3.analysis_cli write --input data/writer-ready.json --mode extractive --result data/report-result.json
```

조립기는 실제 Paper Store에서 논문을 읽고 파일 해시를 검사한다. 그룹 2 입력으로 논문 원문을 교체하지 않는다. Agent 2의 공통 참고문헌은 선정 논문에서 다시 계산한다. quote가 가리키는 paper/section/텍스트, claim→evidence, conflict 양측 출처를 검증한 후 WriterRequest를 만든다. 입력 부족 목록은 그대로 반환한다. 원문에 없는 quote나 미선정 paper ID는 거절한다. 사용자 입력의 의미적 함의는 별도의 Reader/Supervisor 검증 대상이다.

provenance=group2는 입력 제공자가 선언하는 출처이며 자동 인증이 아니다. example_fixture를 실제 분석으로 승격시키지 않는다. 원문 문서의 ID/섹션 식별자를 새로 만들어 채우지 않는다.

## 연동 준비 상태 확인

```powershell
python -m group3.integration.cli check --task-id a2a-live --run-id c2fec30f86ac4058a98d385e031e1149 --group2-input examples/group2-output.example.json --output data/readiness.json
```

- Groq: 키 존재 여부만 확인하며 실제 API를 호출하지 않는다. 키 값은 출력하지 않는다.
- GROBID: `/api/isalive`의 HTTP 200 및 plain-text true를 확인한다. liveness와 실제 PDF 파싱 성공을 구분한다. [공식 서비스 점검 문서](https://grobid.readthedocs.io/en/latest/Grobid-service/#service-checks)
- 그룹 1/2 endpoint: 환경변수 설정 여부만 확인한다. 프로토콜이 합의되지 않은 상태에서 임의 요청을 보내지 않는다.
- Paper Store: 선택 실행의 manifest, 실제 파일, SHA-256을 확인한다.
- 그룹 2 입력: 구조·원문 연결·coverage를 확인하고 example_fixture 여부를 유지한다.

`configured_unverified`는 연결 성공이 아니다. `ready_for_external_attempt`는 필수 설정/입력이 준비되어 실제 검증을 시도할 수 있다는 뜻이며, 외부 연동 성공 또는 사실 검증 PASS가 아니다. 준비가 부족하면 exit code 2를 반환한다. 키나 URL의 query/token, 외부 오류 body는 진단 기록에 넣지 않는다.

관련 환경변수는 `.env.example`의 주석에 있다. 현재 실제 endpoint가 없으므로 값을 추측해 채우지 않았다.

## 재현 검증

```powershell
python -m scripts.verify_handoff --task-id a2a-live --run-id c2fec30f86ac4058a98d385e031e1149
```

실제 저장된 8편을 ZIP으로 이전 → 다른 로컬 루트에서 재검증 → 예시 Group2Output을 조립 → 실제 Uvicorn/A2A HTTP로 Agent 2와 Writer를 호출한다. 새 arXiv 다운로드/Groq 호출/실제 다른 그룹 서비스 호출은 하지 않는다. 이는 같은 PC에서 저장 경로 이동을 검증한 결과이며, 다른 OS/실제 팀 장비에서 실행한 결과라고 주장하지 않는다.

실행 결과는 [통합 전달 검증 기록](test-results/handoff.md)에 있다.
