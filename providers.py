"""
One place that knows about the three providers.

All of them speak the OpenAI wire format, so the only things that change are
the base URL, the key and the model name. That means a single client and a
single call path instead of one SDK per provider.

The key can come from the request (typed into the UI) or from the environment.
Whatever the UI sends wins, so nobody has to edit a .env to try a provider.
"""

import os
import re

from openai import OpenAI

PROVIDERS = {
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "env": ["GROQ_API_KEY"],
        "default_model": "openai/gpt-oss-120b",
        "console": "https://console.groq.com/keys",
    },
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "default_model": "gemini-flash-latest",
        "console": "https://aistudio.google.com/apikey",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env": ["OPENAI_API_KEY"],
        "default_model": "gpt-4o-mini",
        "console": "https://platform.openai.com/api-keys",
    },
}

DEFAULT_PROVIDER = "groq"


class ProviderError(Exception):
    """Something the user can fix - a missing key, an unknown provider."""


def env_key(provider: str):
    for name in PROVIDERS[provider]["env"]:
        value = os.getenv(name)
        if value:
            return value
    return None


def resolve(provider: str = None, api_key: str = None, model: str = None):
    """Work out which provider, key and model to use for one request."""
    provider = (provider or DEFAULT_PROVIDER).strip().lower()
    if provider not in PROVIDERS:
        raise ProviderError(f"Unknown provider '{provider}'.")

    spec = PROVIDERS[provider]

    # a key typed into the UI beats whatever is in the environment
    key = (api_key or "").strip() or env_key(provider)
    if not key:
        names = " or ".join(spec["env"])
        raise ProviderError(
            f"No API key for {spec['label']}. Add one in Settings, or set {names} in .env."
        )

    return provider, key, (model or "").strip() or spec["default_model"]


def client_for(provider: str, api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=PROVIDERS[provider]["base_url"])


def clean(text: str) -> str:
    """
    Some models emit LaTeX or markdown no matter what the prompt says. Strip
    the delimiters so the plain-text UI does not show raw markup.
    """
    if not text:
        return ""
    # \frac{a}{b} reads fine as a/b
    text = re.sub(r"\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", text)
    for old, new in (
        ("\\[", ""), ("\\]", ""), ("\\(", ""), ("\\)", ""),
        ("\\displaystyle", ""), ("\\times", "x"), ("\\div", "/"),
        ("\\cdot", "*"), ("\\,", " "), ("\\!", ""), ("$$", ""),
        ("**", ""), ("###", ""), ("##", ""),
    ):
        text = text.replace(old, new)
    # collapse the blank lines the stripping leaves behind
    lines = [ln.rstrip() for ln in text.splitlines()]
    out, blank = [], False
    for ln in lines:
        if not ln.strip():
            if not blank and out:
                out.append("")
            blank = True
        else:
            out.append(ln)
            blank = False
    return "\n".join(out).strip()


def friendly_error(exc: Exception) -> str:
    """
    Turn the provider's error into something worth showing a user. The SDK
    messages wrap the raw JSON, so pull the message out of it.
    """
    text = str(exc)
    status = getattr(exc, "status_code", None)

    # the SDK exposes the parsed body on most errors
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            text = err["message"]
        elif isinstance(err, str):
            text = err

    # fall back to digging the message out of the repr
    if text.startswith("Error code:"):
        found = re.search(r"'message': ['\"](.+?)['\"], ['\"](?:type|code)['\"]", text)
        if found:
            text = found.group(1)

    lowered = text.lower()
    if status == 401 or "invalid_api_key" in lowered or "api key not valid" in lowered:
        return "That API key was rejected. Check it is correct and for the right provider."
    if status == 429 or "rate limit" in lowered or "quota" in lowered:
        return "Rate limited or out of quota on this key. Wait a moment, or try another provider."
    if "does not exist" in lowered or "model_not_found" in lowered or status == 404:
        return f"{text} Pick a different model in Settings."
    return text


def list_models(provider: str, api_key: str):
    """Ask the provider what it can actually run, so the UI never offers a dead model."""
    models = [m.id for m in client_for(provider, api_key).models.list().data]

    # gemini's openai-compatible endpoint prefixes everything with "models/"
    models = [m.split("/", 1)[1] if m.startswith("models/") else m for m in models]

    # keep chat models, drop the embedding / audio / image ones
    skip = ("embedding", "embed", "whisper", "tts", "image", "vision-preview",
            "guard", "moderation", "dall-e", "sora", "veo", "imagen", "gemma")
    chat = [m for m in models if not any(s in m.lower() for s in skip)]

    return sorted(set(chat or models))
