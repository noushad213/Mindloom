from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_KEYS = {"fbclid", "gclid", "ref"}


def canonical_url(url: str) -> str:
    """Return a stable http(s) page identity, or raise ValueError."""
    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        if scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if host.startswith("www."):
            host = host[4:]
        port = parts.port
        if ":" in host:
            host = f"[{host}]"
        netloc = host if port in {None, 80 if scheme == "http" else 443} else f"{host}:{port}"
        query = urlencode(
            sorted(
                (key, value)
                for key, value in parse_qsl(parts.query, keep_blank_values=True)
                if not key.lower().startswith(("utm_", "mc_")) and key.lower() not in TRACKING_KEYS
            ),
            doseq=True,
        )
        return urlunsplit((scheme, netloc, parts.path.rstrip("/"), query, ""))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("url must be an absolute HTTP or HTTPS URL") from exc
