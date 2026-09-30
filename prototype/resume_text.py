"""Read a resume file and suggest form values.

Suggestions, not an import. The plan requires a human to check every profile, and a pre-filled
form the person corrects before saving is the cheapest way to make that the default rather than
a separate review step nobody does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["ParsedResume", "parse_resume", "extract_profile_hints"]

SKILL_VOCAB = (
    "python", "java", "javascript", "typescript", "golang", "rust", "c++", "c#", "php", "ruby",
    "scala", "kotlin", "swift", "django", "flask", "fastapi", "spring boot", "spring", "node.js",
    "nodejs", "react", "angular", "vue", "next.js", "express", "postgresql", "postgres", "mysql",
    "mongodb", "redis", "elasticsearch", "kafka", "rabbitmq", "celery", "docker", "kubernetes",
    "aws", "azure", "gcp", "terraform", "ansible", "jenkins", "github actions", "ci/cd",
    "graphql", "rest api", "microservices", "machine learning", "deep learning", "pytorch",
    "tensorflow", "scikit-learn", "nlp", "llm", "pandas", "numpy", "spark", "airflow", "dbt",
    "snowflake", "tableau", "power bi", "sql", "linux", "git", "selenium", "pytest", "cypress",
    # Azure and data engineering. Added after a real resume came back with almost no skills
    # detected: the vocabulary was Python-web shaped and missed an entire discipline.
    "databricks", "azure databricks", "pyspark", "delta lake", "unity catalog", "lakehouse",
    "medallion", "azure data factory", "adf", "synapse", "azure synapse", "adls", "data lake",
    "etl", "elt", "ssis", "sql server", "t-sql", "azure devops", "databricks sql",
    "delta live tables", "dlt", "autoloader", "great expectations", "data modeling",
    "dimensional modeling", "star schema", "slowly changing dimensions", "scd",
    "data warehouse", "redshift", "bigquery", "glue", "athena", "emr", "hive", "hadoop",
    "looker", "dax", "azure functions", "event hubs", "cosmos db", "blob storage",
)


@dataclass
class ParsedResume:
    text: str
    page_count: int = 0
    warnings: list[str] = field(default_factory=list)


def parse_resume(path: Path | str) -> ParsedResume:
    """Extract plain text from PDF, DOCX or TXT. Never raises on a bad file."""
    path = Path(path)
    suffix = path.suffix.lower()

    if not path.is_file():
        return ParsedResume("", warnings=["file_not_found"])
    if path.stat().st_size == 0:
        return ParsedResume("", warnings=["empty_file"])

    try:
        if suffix == ".pdf":
            return _parse_pdf(path)
        if suffix == ".docx":
            return _parse_docx(path)
        if suffix in {".txt", ".rtf"}:
            return ParsedResume(_normalise(path.read_text(encoding="utf-8", errors="replace")))
        if suffix == ".doc":
            return ParsedResume("", warnings=["legacy_doc_unsupported"])
    except Exception as exc:  # noqa: BLE001 - a bad upload must not 500 the app
        return ParsedResume("", warnings=[f"parse_failed: {type(exc).__name__}"])

    return ParsedResume("", warnings=[f"unsupported_suffix: {suffix}"])


def _parse_pdf(path: Path) -> ParsedResume:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
    except PdfReadError as exc:
        return ParsedResume("", warnings=[f"unreadable_pdf: {exc}"])

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:  # noqa: BLE001
            return ParsedResume("", warnings=["encrypted_pdf"])

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            pages.append("")

    text = _normalise("\n".join(pages))
    warnings = [] if len(text) > 40 else ["no_extractable_text"]
    return ParsedResume(text, page_count=len(reader.pages), warnings=warnings)


def _parse_docx(path: Path) -> ParsedResume:
    import docx

    document = docx.Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))

    text = _normalise("\n".join(parts))
    return ParsedResume(text, warnings=[] if len(text) > 40 else ["no_extractable_text"])


def _normalise(text: str) -> str:
    """Rejoin words broken across line ends, collapse whitespace, keep line structure."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


#: Lines that are contact details rather than content.
_CONTACT_MARKERS = re.compile(
    r"(@|linkedin|github|gitlab|portfolio|https?://|www\.|\+\d{1,3}[\s-]?\d|\d{10})",
    re.IGNORECASE,
)

#: Headings that introduce a real summary, in the wording resumes actually use.
_SUMMARY_HEADINGS = (
    "professional summary", "career summary", "profile summary", "executive summary",
    "summary of qualifications", "summary", "professional profile", "profile", "about me",
    "about", "objective", "career objective", "overview", "synopsis", "introduction",
)


def _strip_contact_block(text: str) -> list[str]:
    """Drop the contact header so it cannot be mistaken for content.

    A real resume put the name, phone, email and LinkedIn on two lines with no SUMMARY heading
    anywhere, and the old fallback -- "first 45 words" -- filled the summary field with the
    contact block. Removing those lines up front fixes the summary, the name and the headline
    together.
    """
    kept: list[str] = []
    for index, raw in enumerate(text.splitlines()):
        line = raw.strip()
        if not line:
            continue
        # Only the top of the document is contact-shaped; an email further down is content.
        if index < 8 and _CONTACT_MARKERS.search(line):
            continue
        kept.append(line)
    return kept


def _looks_like_prose(line: str) -> bool:
    """Whether a line reads as a sentence rather than a heading or a skills bar."""
    if len(line) < 45:
        return False
    if line.count("|") >= 2 or line.count("•") >= 2:
        return False
    if line.isupper():
        return False
    words = line.split()
    if len(words) < 8:
        return False
    # Counting lower-case words rejected real sentences: technical prose is full of proper
    # nouns ("Built Medallion pipelines on Azure Databricks using PySpark"). Function words
    # are the reliable signal -- a comma-separated skills list has almost none.
    functions = {
        "the", "a", "an", "with", "of", "on", "for", "and", "in", "to", "from", "that",
        "by", "as", "into", "across", "using", "through", "over", "at", "while",
    }
    hits = sum(1 for w in words if w.strip(",.;:()").lower() in functions)
    return hits >= 2


#: A summary longer than this is almost certainly the whole document, not a summary.
SUMMARY_LIMIT = 1400


def _truncate_cleanly(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """Cut at a sentence, or failing that a word, never mid-word.

    A hard slice produced "...CI/CD with Azure DevOps and GitHub A", which reads as a bug to
    whoever is reviewing the profile and has to be repaired by hand.
    """
    text = text.strip()
    if len(text) <= limit:
        return text

    window = text[:limit]
    # Prefer the last sentence end that keeps most of the text.
    sentence_end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if sentence_end > limit * 0.6:
        return window[: sentence_end + 1].strip()

    space = window.rfind(" ")
    return (window[:space] if space > 0 else window).strip() + "…"


def _extract_summary(text: str, content_lines: list[str]) -> str:
    """A real summary, or nothing at all.

    Empty beats wrong here: the field is edited by hand before saving, and deleting a paragraph
    of someone's phone number is more work than typing one line.
    """
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        heading = raw.strip().rstrip(":").strip().lower()
        if heading in _SUMMARY_HEADINGS:
            body: list[str] = []
            for following in lines[index + 1 : index + 12]:
                stripped = following.strip()
                if not stripped:
                    if body:
                        break
                    continue
                # Stop at the next heading.
                if stripped.rstrip(":").strip().lower() in _SUMMARY_HEADINGS or (
                    stripped.isupper() and len(stripped.split()) <= 5
                ):
                    break
                body.append(stripped)
            joined = " ".join(" ".join(body).split())
            if len(joined) >= 40:
                return _truncate_cleanly(joined)

    # No heading: take the first run of consecutive prose lines, so the summary starts at the
    # beginning of a paragraph rather than halfway through a sentence.
    run: list[str] = []
    for line in content_lines:
        if not run:
            if _looks_like_prose(line):
                run.append(line)
            continue

        # Continuation of a wrapped paragraph. A looser test on purpose: the last line of a
        # wrapped paragraph is short ("reporting. Automated deployments with Azure DevOps."),
        # and the full prose test rejects it, which truncated the summary mid-sentence.
        if _is_heading(line) or len(line.split()) < 3:
            break
        run.append(line)
        if len(run) >= 6 or line.rstrip().endswith((".", "!", "?")) and len(run) >= 2:
            break

    if run:
        return _truncate_cleanly(" ".join(" ".join(run).split()))
    return ""


def _is_heading(line: str) -> bool:
    """A short all-caps or title-style line that starts a new section."""
    stripped = line.strip().rstrip(":")
    if not stripped:
        return True
    if stripped.lower() in _SUMMARY_HEADINGS:
        return True
    return stripped.isupper() and len(stripped.split()) <= 5


#: Headline segments that are not skills. These show up when a headline wraps across lines,
#: e.g. "DELTA LAKE Lakehouse (Medallion)" / "Architecture | ETL ...", which yields a bare
#: "architecture" segment.
_NOT_A_SKILL = {
    "architecture", "architectures", "pipelines", "pipeline", "engineering", "development",
    "design", "solutions", "services", "systems", "platform", "platforms", "tools",
    "technologies", "frameworks", "experience", "expertise", "specialist", "professional",
    "certified", "immediate joiner", "notice period", "available", "resume", "cv",
}


def _extract_headline_skills(content_lines: list[str]) -> list[str]:
    """Skills from a pipe- or bullet-delimited headline bar near the top.

    "DATA ENGINEER | AZURE DATABRICKS | PYSPARK | DELTA LAKE" is the densest skill signal in
    many resumes and the vocabulary scan alone misses the phrasing.
    """
    found: list[str] = []
    for line in content_lines[:6]:
        if line.count("|") < 2:
            continue
        for part in line.split("|"):
            token = part.strip().strip("-• ").lower()
            token = re.sub(r"\s*\(.*?\)\s*", " ", token).strip()
            if 2 <= len(token) <= 40 and not token.isdigit() and token not in _NOT_A_SKILL:
                found.append(token)
    return found


def _clean_phone(match) -> str:
    """Only return a phone number long enough to plausibly be one."""
    if not match:
        return ""
    value = match.group(0).strip()
    return value if len(value) >= 8 else ""


def extract_profile_hints(text: str) -> dict:
    """Guess name, email, phone, title, skills, years and location from resume text."""
    lowered = text.lower()
    content_lines = _strip_contact_block(text)

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone_match = re.search(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)?\d{5,10}", text)

    # The name often shares a line with the phone number ("YASH MHATRE +91 75069..."), so read
    # the leading capitalised words rather than requiring a line that holds only a name.
    name = ""
    for raw in text.splitlines()[:6]:
        leading = re.match(r"^\s*((?:[A-Z][A-Za-z.'-]+\s+){1,3}[A-Z][A-Za-z.'-]+)", raw.strip())
        if not leading:
            continue
        words = leading.group(1).split()
        if not (2 <= len(words) <= 4):
            continue
        if not all(w.replace(".", "").replace("-", "").replace("'", "").isalpha() for w in words):
            continue
        candidate = " ".join(words)
        if candidate.lower() in {"curriculum vitae", "resume of", "data engineer"}:
            continue
        name = " ".join(w.capitalize() for w in words)
        break

    title = ""
    title_match = re.search(
        r"\b((?:senior|lead|principal|staff|junior)?\s*(?:python|java|backend|front[\s-]?end|"
        r"full[\s-]?stack|devops|data|ml|machine learning|qa|cloud|software)\s*"
        r"(?:engineer|developer|architect|scientist|analyst|consultant))\b",
        lowered,
    )
    if title_match:
        title = " ".join(w.capitalize() for w in title_match.group(1).split())
    if not title:
        # Many resumes put the title first in a pipe-delimited headline bar.
        for line in content_lines[:4]:
            first = line.split("|")[0].strip()
            if 2 <= len(first.split()) <= 5 and re.search(
                r"\b(engineer|developer|architect|analyst|scientist|consultant|administrator)\b",
                first,
                re.IGNORECASE,
            ):
                title = " ".join(w.capitalize() for w in first.split())
                break

    years = None
    for pattern in (
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+|total\s+)?experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)",
    ):
        found = re.search(pattern, lowered)
        if found:
            years = float(found.group(1))
            break

    if years is None:
        # No "N years of experience" phrasing anywhere. Infer from the earliest employment date
        # range, which many resumes state only as "(2022-present)". A guess, and the form is
        # edited before saving, so a wrong guess costs one correction rather than a bad match.
        ranges = re.findall(r"\b(19|20)(\d{2})\s*(?:-|to|–)\s*(present|current|\d{4})", lowered)
        if ranges:
            span = datetime.now(UTC).year - min(int(f"{c}{y}") for c, y, _ in ranges)
            if 0 < span <= 45:
                years = float(span)

    cities = (
        "pune", "navi mumbai", "mumbai", "thane", "bangalore", "bengaluru", "hyderabad",
        "new delhi", "delhi", "noida", "gurugram", "gurgaon", "chennai", "kolkata",
        "ahmedabad", "jaipur", "indore", "kochi", "coimbatore", "nagpur", "remote",
    )
    # Search the contact header first. Scanning the whole document picked up the university city
    # from an EDUCATION line, which is not where the candidate lives now.
    header = "\n".join(text.splitlines()[:4]).lower()
    location = ""
    for scope in (header, lowered):
        for city in cities:
            if re.search(rf"\b{city}\b", scope):
                location = city.title()
                break
        if location:
            break

    vocab_hits = {
        s for s in SKILL_VOCAB if re.search(rf"(?<![a-z]){re.escape(s)}(?![a-z])", lowered)
    }
    # Merge in the headline bar, but drop segments that are job titles, so "data engineer" does
    # not become a skill alongside "pyspark".
    for token in _extract_headline_skills(content_lines):
        if token in SKILL_VOCAB:
            vocab_hits.add(token)
        elif not re.search(
            r"\b(engineer|developer|architect|analyst|scientist|consultant)\b", token
        ):
            vocab_hits.add(token)
    # Headline bars produce compounds like "delta lake lakehouse architecture" beside the
    # canonical "delta lake". Keep the canonical term and drop anything that merely wraps it.
    canonical = {t for t in vocab_hits if t in SKILL_VOCAB}
    skills = sorted(
        t for t in vocab_hits if t in canonical or not any(c in t and c != t for c in canonical)
    )

    summary = _extract_summary(text, content_lines)

    return {
        "name": name,
        "email": email_match.group(0) if email_match else "",
        "phone": _clean_phone(phone_match),
        "title": title,
        "skills": ", ".join(skills),
        "years_experience": years,
        "location": location,
        "summary": summary,
    }
