# 임시 공통 JSON Schema

`python -m group3.integration.cli schemas --output docs/contracts`로 Pydantic 계약을 내보냈다. 팀 최종 계약이 아니며, 각 파일에도 provisional 주석을 남긴다.

| 소비자 | 계약 |
|---|---|
| Supervisor → Agent 1 | [RetrievalRequest](RetrievalRequest.schema.json) |
| Agent 1 → Supervisor | [RetrievalResult](RetrievalResult.schema.json) |
| Paper Store → Reader/Agent 2 | [PaperDocument](PaperDocument.schema.json) |
| Supervisor → Agent 2 | [ReferencesRequest](ReferencesRequest.schema.json) |
| Agent 2 → Writer | [ReferencesResult](ReferencesResult.schema.json) |
| Reader/Connections → 통합 조립기 | [Group2Output](Group2Output.schema.json) |
| 조립기 → Writer | [WriterRequest](WriterRequest.schema.json) |
| Supervisor → Writer 재작성 | [RevisionRequest](RevisionRequest.schema.json) |
| Writer → Supervisor | [WriterResult](WriterResult.schema.json) |

Schema 적합성은 원문 근거 존재 또는 사실성을 보증하지 않는다. 조립기/Writer의 원문 연결 검증을 통과해야 하며, 의미적 검증은 Supervisor/Reader 책임이다. SDK/protocol 버전과 이 도메인 스키마 버전은 서로 다르다.
