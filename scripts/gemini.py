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
import socket
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
UA = "NaijaOutingBot/1.0 (+https://github.com/TemitopeB/Naijaouting)"
_model = None
QUOTA_LOG = []  # which models ran out, and which limit (for the run summary)


class GeminiError(RuntimeError):
    pass


def key():
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if not k:
        raise GeminiError("GEMINI_API_KEY secret is not set")
    return k


class QuotaError(GeminiError):
    pass


class SlowError(GeminiError):
    """The model didn't answer in time (or the connection failed)."""


def _quota_info(raw):
    """Short description of which Google limit was hit, from the error body."""
    try:
        err = json.loads(raw).get("error", {})
    except Exception:
        return raw[:200]
    bits = []
    for d in err.get("details", []):
        for v in d.get("violations", []) or []:
            bits.append(f"{v.get('quotaId') or v.get('quotaMetric', '')} (limit {v.get('quotaValue', '?')})")
        if d.get("retryDelay"):
            bits.append("retry after " + d["retryDelay"])
    return "; ".join(bits) or err.get("message", "")[:200]


def _call(method, path, body=None, tries=3, timeout=45):
    data = json.dumps(body).encode() if body is not None else None
    for n in range(tries):
        req = urllib.request.Request(API + path, data=data, method=method,
                                     headers={"x-goog-api-key": key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code == 429:
                info = _quota_info(raw)
                per_minute = "PerMinute" in info and "PerDay" not in info and "limit 0" not in info
                if per_minute and n < tries - 1:
                    time.sleep(30)
                    continue
                raise QuotaError(info)
            if e.code in (500, 503) and n < tries - 1:
                time.sleep(10 * (n + 1))
                continue
            if e.code in (404, 500, 503):
                raise SlowError(f"HTTP {e.code}: model not available right now")
            raise GeminiError(f"HTTP {e.code}: {raw[:300]}")
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as e:
            if n < tries - 1 and not isinstance(e, (TimeoutError, socket.timeout)):
                time.sleep(5)
                continue
            raise SlowError(f"no answer: {e}")


def _ver(name):
    nums = re.findall(r"(\d+(?:\.\d+)?)", name)
    return float(nums[0]) if nums else 0.0


_candidates = None
_dead = set()


def candidates():
    """Flash models, newest first; Flash-Lite ones at the end as a last resort."""
    global _candidates
    if _candidates is not None:
        return _candidates
    forced = os.environ.get("GEMINI_MODEL", "").strip()
    if forced:
        _candidates = [forced if forced.startswith("models/") else "models/" + forced]
        return _candidates
    names, token = [], ""
    while True:
        j = _call("GET", "/models?pageSize=200" + (f"&pageToken={token}" if token else ""))
        for m in j.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                names.append(m["name"])
        token = j.get("nextPageToken", "")
        if not token:
            break
    bad = re.compile(r"image|tts|audio|live|embed|vision|thinking|exp|preview|learnlm|gemma|aqa|robotics|computer", re.I)
    flash = [n for n in names if "flash" in n and not bad.search(n)]
    order = lambda n: (_ver(n), "latest" not in n, -len(n))
    full = sorted([n for n in flash if "lite" not in n], key=order, reverse=True)
    lite = sorted([n for n in flash if "lite" in n], key=order, reverse=True)
    _candidates = full + lite
    if not _candidates:
        raise GeminiError("No Gemini Flash model is available to this key")
    return _candidates


def model():
    """The model currently in use (the first candidate that hasn't run out of quota)."""
    global _model
    if _model and _model not in _dead:
        return _model
    for m in candidates():
        if m not in _dead:
            _model = m
            return m
    raise QuotaError("every available Gemini model is out of free quota for now")


def ask(prompt, search=False, temperature=0.2):
    """Returns (text, sources). sources = [{'title': domain, 'uri': grounding link}]"""
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if search:
        body["tools"] = [{"google_search": {}}]
    while True:
        m = model()
        try:
            j = _call("POST", f"/{m}:generateContent", body)
            break
        except (QuotaError, SlowError) as ex:
            _dead.add(m)
            QUOTA_LOG.append(f"{m.split('/')[-1]}{' + Google Search' if search else ''}: {ex}")
            continue
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
