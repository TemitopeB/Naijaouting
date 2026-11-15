"""
Small helper for Google's Gemini API, used by the smart sweep and the news leads.

- Uses the key in the GEMINI_API_KEY secret (new "AQ." keys and older "AIza" keys both work),
  sent in the x-goog-api-key header to the native Gemini endpoint.
- Picks the newest available "Flash" model automatically, so it keeps working when Google
  retires old model names. Set GEMINI_MODEL to force one.
- search=True lets Gemini run Google searches ("grounding"); the pages it used come back as
  sources, which are resolved to their real web addresses here.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
UA = "NaijaOutingBot/1.0 (+https://github.com/TemitopeB/Naijaouting)"
_model = None


class GeminiError(RuntimeError):
    pass


def key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if not k:
        raise GeminiError("GEMINI_API_KEY secret is not set")
    return k


def _call(method, path, body=None, tries=4):
    data = json.dumps(body).encode() if body is not None else None
    for n in range(tries):
        req = urllib.request.Request(API + path, data=data, method=method,
                                     headers={"x-goog-api-key": key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 503) and n < tries - 1:
                time.sleep(20 * (n + 1))  # free tier: wait and retry
                continue
            raise GeminiError(f"HTTP {e.code}: {msg}")
        except urllib.error.URLError as e:
            if n < tries - 1:
                time.sleep(5)
                continue
            raise GeminiError(str(e))


def _ver(name):
    nums = re.findall(r"(\d+(?:\.\d+)?)", name)
    return float(nums[0]) if nums else 0.0


def model():
    """Newest stable 'flash' text model that supports generateContent."""
    global _model
    if _model:
        return _model
    forced = os.environ.get("GEMINI_MODEL", "").strip()
    if forced:
        _model = forced if forced.startswith("models/") else "models/" + forced
        return _model
    names, token = [], ""
    while True:
        j = _call("GET", "/models?pageSize=200" + (f"&pageToken={token}" if token else ""))
        for m in j.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(m["name"])
        token = j.get("nextPageToken", "")
        if not token:
            break
    bad = re.compile(r"lite|image|tts|audio|live|embed|vision|thinking|exp|preview|learnlm|gemma|aqa|robotics|computer", re.I)
    flash = [n for n in names if "flash" in n and not bad.search(n)]
    if not flash:
        flash = [n for n in names if "flash" in n and "image" not in n and "tts" not in n]
    if not flash:
        raise GeminiError("No Gemini Flash model is available to this key")
    flash.sort(key=lambda n: (_ver(n), "latest" not in n, -len(n)), reverse=True)
    _model = flash[0]
    return _model


def ask(prompt, search=False, temperature=0.2):
    """Returns (text, sources). sources = [{'title': domain, 'uri': grounding link}]"""
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if search:
        body["tools"] = [{"google_search": {}}]
    j = _call("POST", f"/{model()}:generateContent", body)
    cands = j.get("candidates") or []
    if not cands:
        raise GeminiError("Empty answer: " + json.dumps(j.get("promptFeedback", {}))[:200])
    c = cands[0]
    text = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []))
    srcs = []
    for ch in (c.get("groundingMetadata") or {}).get("groundingChunks", []) or []:
        w = ch.get("web") or {}
        if w.get("uri"):
            srcs.append({"title": (w.get("title") or "").lower(), "uri": w["uri"]})
    return text, srcs


_resolved = {}


def real_url(uri):
    """Grounding links are Google redirects; follow one hop to the real page address."""
    if uri in _resolved:
        return _resolved[uri]
    out = ""
    if "grounding-api-redirect" not in uri:
        out = uri
    else:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        op = urllib.request.build_opener(NoRedirect)
        try:
            op.open(urllib.request.Request(uri, method="HEAD", headers={"User-Agent": UA}), timeout=20)
        except urllib.error.HTTPError as e:
            out = e.headers.get("Location", "") if e.code in (301, 302, 303, 307, 308) else ""
        except Exception:
            out = ""
    if out and not out.startswith("https://"):
        out = ""
    _resolved[uri] = out
    return out


def domain(u):
    try:
        h = urllib.parse.urlparse(u if "://" in u else "https://" + u).hostname or ""
    except Exception:
        return ""
    return h.lower().removeprefix("www.")


def parse_json(text):
    """Pull the first JSON array or object out of a model answer (handles ```json fences)."""
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        i = t.find(opener)
        j = t.rfind(closer)
        if i != -1 and j > i:
            chunk = t[i:j + 1]
            try:
                return json.loads(chunk)
            except Exception:
                try:
                    return json.loads(re.sub(r",\s*([}\]])", r"\1", chunk))
                except Exception:
                    continue
    return None
