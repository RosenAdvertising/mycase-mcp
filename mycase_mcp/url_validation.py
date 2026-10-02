"""Path and destination validation without DNS queries or caller-directed I/O.

The vendor resolves these URLs later; DNS rebinding must also be prevented there.
"""

import ipaddress
import os
import re
import socket
from urllib.parse import urlsplit


DESTINATION_SETTING = "MYCASE_ALLOWED_DESTINATION_HOSTS"
# Normalize only spelling conventions, then match whole keys (never substrings).
DESTINATION_KEYS = frozenset(
    {
        "url",
        "uri",
        "targeturl",
        "targeturi",
        "callbackurl",
        "callbackuri",
        "webhookurl",
        "destinationurl",
        "baseurl",
        "baseurlpattern",
        "backendurl",
        "endpointurl",
        "redirecturl",
        "redirecturi",
    }
)


def document_path(value: str) -> str:
    """Accept an unencoded relative MyCase folder/name, never a fetch locator."""
    message = (
        "Invalid document path: use a safe relative MyCase folder/name "
        "(ASCII letters, digits, spaces, _, -, ., parentheses; at most 1024 "
        "characters and 255 per segment). URLs, empty/dot segments, encodings "
        "and leading/trailing spaces or dots are not allowed."
    )
    if not isinstance(value, str) or not 1 <= len(value) <= 1024:
        raise ValueError(message)
    segments = value.split("/")
    if any(
        not re.fullmatch(r"[A-Za-z0-9 _().-]{1,255}", segment)
        or segment in {".", ".."}
        or segment != segment.strip(" .")
        for segment in segments
    ):
        raise ValueError(message)
    # A bare filename may have an extension; a hostname before / is URL-shaped.
    first = segments[0].lower()
    if first.startswith("www.") or (
        len(segments) > 1
        and (
            re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", first) or first == "localhost"
        )
    ):
        raise ValueError(message)
    return value


def _normalized_host(host: str) -> str:
    """Normalize configuration hostnames; reject URL syntax and ambiguous dots."""
    if any(c in host for c in "/\\:@%?#") or any(ord(c) <= 32 for c in host):
        raise ValueError
    host = host.encode("idna").decode("ascii").lower()
    if host.endswith("."):
        host = host[:-1]
    if (
        len(host) > 253
        or len(host.split(".")) < 2
        or any(
            not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in host.split(".")
        )
    ):
        raise ValueError
    return host


def destination_url(value: str) -> str:
    """Require the literal URL policy and an administrator-owned host rule."""
    public_https_url(value)
    message = (
        f"Destination refused: configure {DESTINATION_SETTING} with trusted "
        "comma-separated exact hostnames or .example.com for a domain and "
        "its subdomains; the URL host must match."
    )
    try:
        rules = []
        for item in os.environ.get(DESTINATION_SETTING, "").split(","):
            item = item.strip()
            if not item:
                continue
            subtree = item.startswith(".")
            rules.append((_normalized_host(item[1:] if subtree else item), subtree))
        host = _normalized_host(urlsplit(value).hostname or "")
        if not any(
            host == allowed or (subtree and host.endswith("." + allowed))
            for allowed, subtree in rules
        ):
            raise ValueError
    except (ValueError, UnicodeError):
        raise ValueError(message) from None
    return value


def validate_destinations(value) -> None:
    """Check explicit destination keys recursively in caller-supplied objects."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[_\-\s]", "", key).casefold()
            if normalized in DESTINATION_KEYS:
                destination_url(child)
            validate_destinations(child)
    elif isinstance(value, list):
        for child in value:
            validate_destinations(child)


def public_https_url(value: str) -> str:
    message = (
        "Use a public HTTPS URL without userinfo, fragment, or a non-default port."
    )
    try:
        if (
            not isinstance(value, str)
            or not value
            or any(ord(c) <= 32 or ord(c) >= 127 for c in value)
            or "\\" in value
        ):
            raise ValueError
        url = urlsplit(value)
        host = (url.hostname or "").lower().rstrip(".")
        if (
            url.scheme != "https"
            or not host
            or url.username is not None
            or url.password is not None
            or url.fragment
            or url.port not in (None, 443)
            or "%" in url.netloc
        ):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            try:
                address = ipaddress.ip_address(socket.inet_aton(host))
            except OSError:
                address = None
        if address is not None:
            address = getattr(address, "ipv4_mapped", None) or address
            if not address.is_global or address.is_multicast or address.is_reserved:
                raise ValueError
        else:
            labels = host.split(".")
            if len(labels) < 2 or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x)
                for x in labels
            ):
                raise ValueError
            if labels[-1] in {
                "localhost",
                "localdomain",
                "localdomain6",
                "local",
                "internal",
                "lan",
                "home",
                "invalid",
                "test",
            } or re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", labels[-1]):
                raise ValueError
        return value
    except (ValueError, TypeError, OverflowError):
        raise ValueError(message) from None
