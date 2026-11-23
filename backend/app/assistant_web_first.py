"""Public-web-first SmartRadar assistant safety and output contract.

Pure helpers: they never query the database or send text to a third party.
"""
import re
from urllib.parse import urlsplit
from ipaddress import ip_address

PRIVATE_REFERENCE = re.compile(
    r"(?<!\w)(?:SOCIAL-\d+|INT-[A-Za-z0-9:_-]+|DOC-\d+-P\d+|ATT-[a-f0-9]{32}-S\d+)(?!\w)",
    re.IGNORECASE,
)


def safe_public_question(question):
    """Do not forward internal record IDs to external search providers."""
    return not PRIVATE_REFERENCE.search(str(question or ""))


def safe_web_urls(urls):
    """Only keep attributable, ordinary HTTPS web URLs (never source text)."""
    out=[]
    for value in urls or []:
        if not isinstance(value,str) or len(value)>1900:
            continue
        try:
            parsed=urlsplit(value)
            hostname=(parsed.hostname or '').lower().rstrip('.')
            if (parsed.scheme!='https' or not hostname or parsed.username or parsed.password or
                    hostname=='localhost' or hostname.endswith('.localhost')):
                continue
            try:
                address=ip_address(hostname)
            except ValueError:
                address=None
            if address is not None and not address.is_global:
                continue
        except ValueError:
            continue
        if value not in out:out.append(value)
    return out[:6]


def web_brief_text(research, language='en'):
    """Never fill a failed external search with unverified model assertions."""
    if not research or not safe_web_urls(research.get('urls')) or not str(research.get('summary') or '').strip():
        if language=='id':
            return ('Pencarian web publik belum menghasilkan sumber yang dapat dikutip. '
                    'Tidak ada klaim terkini yang terverifikasi dari pencarian ini. '
                    'Periksa laman resmi BAWASLU, KPU, MK atau JDIH, lalu ulangi pencarian. '
                    'Jangan membuka perkara atau menyimpulkan pelanggaran hanya dari jawaban ini.')
        return ('Live public research returned no attributable sources. No current claims or '
                'trends have been verified here. Check official BAWASLU, KPU, MK and JDIH '
                'publications or retry. Do not determine a violation from this response.')
    return str(research['summary']).strip()
