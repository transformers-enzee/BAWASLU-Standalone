"""Conservative Kabupaten/Kota source-cue extraction for human jurisdiction review.

Matches only an explicit incident-location construction, never an author
profile, organization address, or campaign's assigned province. No AI or DB IO.
The full Indonesian regency inventory is loaded from the bundled local dataset.
"""
import re
from .geography import REGENCIES, PROVINCE_BY_CODE

_INCIDENT_WORDS=re.compile(
    r'(?<!\w)(?:dugaan|pelanggaran|insiden|kejadian|kasus|kecurangan|'
    r'pemungutan|pencoblosan|mencoblos|penyalahgunaan|peristiwa|'
    r'kericuhan|laporan|temuan|pemilu|pilkada)(?!\w)',re.I)
_NO_INFERENCE=re.compile(
    r'\b(?:akun|profil|pengguna|berasal|domisili|alamat|kantor|'
    r'sekretariat|berkantor|markas|berbasis|organisasi|'
    r'berita\s+dari|media\s+dari|narasumber)\b',re.I)
_ROW_BY_NAME={}
_EXPLICIT_FORMS={}
_SUFFIXES={}
for _row in REGENCIES:
    _name=str(_row.get('name') or '')
    if not _name.startswith(('Kabupaten ','Kota ')):
        continue
    _ROW_BY_NAME[_name.casefold()]=_row
    _EXPLICIT_FORMS[_name.casefold()]=_row
    if _name.startswith('Kabupaten '):
        _suffix=_name[len('Kabupaten '):]
        for _prefix in ('Kab. ','Kab '):
            _EXPLICIT_FORMS[(_prefix+_suffix).casefold()]=_row
    else:
        _suffix=_name[len('Kota '):]
    _SUFFIXES.setdefault(_suffix.casefold(),[]).append(_row)

# Bare locality names can follow an explicitly qualified locality in the
# same grammatical location clause, but are never accepted on their own.
# Ignore bare names shared by different Kabupaten/Kota.
_UNIQUE_SUFFIXES={name:rows[0] for name,rows in _SUFFIXES.items()
                  if len(rows)==1}
_EXPLICIT_TERMS='|'.join(re.escape(n) for n in
                         sorted(_EXPLICIT_FORMS,key=len,reverse=True))
_FOLLOWUP_TERMS='|'.join(re.escape(n) for n in sorted(
    dict.fromkeys([*_EXPLICIT_FORMS,*_UNIQUE_SUFFIXES]),key=len,reverse=True))
_EXPLICIT=re.compile(
    r'(?<!\w)(?:di|pada|berlokasi\s+di|bertempat\s+di)\s+'
    r'(?P<name>'+_EXPLICIT_TERMS+r')(?!\w)',re.I)
_FOLLOWUP=re.compile(
    r'^\s*(?:dan|serta|atau)\s+(?P<name>'+_FOLLOWUP_TERMS+r')(?!\w)',re.I)

def incident_regency_candidates(text):
    """Return source-supported, unverified official region candidates.

    Matching is sentence-local and intentionally incomplete. Ambiguous or
    incomplete sources must be reviewed rather than guessed.
    """
    body=str(text or '')
    found={}
    for sentence in re.split(r'(?<!\bKab)[.!?;\n]+',body,flags=re.I):
        for match in _EXPLICIT.finditer(sentence):
            before=sentence[max(0,match.start()-180):match.start()]
            # Exclude profile/address contexts, even when a nearby source
            # contains a seemingly relevant incident term.
            trailing=before[max(before.rfind(','),before.rfind(':'),0):]
            if not _INCIDENT_WORDS.search(before) or _NO_INFERENCE.search(trailing):
                continue
            names=[match.group('name')]
            after=sentence[match.end():]
            next_match=_FOLLOWUP.match(after)
            if next_match:names.append(next_match.group('name'))
            for name in names:
                row=(_EXPLICIT_FORMS.get(name.casefold()) or
                     _UNIQUE_SUFFIXES.get(name.casefold()))
                if not row:continue
                code=str(row['code'])
                pcode=str(row.get('province_code') or '')
                found[code]={
                    'regency_city_code':code,
                    'regency_city':row['name'],
                    'province_code':pcode,
                    'province':PROVINCE_BY_CODE.get(pcode,{}).get('name',''),
                    'evidence_phrase':name,
                    'verification_status':'UNVERIFIED_SOURCE_CUE',
                }
    return [found[key] for key in sorted(found)]

def incident_regency_preview(text):
    candidates=incident_regency_candidates(text)
    provinces=sorted({item['province_code'] for item in candidates})
    return {
        'candidates':candidates,
        'candidate_count':len(candidates),
        'province_code_count':len(provinces),
        'multiple_regency_candidates':len(candidates)>1,
        'multiple_provinces':len(provinces)>1,
        'kabupaten_kota_verified':False,
        'requires_human_incident_review':bool(candidates),
        'method':'EXPLICIT_INCIDENT_LOCATION_TEXT_AND_LOCAL_REGION_REGISTRY',
        'provider_calls':0,
    }
