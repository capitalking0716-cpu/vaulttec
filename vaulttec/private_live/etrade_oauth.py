"""OAuth 1.0a request signing for the E*TRADE Developer Platform.

E*TRADE uses OAuth 1.0a (RFC 5849), NOT the simple API-key headers
Alpaca uses. Every request is signed with HMAC-SHA1 using the
consumer secret and the access-token secret, and the signature
travels in an ``Authorization`` header.

This module is stdlib only (``hmac``, ``hashlib``, ``urllib``) —
the same rule as the Alpaca broker, so no new dependency is needed.

No credentials live here. Keys and tokens are passed in by the
caller and are never written to a log or a report.

The signer is checked against the worked example in RFC 5849
section 3.4.1.3.2 (see ``tests/test_etrade_broker.py``), so the
math is proven without ever touching E*TRADE's servers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

SIGNATURE_METHOD = "HMAC-SHA1"
OAUTH_VERSION = "1.0"


def percent_encode(value: str) -> str:
    """RFC 3986 percent-encoding (the OAuth flavour).

    Unreserved characters (A-Z a-z 0-9 - . _ ~) are left alone;
    everything else is encoded as %XX with uppercase hex. This
    is NOT the same as ``urllib.parse.quote_plus`` (which turns
    spaces into ``+``) — OAuth needs %20.
    """
    return quote(str(value), safe="-._~")


def normalize_url(url: str) -> str:
    """Lower-case scheme/host, drop the query and fragment, drop
    any default port. E*TRADE's hosts are plain https on 443, so
    in practice this just lower-cases the host."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = parts.hostname.lower() if parts.hostname else ""
    port = parts.port
    if port and ((scheme == "http" and port != 80)
                 or (scheme == "https" and port != 443)):
        host = f"{host}:{port}"
    return urlunsplit((scheme, host, parts.path or "/", "", ""))


def build_signature_base_string(method: str, url: str,
                                params: dict[str, str]) -> str:
    """The exact string that gets signed (RFC 5849 section 3.4.1).

    METHOD & normalized-URL & sorted-encoded-parameters, each
    piece percent-encoded and joined with ``&``.
    """
    encoded = sorted(
        (percent_encode(k), percent_encode(v)) for k, v in params.items())
    param_string = "&".join(f"{k}={v}" for k, v in encoded)
    return "&".join([
        method.upper(),
        percent_encode(normalize_url(url)),
        percent_encode(param_string),
    ])


def sign(method: str, url: str, params: dict[str, str],
         consumer_secret: str, token_secret: str = "") -> str:
    """HMAC-SHA1 signature, base64-encoded (RFC 5849 section 3.4.2).

    The signing key is ``consumer_secret & token_secret``
    (both percent-encoded, joined with ``&``).
    """
    base = build_signature_base_string(method, url, params)
    key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}"
    digest = hmac.new(key.encode("utf-8"), base.encode("utf-8"),
                      hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def oauth_params(consumer_key: str, token: str | None = None,
                 callback: str | None = None,
                 extra: dict[str, str] | None = None) -> dict[str, str]:
    """The OAuth parameters that go into every signed request."""
    params: dict[str, str] = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": SIGNATURE_METHOD,
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": OAUTH_VERSION,
    }
    if token:
        params["oauth_token"] = token
    if callback:
        params["oauth_callback"] = callback
    if extra:
        params.update(extra)
    return params


def authorization_header(oauth: dict[str, str]) -> str:
    """Render OAuth parameters as an ``Authorization`` header."""
    parts = ", ".join(
        f'{percent_encode(k)}="{percent_encode(v)}"'
        for k, v in sorted(oauth.items()))
    return f"OAuth {parts}"


def sign_request(method: str, url: str, query_params: dict[str, str],
                 consumer_key: str, consumer_secret: str,
                 token: str | None = None, token_secret: str = "",
                 callback: str | None = None,
                 extra_oauth: dict[str, str] | None = None) -> str:
    """Sign a request and return its ``Authorization`` header value.

    ``query_params`` are the URL query parameters (for a GET they
    are part of the signature; a JSON body is NOT signed — OAuth
    only signs form-encoded bodies, and E*TRADE's order endpoints
    take JSON, so the body stays out of the signature, exactly
    the way the community clients do it).
    """
    oauth = oauth_params(consumer_key, token=token, callback=callback,
                         extra=extra_oauth)
    all_params = {**query_params, **oauth}
    signature = sign(method, url, all_params, consumer_secret, token_secret)
    oauth["oauth_signature"] = signature
    return authorization_header(oauth)


def parse_token_response(body: str) -> dict[str, str]:
    """Parse an E*TRADE token response (``oauth_token=...&...``).

    Token endpoints answer with a query string, not JSON.
    Returns the fields as a dict; an empty body gives {}.
    """
    if not body:
        return {}
    return dict(parse_qsl(body.strip(), keep_blank_values=True))
