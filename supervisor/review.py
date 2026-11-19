from supervisor.validation import UnverifiedClaim

def keep_question(claims: list[UnverifiedClaim]) -> str:
    """The keep/drop question: each keepable claim with its number, reason and closest passages."""
    lines = [f'{len(claims)} claim(s) could not be verified, but their quotes are real. You may keep some:']
    for number, item in enumerate(claims, start=1):
        lines.append(f'  {number}. [{item.paper_id}] {item.claim.text[:200]}')
        lines.append(f'     reason: {item.reason}')
        lines.extend(f'     closest: {passage.section_id} | {passage.text[:100]}' for passage in item.closest)
    lines.append(keep_hint(claims))
    return '\n'.join(lines)

def keep_hint(claims: list[UnverifiedClaim]) -> str:
    """How to answer the keep/drop question."""
    return f"Reply with the numbers to keep, from 1 to {len(claims)} (for example: 1 3), or 'none' to drop all."

def parse_keep_answer(answer: str, claims: list[UnverifiedClaim]) -> set[str] | None:
    """The claim IDs the answer keeps; an empty answer or 'none' keeps nothing; None if it cannot be understood."""
    words = answer.replace(',', ' ').split()
    if not words or [word.lower() for word in words] == ['none']:
        return set()
    if not all(word.isdigit() and 1 <= int(word) <= len(claims) for word in words):
        return None
    return {claims[int(word) - 1].claim.claim_id for word in words}

