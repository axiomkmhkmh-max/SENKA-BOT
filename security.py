"""Signed callbacks, text normalisation, name validation, rate limiting."""
import hashlib
import hmac
import re
import time
import unicodedata

from config import settings

_TRANS = str.maketrans({
    "ي": "ی", "ك": "ک", "ى": "ی", "ة": "ه", "أ": "ا", "إ": "ا", "ؤ": "و", "ۀ": "ه",
    **{c: str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")},
    **{c: str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")},
})
_STRIP = dict.fromkeys(map(ord, "\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0640"), " ")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").translate(_TRANS).translate(_STRIP).lower()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE).replace("_", " ")
    return re.sub(r"\s+", " ", value).strip()


# ---- signed callback data (<= 64 bytes, bound to the clicking user) -------
def _sig(body: str) -> str:
    return hmac.new(settings.hmac_secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:10]


def make_cb(code: str, arg: str = "", owner: int = 0) -> str:
    if ":" in code:
        raise ValueError("':' is reserved in the callback code")
    body = f"{code}:{arg}:{int(owner)}"
    data = f"{body}:{_sig(body)}"
    if len(data.encode()) > 64:
        raise ValueError("callback_data exceeds 64 bytes: " + data)
    return data


def parse_cb(data: str, uid: int):
    """Return (code, arg, allowed) or None when the signature is invalid."""
    head, sep, rest = (data or "").partition(":")
    parts = rest.rsplit(":", 2)
    if not sep or len(parts) != 3:
        return None
    code = head
    arg, owner, sig = parts
    if not hmac.compare_digest(sig, _sig(f"{code}:{arg}:{owner}")):
        return None
    return code, arg, (owner == "0" or owner == str(uid))


# ---- names -----------------------------------------------------------------
_BAD_LATIN = ("fuck", "shit", "bitch", "cunt", "nigger", "nigga", "whore", "slut", "dick", "pussy", "koskesh", "jendeh")
_BAD_FA = {"کس", "کیر", "کون", "جنده", "کصکش", "کسکش", "گاییدم", "کونی", "ممه", "کسخل"}


def clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", (value or "").replace("\u200c", " ")).strip()
    if not 3 <= len(value) <= 20:
        raise ValueError("len")
    if not all(ch.isalnum() or ch in " _-" for ch in value) or not any(ch.isalpha() for ch in value):
        raise ValueError("chars")
    low = normalize_text(value)
    squashed = re.sub(r"[^a-z]", "", low)
    if any(w in squashed for w in _BAD_LATIN) or any(tok in _BAD_FA for tok in low.split()):
        raise ValueError("bad")
    return value


# ---- rate limiting (per process; Mongo cooldowns guard the real actions) ---
_last: dict = {}


def allow(uid: int, key: str, interval: float) -> bool:
    now = time.monotonic()
    k = (uid, key)
    if now - _last.get(k, 0.0) < interval:
        return False
    _last[k] = now
    if len(_last) > 50000:
        cutoff = now - 600
        for kk in [kk for kk, v in _last.items() if v < cutoff]:
            _last.pop(kk, None)
    return True


def now_ts() -> int:
    return int(time.time())
