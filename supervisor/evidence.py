import asyncio
from dataclasses import dataclass
import chromadb
from group3.common.schemas import PaperDocument

MAX_PASSAGE_WORDS = 150

@dataclass
class Passage:
    """A short piece of one section: what the evidence store searches."""

    passage_id: str
    paper_id: str
    section_id: str
    text: str

def split_into_passages(paper: PaperDocument) -> list[Passage]:
    """Split every section of a paper at its blank lines, and long paragraphs into 150-word pieces."""
    passages = []
    for section in paper.sections:
        number = 0
        for paragraph in section.text.split('\n\n'):
            words = paragraph.split()
            for start in range(0, len(words), MAX_PASSAGE_WORDS):
                piece = ' '.join(words[start:start + MAX_PASSAGE_WORDS])
                passages.append(Passage(f'{paper.paper_id}#{section.section_id}#{number}', paper.paper_id, section.section_id, piece))
                number += 1
    return passages

class EvidenceStore:
    """One run's passages in an in-memory Chroma collection, searchable by meaning."""

    def __init__(self, task_id: str) -> None:
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(name=task_id)

    async def add_papers(self, papers: list[PaperDocument]) -> int:
        """Store every passage of the papers and return how many were stored."""
        passages = [passage for paper in papers for passage in split_into_passages(paper)]
        await asyncio.to_thread(
            self.collection.add,
            ids=[passage.passage_id for passage in passages],
            documents=[passage.text for passage in passages],
            metadatas=[{'paper_id': passage.paper_id, 'section_id': passage.section_id} for passage in passages],
        )
        return len(passages)

    async def search(self, text: str, paper_id: str, limit: int) -> list[Passage]:
        """The passages of one paper closest in meaning to the text, closest first."""
        found = await asyncio.to_thread(
            self.collection.query,
            query_texts=[text],
            n_results=limit,
            where={'paper_id': paper_id},
        )
        return [
            Passage(passage_id, metadata['paper_id'], metadata['section_id'], document)
            for passage_id, metadata, document in zip(found['ids'][0], found['metadatas'][0], found['documents'][0])
        ]

    def delete(self) -> None:
        """Remove this run's collection; otherwise it stays in memory until the program ends."""
        self.client.delete_collection(name=self.collection.name)
    