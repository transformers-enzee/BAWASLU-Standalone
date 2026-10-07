import json
import re
from pathlib import Path

_DATA=json.loads(Path(__file__).with_name('regions.json').read_text(encoding='utf-8'))
PROVINCES=_DATA.get('provinces',[])
REGENCIES=_DATA.get('regencies',[])
PROVINCE_BY_CODE={str(x.get('code')):x for x in PROVINCES}
REGENCY_BY_CODE={str(x.get('code')):x for x in REGENCIES}

INDONESIAN_PROVINCE_ALIASES={
 '11':['Aceh'],
 '12':['Sumatera Utara'],
 '13':['Sumatera Barat'],
 '14':['Riau'],
 '15':['Jambi'],
 '16':['Sumatera Selatan'],
 '17':['Bengkulu'],
 '18':['Lampung'],
 '19':['Kepulauan Bangka Belitung','Bangka Belitung'],
 '21':['Kepulauan Riau'],
 '31':['DKI Jakarta','Jakarta'],
 '32':['Jawa Barat'],
 '33':['Jawa Tengah'],
 '34':['DI Yogyakarta','Daerah Istimewa Yogyakarta','Yogyakarta'],
 '35':['Jawa Timur'],
 '36':['Banten'],
 '51':['Bali'],
 '52':['Nusa Tenggara Barat'],
 '53':['Nusa Tenggara Timur'],
 '61':['Kalimantan Barat'],
 '62':['Kalimantan Tengah'],
 '63':['Kalimantan Selatan'],
 '64':['Kalimantan Timur'],
 '65':['Kalimantan Utara'],
 '71':['Sulawesi Utara'],
 '72':['Sulawesi Tengah'],
 '73':['Sulawesi Selatan'],
 '74':['Sulawesi Tenggara'],
 '75':['Gorontalo'],
 '76':['Sulawesi Barat'],
 '81':['Maluku'],
 '82':['Maluku Utara'],
 '91':['Papua'],
 '92':['Papua Barat'],
 '93':['Papua Selatan'],
 '94':['Papua Tengah'],
 '95':['Papua Pegunungan'],
 '96':['Papua Barat Daya'],
}

def _norm(value):
    return re.sub(r'[^a-z0-9]+',' ',str(value or '').lower()).strip()

PROVINCE_CODE_BY_NAME={}
for code,row in PROVINCE_BY_CODE.items():
    PROVINCE_CODE_BY_NAME[_norm(row.get('name'))]=code
for code,names in INDONESIAN_PROVINCE_ALIASES.items():
    for name in names:
        PROVINCE_CODE_BY_NAME[_norm(name)]=code

REGENCY_CODE_BY_NAME={}
for code,row in REGENCY_BY_CODE.items():
    REGENCY_CODE_BY_NAME[(_norm(row.get('name')),str(row.get('province_code') or ''))]=code
    REGENCY_CODE_BY_NAME[(_norm(row.get('name')),'')]=code

def province_code_for(name='',code=''):
    c=str(code or '').strip()
    if c in PROVINCE_BY_CODE: return c
    return PROVINCE_CODE_BY_NAME.get(_norm(name),'')

def province_name_for(code='',fallback=''):
    row=PROVINCE_BY_CODE.get(str(code or '').strip())
    return str(fallback or '').strip() or (row.get('name','') if row else '')

def regency_code_for(name='',province_code='',code=''):
    c=str(code or '').strip()
    if c in REGENCY_BY_CODE: return c
    key=(_norm(name),str(province_code or '').strip())
    return REGENCY_CODE_BY_NAME.get(key) or REGENCY_CODE_BY_NAME.get((_norm(name),''),'')

def regency_name_for(code='',fallback=''):
    row=REGENCY_BY_CODE.get(str(code or '').strip())
    return str(fallback or '').strip() or (row.get('name','') if row else '')

def normalize_assignment(value):
    value=value or {}
    regency_code=regency_code_for(value.get('regency_city') or value.get('regency_city_name'),value.get('province_code'),value.get('regency_city_code'))
    regency_row=REGENCY_BY_CODE.get(regency_code)
    province_code=province_code_for(value.get('province') or value.get('province_name'),value.get('province_code'))
    if regency_row:
        province_code=str(regency_row.get('province_code') or province_code)
    province=province_name_for(province_code,value.get('province') or value.get('province_name'))
    regency=regency_name_for(regency_code,value.get('regency_city') or value.get('regency_city_name'))
    return {
      'province_code':province_code,
      'province':province,
      'regency_city_code':regency_code,
      'regency_city':regency,
    }

def normalize_assignments(values):
    out=[]
    seen=set()
    for raw in values or []:
        area=normalize_assignment(raw)
        if not area['province_code'] and not area['province']:
            continue
        key=(area['province_code'] or _norm(area['province']),area['regency_city_code'] or _norm(area['regency_city']))
        if key in seen:
            continue
        seen.add(key)
        out.append(area)
        if len(out)>=30: break
    return out

def normalize_jurisdiction(value,require_valid=False):
    value=value or {}
    kind=str(value.get('jurisdiction_type') or 'Unresolved').strip()
    if kind not in ('National','Province','Regency / City','Multi-Region','Unresolved'):
        raise ValueError('Invalid jurisdiction classification')

    result={
      'jurisdiction_type':kind,
      'province':'','province_code':'',
      'regency_city':'','regency_city_code':'',
      'geographic_assignments':[]
    }

    if kind in ('Unresolved','National'):
        return result

    if kind=='Multi-Region':
        assignments=normalize_assignments(value.get('geographic_assignments') or [])
        if require_valid and len(assignments)<2:
            raise ValueError('Multi-Region jurisdiction requires at least two distinct areas')
        result['geographic_assignments']=assignments
        return result

    area=normalize_assignment(value)
    if require_valid and not (area['province_code'] or area['province']):
        raise ValueError('Province is required for this jurisdiction')
    if kind=='Regency / City' and require_valid and not (area['regency_city_code'] or area['regency_city']):
        raise ValueError('Regency / City is required for this jurisdiction')
    result.update(area)
    return result

def profile_region_codes(province='',regency_city=''):
    pcode=province_code_for(province)
    rcode=regency_code_for(regency_city,pcode)
    if rcode and not pcode:
        row=REGENCY_BY_CODE.get(rcode)
        pcode=str(row.get('province_code') or '') if row else ''
    return pcode,rcode

def assignment_matches_profile(area,profile):
    a=normalize_assignment(area)
    pcode=profile.get('province_code') or province_code_for(profile.get('province'))
    rcode=profile.get('regency_city_code') or regency_code_for(profile.get('regency_city'),pcode)
    province_match=bool(pcode and a['province_code']==pcode) or bool(profile.get('province') and _norm(profile.get('province'))==_norm(a['province']))
    if not province_match: return False
    if profile.get('geographic_scope')=='Regency/City':
        if not rcode and not profile.get('regency_city'): return False
        if not a['regency_city_code'] and not a['regency_city']: return True
        return bool(rcode and a['regency_city_code']==rcode) or _norm(profile.get('regency_city'))==_norm(a['regency_city'])
    return True
