from __future__ import annotations
import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit
from .config import allowed_roots, WORKSPACE

class SafetyError(ValueError):
    pass

def safe_path(value: str, *, must_exist: bool = False) -> Path:
    """Resolve before authorizing; reject UNC paths and escapes from configured roots."""
    if not value or '\x00' in value or len(value) > 1000:
        raise SafetyError('Invalid path.')
    if value.startswith(('\\\\', '//')) or value.startswith('\\\\?\\'):
        raise SafetyError('Network/device paths are not allowed.')
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = WORKSPACE / p
    p = p.resolve(strict=False)
    if not any(p == root or root in p.parents for root in allowed_roots()):
        raise SafetyError('Path is outside authorized folders. Configure FRIDAY_ALLOWED_ROOTS to add one.')
    if must_exist and not p.exists():
        raise SafetyError('The requested path does not exist.')
    return p

def safe_public_url(url: str, *, resolve: bool = True) -> str:
    """Allow HTTP(S) only; reject loopback/private/reserved names and resolved addresses.

    DNS is checked before the browser request, but DNS-rebinding cannot be ruled out
    entirely without a network-level firewall; do not expose FRIDAY on a network.
    """
    if len(url) > 2048:
        raise SafetyError('URL is too long.')
    parts = urlsplit(url)
    if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise SafetyError('Only public HTTP(S) URLs without embedded credentials are allowed.')
    host = parts.hostname.rstrip('.').lower()
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
        raise SafetyError('Local or private network destinations are blocked.')
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise SafetyError('Private, local and reserved network addresses are blocked.')
    except ValueError as e:
        if isinstance(e, SafetyError):
            raise
        if resolve:
            try:
                ips = {item[4][0] for item in socket.getaddrinfo(host, parts.port or (443 if parts.scheme == 'https' else 80), type=socket.SOCK_STREAM)}
            except (OSError, ValueError) as exc:
                raise SafetyError(f'Cannot resolve website: {host}') from exc
            if not ips or any(not ipaddress.ip_address(addr).is_global for addr in ips):
                raise SafetyError('Website resolves to a private, local or reserved address.')
    return url

SECRET_PATTERNS = [
    re.compile(r'(?i)\b(password|passwd|passphrase|api[_ -]?key|secret|auth(?:orization)?[_ -]?token|access[_ -]?token|refresh[_ -]?token)\s*[:=]\s*\S+'),
    re.compile(r'(?i)\bbearer\s+[a-z0-9._\-]{12,}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b'),
]
def reject_obvious_secrets(text: str) -> None:
    if any(p.search(text) for p in SECRET_PATTERNS):
        raise SafetyError('This looks like a credential. Passwords and authentication tokens cannot be saved as memory.')

def redact_arguments(name: str, args: dict) -> dict:
    # Action history should record WHAT happened, not page text, file contents or typed text.
    protected = {'content', 'text', 'slides', 'rows', 'question', 'body', 'value', 'message', 'reason', 'query'}
    out = {}
    for k, v in args.items():
        if k in protected:
            out[k] = '[redacted]'
        elif isinstance(v, str):
            out[k] = v[:300]
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, list):
            out[k] = f'[{len(v)} items]'
        else:
            out[k] = '[structured data]'
    return out
