"""One JSON-returning model call, over whichever free API has a key in the environment.

Why provider-agnostic: the production plan targets local Ollama, but a 5GB download is not a
5-hour-prototype decision. Both free hosted tiers that work well for this shape of task are
supported, plus any OpenAI-compatible endpoint, plus a no-key path so the prototype always runs.

Set exactly one of these in ``.env``:

    GEMINI_API_KEY=...      # aistudio.google.com/apikey  - best free-tier quality, JSON schema
    GROQ_API_KEY=...        # console.groq.com/keys       - fastest, generous free tier
    OPENAI_API_KEY=...      # any OpenAI-compatible base url via OPENAI_BASE_URL
    OLLAMA_HOST=...         # if you later install Ollama locally

With no key at all, ``RuleBackend`` answers instead. It is deliberately crude — keyword and
header heuristics — and exists so the pipeline is demonstrable end to end without waiting on a
download or a signup. Everything downstream sees the same shape either way, so swapping in a
real model changes no other file.

Model names are env-overridable because hosted free tiers rename and retire models often, and a
wrong default should be a one-line fix rather than a code change.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

__all__ = ["LLMResult", "get_backend", "backend_name", "RuleBackend"]

TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "45"))


@dataclass
class LLMResult:
    data: dict[str, Any]
    backend: str
    model: str
    latency_ms: int
    raw: str = ""


class BackendError(RuntimeError):
    pass


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object out of a model response.

    Hosted models wrap JSON in prose or fences more often than their docs admit, so this tries
    the whole string, then a fenced block, then the outermost braces.
    """
    text = (text or "").strip()
    if not text:
        raise BackendError("Empty response")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise BackendError(f"No JSON object in response: {text[:200]}")


# ---------------------------------------------------------------------------
# Hosted backends
# ---------------------------------------------------------------------------


class GeminiBackend:
    name = "gemini"

    #: Tried in order when the configured model is overloaded or retired.
    #: Tried in order. Lite first on purpose: each Gemini model has its own free-tier quota,
    #: and the bigger models exhaust theirs first. Classification and re-ranking do not need
    #: the bigger model, so spending its quota is a demo risk with no upside.
    ALTERNATES = ("gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest",
                  "gemini-3.8-flash", "gemini-3.1-flash-lite")

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        # An alias rather than a dated name: dated Gemini models retire, and a 404 on a
        # retired default is a bad failure mode for a prototype someone picks up later.
        self.model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

    def generate_json(self, system: str, user: str) -> LLMResult:
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "response_mime_type": "application/json"},
        }

        # The free tier returns 503 UNAVAILABLE under load and 429 when the quota is hit, often
        # on one model while another is fine. So: retry with backoff, then try the alternates.
        # Without this the prototype silently degrades to keyword heuristics mid-demo.
        attempts: list[str] = []
        response = None
        for model in [self.model, *(m for m in self.ALTERNATES if m != self.model)]:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )
            for delay in (0, 1.0):
                if delay:
                    time.sleep(delay)
                with httpx.Client(timeout=TIMEOUT) as client:
                    response = client.post(url, params={"key": self.api_key}, json=body)
                if response.status_code == 200:
                    self.model = model
                    break
                attempts.append(f"{model}={response.status_code}")
                if response.status_code not in (429, 500, 502, 503, 504):
                    break  # 404 or 401: retrying will not help
            if response is not None and response.status_code == 200:
                break

        if response is None or response.status_code != 200:
            raise BackendError(f"Gemini unavailable after {len(attempts)} attempts: {attempts[-4:]}")

        payload = response.json()
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise BackendError(f"Unexpected Gemini response: {str(payload)[:300]}") from exc

        return LLMResult(
            data=_extract_json(text),
            backend=self.name,
            model=self.model,
            latency_ms=int(response.elapsed.total_seconds() * 1000),
            raw=text,
        )


class OpenAICompatBackend:
    """Groq, OpenRouter, Together, local vLLM, OpenAI itself — all the same wire format."""

    def __init__(self, api_key: str, base_url: str, model: str, name: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = name

    def generate_json(self, system: str, user: str) -> LLMResult:
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
            )
        if response.status_code >= 400:
            raise BackendError(f"{self.name} {response.status_code}: {response.text[:300]}")

        payload = response.json()
        try:
            text = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise BackendError(f"Unexpected {self.name} response: {str(payload)[:300]}") from exc

        return LLMResult(
            data=_extract_json(text),
            backend=self.name,
            model=self.model,
            latency_ms=int(response.elapsed.total_seconds() * 1000),
            raw=text,
        )


class OllamaBackend:
    name = "ollama"

    def __init__(self, host: str) -> None:
        self.host = host.rstrip("/")
        self.model = os.environ.get("OLLAMA_CLASSIFY_MODEL", "qwen3:8b")

    def generate_json(self, system: str, user: str) -> LLMResult:
        body = {
            "model": self.model,
            "system": system,
            "prompt": user,
            "format": "json",
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(f"{self.host}/api/generate", json=body)
        if response.status_code >= 400:
            raise BackendError(f"Ollama {response.status_code}: {response.text[:300]}")

        text = response.json().get("response", "")
        return LLMResult(
            data=_extract_json(text),
            backend=self.name,
            model=self.model,
            latency_ms=int(response.elapsed.total_seconds() * 1000),
            raw=text,
        )


# ---------------------------------------------------------------------------
# No-key fallback
# ---------------------------------------------------------------------------

_RECRUITER_SIGNALS = (
    "hiring", "opening", "opportunity", "role", "position", "requirement", "vacancy",
    "candidate", "resume", "cv", "profile", "shortlist", "interview", "client",
    "notice period", "ctc", "recruiter", "talent acquisition", "staffing", "job description",
)
_BULK_SIGNALS = ("unsubscribe", "newsletter", "view in browser", "manage preferences", "digest")

_SKILL_VOCAB = (
    "python", "java", "javascript", "typescript", "golang", "go", "rust", "c++", "c#", "php",
    "ruby", "scala", "kotlin", "swift", "django", "flask", "fastapi", "spring", "spring boot",
    "node", "nodejs", "react", "angular", "vue", "next.js", "postgres", "postgresql", "mysql",
    "mongodb", "redis", "elasticsearch", "kafka", "rabbitmq", "docker", "kubernetes", "aws",
    "azure", "gcp", "terraform", "jenkins", "ci/cd", "graphql", "rest", "microservices",
    "machine learning", "deep learning", "pytorch", "tensorflow", "nlp", "llm", "pandas",
    "numpy", "spark", "airflow", "sql", "nosql", "devops", "sre", "linux", "git",
)


class RuleBackend:
    """Deterministic stand-in. Crude on purpose, and honest about it in the UI."""

    name = "rules"
    model = "keyword-heuristics"

    def generate_json(self, system: str, user: str) -> LLMResult:
        task = "rerank" if "rerank" in system.lower() else "classify"
        if task == "rerank":
            return LLMResult(data={"ranked": []}, backend=self.name, model=self.model, latency_ms=0)

        text = user.lower()
        bulk_hits = sum(1 for s in _BULK_SIGNALS if s in text)
        hits = [s for s in _RECRUITER_SIGNALS if s in text]

        is_recruiter = len(hits) >= 2 and bulk_hits == 0
        confidence = 0.0 if not is_recruiter else min(0.5 + 0.06 * len(hits), 0.92)

        asking = ("send me", "share the", "share his", "share her", "resume of", "profile of")
        if any(w in text for w in asking):
            intent = "resume_request"
        elif any(w in text for w in ("interview", "availability for a call", "schedule")):
            intent = "interview"
        elif any(w in text for w in ("following up", "any update", "checking in", "circling back")):
            intent = "follow_up"
        elif is_recruiter:
            intent = "new_requirement"
        else:
            intent = "other"

        years = None
        match = re.search(r"(\d+)\s*(?:\+|plus)?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)", text)
        if match:
            years = float(match.group(1))

        location = None
        for city in ("pune", "bangalore", "bengaluru", "hyderabad", "mumbai", "delhi", "noida",
                     "gurgaon", "chennai", "kolkata", "remote", "ahmedabad"):
            if city in text:
                location = city.title()
                break

        role = None
        role_match = re.search(
            r"\b((?:senior|lead|principal|junior|staff)?\s*(?:python|java|backend|frontend|full[\s-]?stack|"
            r"devops|data|ml|machine learning|qa|cloud)\s*"
            r"(?:engineer|developer|architect|scientist|analyst))\b",
            text,
        )
        if role_match:
            role = " ".join(w.capitalize() for w in role_match.group(1).split())

        return LLMResult(
            data={
                "is_recruiter": is_recruiter,
                "confidence": round(confidence, 2),
                "intent": intent,
                "role": role,
                "skills": sorted({s for s in _SKILL_VOCAB if re.search(rf"\b{re.escape(s)}\b", text)}),
                "min_years_experience": years,
                "location": location,
                "candidate_names": [],
                "resume_requested": intent == "resume_request"
                or ("send" in text and any(w in text for w in ("resume", "cv", "profile"))),
            },
            backend=self.name,
            model=self.model,
            latency_ms=0,
        )


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def configured_backends() -> list[Any]:
    """Every configured backend, best first, always ending in the rule fallback.

    A list rather than a single choice because free tiers run out. Each Gemini model has its
    own daily quota, and when they are gone a second provider is the difference between a
    working demo and keyword heuristics. Add a Groq key alongside the Gemini one and the
    prototype crosses over automatically.
    """
    backends: list[Any] = []

    if key := os.environ.get("GEMINI_API_KEY", "").strip():
        backends.append(GeminiBackend(key))

    if key := os.environ.get("GROQ_API_KEY", "").strip():
        backends.append(
            OpenAICompatBackend(
                key,
                os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "groq",
            )
        )

    if key := os.environ.get("OPENAI_API_KEY", "").strip():
        backends.append(
            OpenAICompatBackend(
                key,
                os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "openai-compatible",
            )
        )

    if host := os.environ.get("OLLAMA_HOST", "").strip():
        backends.append(OllamaBackend(host))

    backends.append(RuleBackend())
    return backends


def get_backend() -> Any:
    """The preferred backend, for reporting which one the UI expects to use."""
    return configured_backends()[0]


def backend_name() -> str:
    backend = get_backend()
    return f"{backend.name}:{getattr(backend, 'model', '?')}"


def generate_json(system: str, user: str) -> LLMResult:
    """Call the configured backend, falling back to rules on any failure.

    A hosted free tier will rate-limit, and the prototype must keep working when it does. The
    result records which backend actually answered, and the UI shows it, so a degraded run is
    never mistaken for a good one.
    """
    failures: list[str] = []
    for backend in configured_backends():
        try:
            result = backend.generate_json(system, user)
            if failures:
                result.backend = f"{backend.name} (after {', '.join(failures)})"
            return result
        except Exception as exc:  # noqa: BLE001 - a backend failure degrades, never crashes
            failures.append(f"{backend.name} failed: {str(exc)[:120]}")

    # Unreachable: RuleBackend is always last and cannot fail. Kept so a future reordering
    # cannot turn a degraded run into a crash.
    result = RuleBackend().generate_json(system, user)
    result.backend = "rules"
    result.raw = "; ".join(failures)
    return result
