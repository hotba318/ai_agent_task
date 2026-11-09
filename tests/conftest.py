from datetime import date

import pytest

from group3.common.schemas import PaperMetadata


@pytest.fixture
def make_paper():
    """Synthetic metadata for offline tests only; never production observations."""
    def make(index=1, title="multi agent systems", year=2024):
        identifier = f"2401.{index:05d}v1"
        return PaperMetadata(paper_id=identifier, version_id=identifier, title=title, authors=["Fixture"],
            abstract=title, submitted_date=date(year, 1, 1), updated_date=date(year, 1, 2),
            source_url=f"https://arxiv.org/abs/{identifier}", html_url=f"https://arxiv.org/html/{identifier}",
            pdf_url=f"https://arxiv.org/pdf/{identifier}")
    return make


@pytest.fixture
def html_body():
    return b'''<article><section class="ltx_section" id="S1"><h2>1 Introduction</h2>
    <p>Fixture body text.</p><section class="ltx_subsection" id="S1.S1"><h3>Details</h3><p>Nested text.</p></section></section>
    <ul><li class="ltx_bibitem" id="bib1">Fixture reference <a href="https://doi.org/10.1234/test">DOI</a></li></ul></article>'''


@pytest.fixture
def tei_body():
    return b'''<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><div xml:id="d1"><head>Methods</head><p>Fixture method.</p></div></body>
    <back><listBibl><biblStruct xml:id="b1"><analytic><title level="a">Fixture title</title></analytic><idno type="DOI">10.1234/test</idno></biblStruct></listBibl></back></text></TEI>'''
