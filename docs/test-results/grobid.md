# 실제 PDF → GROBID → TEI 검증

실행일: **2026-11-05 (Asia/Seoul)**. UTC 기록은 2026-11-04T16:09:08.765504+00:00이다. Windows x64 / Python 3.12.10.

## 이번 단계에서 한 일

- 실제 Groq Key 및 그룹 1/2 서비스 주소는 여전히 설정되어 있지 않음을 확인했다. 새 실제 그룹 2 출력 파일도 없다.
- Docker 명령이 없고 WSL도 설치되어 있지 않아 로컬 GROBID 서버는 기동하지 못했다. 시스템 소프트웨어를 새로 설치하지 않았다.
- GROBID 공식 프로젝트의 공개 데모를 확인하고 공개 arXiv PDF **한 편**으로 실제 API 검증을 수행했다.
- HTML 기본 경로에 추가로 명시적 PDF 우선 설정을 구현했다. 시험을 위해 존재하지 않는 HTML URL이나 가짜 HTML 실패를 만들지 않았다.
- 실제 생성된 PDF/TEI 자료를 ZIP으로 옮기고 로컬 A2A Agent 2/Writer가 읽을 수 있음을 확인했다.

공식 근거: [GROBID 프로젝트의 데모 안내](https://github.com/grobidOrg), [GROBID REST API](https://grobid.readthedocs.io/en/latest/Grobid-service/). 공개 데모는 CRF 모델 기반이며 사용량 제한이 있다. 운영 서버 배치를 대신하지 않는다.

## 실제 외부 실행

실행 명령:

```powershell
.\.runtime\python.exe -m group3.integration.grobid_probe --task-id a2a-live --run-id c2fec30f86ac4058a98d385e031e1149 --paper-id arxiv:2510.26352 --grobid-url https://grobidorg-grobid.hf.space
```

| 항목 | 실제 결과 |
|---|---|
| 논문 | The Geometry of Dialogue: Graphing Language Models to Reveal Synergistic Teams for Multi-Agent Collaboration |
| 원문 | [arXiv 2510.26352v2 PDF](https://arxiv.org/pdf/2510.26352v2) |
| 서버 | grobidorg-grobid.hf.space, GROBID 0.9.1 |
| 상태 조회 | /api/isalive → HTTP 200 true, /api/version → 0.9.1 |
| 처리 | PDF 다운로드 → 실제 multipart POST /api/processFulltextDocument → TEI 파싱 → JSON/Paper Store 저장 |
| POST 횟수 | **1회**, 재시도 0회 |
| PDF | 2,222,195 bytes, `%PDF-` signature 및 SHA-256 일치 |
| TEI | 92,851 bytes |
| 추출 섹션 | 18개 |
| 추출 참고문헌 | 34개, 그중 title 필드 19개 |
| parse_method | grobid_pdf |
| 수집 상태 | completed, warning 0 / failure 0 |
| 저장 task/run | grobid-pdf-smoke / dc685beee9424e4297c68efafc1e1e41 |

원문 PDF/TEI/JSON은 `data/papers/grobid-pdf-smoke/dc685beee9424e4297c68efafc1e1e41/`에 있다. 실행 기록은 [grobid-live.json](grobid-live.json). 기존 HTML 기반 8편의 파일/해시도 재확인했으며 기존 run은 수정하지 않았다.

**추출 수는 의미적 정확도 점수가 아니다.** CRF 결과에는 발표·채택 정보가 section head로 분류된 항목도 있다. TEI의 실제 제목과 본문은 보존했고, 모든 섹션 경계·참고문헌 서지정보가 정확하다고 판정하지 않았다. 기존 HTML의 해당 논문은 16개 섹션/34개 참고문헌이며, 파서별 섹션 경계 차이를 임의로 동일시하지 않았다. 참고문헌 수가 같다는 사실만으로 동일 문헌 집합이라고 주장하지 않는다.

## 실제 생성 자료의 후속 호환성

다음 명령은 **저장된 실제 PDF/TEI**를 재사용하며 외부 API를 추가로 호출하지 않았다:

```powershell
python -m scripts.verify_handoff --task-id grobid-pdf-smoke --run-id dc685beee9424e4297c68efafc1e1e41 --example-output data/grobid-handoff/group2-example.json --result docs/test-results/grobid-handoff.json
```

- PDF와 TEI를 ZIP export/import하여 다른 로컬 경로로 옮긴 뒤 파일/해시 검증 성공.
- 실제 로컬 Uvicorn/A2A HTTP로 Agent 2 호출 성공. 선정 논문이 한 편이므로 공통 참고문헌은 정상적으로 **0건**.
- 실제 PDF 섹션의 발췌로 만든 example_fixture를 Writer에 전달해 `.md` 생성 성공.
- 데이터셋/연결/연구 공백 입력 **3개**는 부족 상태 그대로 보존. Writer coverage_incomplete, A2A input-required, evidence_verified=false.
- 실제 그룹 2/Supervisor나 Groq를 호출한 것은 아니다.

기록은 [grobid-handoff.json](grobid-handoff.json)에 있다. 기존 8편용 예시 입력은 덮어쓰지 않았다.

## 테스트

PDF 우선 성공, PDF 실패→HTML 대체, HTML 대체를 PDF 성공으로 오인하지 않음, liveness 실패, GROBID 503, 실제 POST 재시도 0회, 미선정 논문·부적절한 endpoint URL 거부 테스트를 추가했다.

- 신규 테스트: **11 passed (31.02초)** — `grobid-probe-unit.xml`.
- 전체 회귀 테스트: **95 passed, 2 deselected, 1 warning (35.52초)** — `grobid-all-unit.xml`. 기존 SDK의 Starlette deprecated 상수 경고 1개이며 실패는 없다. 이 테스트는 Mock이며 위 실제 POST와 구분한다. 대체 경로 테스트에서도 15초 다운로드 간격을 적용했다.

## 아직 실행하지 못한 부분

- Groq: Key 미설정으로 실호출 미실행. 기존 Mock 검증만 있다.
- 그룹 1/2 실제 서비스/출력: 주소·데이터 미제공으로 통합 미실행.
- 로컬/운영 GROBID 배치 및 DL 모델 평가: 미실행. 공개 CRF 데모 한 편 검증과 구분한다.
- 최종 의미적 Evidence/PASS/LLM Judge: 미실행. 생성 예시는 검증된 연구 보고서가 아니다.
