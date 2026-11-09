import re

from lxml import etree, html

from group3.common.schemas import Reference, Section

TEI = {"t": "http://www.tei-c.org/ns/1.0"}


def clean(node):
    return " ".join(" ".join(node.itertext()).split())


def reference(node, index, locator):
    raw = clean(node)
    links = node.xpath(".//@href | .//@target")
    combined = raw + " " + " ".join(links)
    doi = re.search(r"10\.\d{4,9}/[^\s<>\"}]+", combined, re.I)
    arxiv = re.search(r"(?:arxiv:|arxiv\.org/(?:abs|pdf)/)\s*((?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7})(?:v\d+)?)", combined, re.I)
    titles = node.xpath(".//t:title[@level='a']", namespaces=TEI)
    return Reference(reference_id=node.get("id") or node.get("{http://www.w3.org/XML/1998/namespace}id") or f"r{index}",
                     raw_text=raw, title=clean(titles[0]) if titles else None,
                     doi=doi.group().rstrip(".,;)") if doi else None,
                     arxiv_id=arxiv.group(1) if arxiv else None, source_locator=locator)


def parse_html(content: bytes, url: str):
    root = html.fromstring(content)
    tree = root.getroottree()
    for unwanted in root.xpath("//script | //style | //nav"):
        unwanted.drop_tree()
    sections = []
    # Restrict to actual arXiv/LaTeXML sections, never treat an error page as a paper.
    for node in root.xpath("//section[contains(concat(' ', normalize-space(@class), ' '), ' ltx_section ') or contains(concat(' ', normalize-space(@class), ' '), ' ltx_subsection ')]"):
        headings = node.xpath("./h1 | ./h2 | ./h3 | ./h4 | ./h5 | ./h6")
        if not headings:
            continue
        # Each paragraph belongs to its nearest section, avoiding nested duplication.
        paragraphs = [p for p in node.xpath(".//p") if p.xpath("ancestor::section[1]")[0] is node]
        text = "\n\n".join(clean(p) for p in paragraphs if clean(p))
        if text:
            sections.append(Section(section_id=node.get("id") or f"s{len(sections)+1}", title=clean(headings[0]),
                                    text=text, source_locator=tree.getpath(node), source_url=url))
    references = [reference(n, i, tree.getpath(n)) for i, n in enumerate(root.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' ltx_bibitem ')]"), 1) if clean(n)]
    if not sections:
        raise ValueError("HTML has no parseable arXiv body sections")
    return sections, references


def parse_tei(content: bytes, url: str):
    root = etree.fromstring(content, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    tree = root.getroottree()
    sections = []
    for node in root.xpath("//t:text/t:body//t:div", namespaces=TEI):
        heading = node.find("t:head", TEI)
        paragraphs = node.findall("t:p", TEI)
        text = "\n\n".join(clean(p) for p in paragraphs if clean(p))
        if heading is not None and text:
            sections.append(Section(section_id=node.get("{http://www.w3.org/XML/1998/namespace}id") or f"s{len(sections)+1}",
                                    title=clean(heading), text=text, source_locator=tree.getpath(node), source_url=url))
    references = [reference(n, i, tree.getpath(n)) for i, n in enumerate(root.xpath("//t:listBibl/t:biblStruct", namespaces=TEI), 1) if clean(n)]
    if not sections:
        raise ValueError("GROBID TEI has no titled body sections")
    return sections, references
