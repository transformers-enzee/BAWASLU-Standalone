"""Bounded per-process RAM cache for authorized, read-only Inbox queries.

Do not persist evidence to Redis/browser storage, and never cache failed auth.
Every lookup is scoped to the current authenticated access profile. Mutations
invalidate local entries; background jobs and other instances refresh by TTL.
"""
import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict

_TTL=90.0
_MAX=64
_lock=threading.RLock()
_entries=OrderedDict()
_generation=0

def invalidate():
    global _generation
    with _lock:
        _generation+=1
        _entries.clear()

def read(principal,query,loader):
    global _generation
    # Including permissions, province, role, status, user ID and query scope
    # prevents an authorized row leaking into a different access context.
    identity=json.dumps([principal,query],sort_keys=True,default=str,ensure_ascii=True)
    key=hashlib.sha256(identity.encode()).hexdigest()
    now=time.monotonic()
    with _lock:
        item=_entries.get(key)
        if item and item[0]>now and item[2]==_generation:
            _entries.move_to_end(key)
            return copy.deepcopy(item[1])
        if item:_entries.pop(key,None)
        generation=_generation
    # Don't hold a lock while Supabase is queried.
    result=loader()
    # Copy to prevent downstream mutation of cached dicts.
    with _lock:
        if generation==_generation:
            _entries[key]=(time.monotonic()+_TTL,copy.deepcopy(result),generation)
            _entries.move_to_end(key)
            while len(_entries)>_MAX:_entries.popitem(last=False)
    return result

def statistics():
    with _lock:
        return {'entries':len(_entries),'ttl_seconds':_TTL,'max_entries':_MAX}
