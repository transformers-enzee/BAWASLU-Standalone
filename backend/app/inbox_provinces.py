"""Province options from authorized, assessed Inbox source evidence.

These describe source text/saved geographic signals, not confirmed jurisdiction.
Match names on token boundaries so 'Bali' is not inferred from 'kembali'.
"""
import re
from sqlalchemy import or_, func
from .geography import INDONESIAN_PROVINCE_ALIASES, PROVINCE_BY_CODE
from .processing_hints import PROVINCE_ALIASES, INCIDENT_REGENCY_PROVINCES

_variant_sets={}
for code,names in INDONESIAN_PROVINCE_ALIASES.items():
    canonical=names[0]
    _variant_sets[canonical]={name.casefold() for name in names}
    row=PROVINCE_BY_CODE.get(code)
    if row and row.get('name'):
        _variant_sets[canonical].add(str(row['name']).casefold())
for alias,canonical in PROVINCE_ALIASES.items():
    _variant_sets.setdefault(canonical,{canonical.casefold()}).add(alias.casefold())
for regency,canonical in INCIDENT_REGENCY_PROVINCES.items():
    _variant_sets.setdefault(canonical,{canonical.casefold()}).add(regency.casefold())

# Both the SQL pagination predicate and in-process dropdown inventory use
# the same expressions. Regex supported by PostgreSQL and SQLAlchemy SQLite.
_PATTERNS={}
for canonical,variants in _variant_sets.items():
    terms='|'.join(re.escape(alias).replace(r'\ ',r'\s+')
        for alias in sorted(variants,key=len,reverse=True))
    pattern=r'(?<![a-z0-9_])(?:'+terms+r')(?![a-z0-9_])'
    _PATTERNS[canonical]=(pattern,re.compile(pattern))

def matching_source_provinces(text,geographic_signals_json=''):
    body=str(text or '').casefold()
    saved=str(geographic_signals_json or '').casefold()
    return sorted((name for name,(_,pattern) in _PATTERNS.items()
        if pattern.search(body) or pattern.search(saved)),key=str.casefold)

def province_match_expression(text_column,signals_column,province):
    selected=_PATTERNS.get(str(province or '').strip())
    if selected is None:
        return None
    pattern=selected[0]
    return or_(func.lower(func.coalesce(text_column,'')).regexp_match(pattern),
               func.lower(func.coalesce(signals_column,'')).regexp_match(pattern))

PROVINCE_NAMES=tuple(sorted(_PATTERNS,key=str.casefold))
