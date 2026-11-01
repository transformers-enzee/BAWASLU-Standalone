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
_inflight={}
_generation=0

def invalidate():
    global _generation
    with _lock:
        _generation+=1
        _entries.clear()
        # Wake waiters so they can re-check the authorization-scoped generation.
        for _,event in _inflight.values():event.set()
        _inflight.clear()

def read(principal,query,loader):
    """One expensive read per scoped principal/query, including cold concurrency.

    Concurrent requests wait for a shared authorized result; they do not start
    duplicated Postgres scans and exhaust the small shared connection pool.
    Invalidation wakes all waiters. Failures are never cached.
    """
    identity=json.dumps([principal,query],sort_keys=True,default=str,ensure_ascii=True)
    key=hashlib.sha256(identity.encode()).hexdigest()
    while True:
        now=time.monotonic()
        with _lock:
            item=_entries.get(key)
            if item and item[0]>now and item[2]==_generation:
                _entries.move_to_end(key)
                return copy.deepcopy(item[1])
            if item:_entries.pop(key,None)
            gen=_generation
            pending=_inflight.get(key)
            owner=pending is None or pending[0]!=gen
            if owner:
                event=threading.Event()
                _inflight[key]=(gen,event)
            else:
                event=pending[1]
        if not owner:
            # A leader can fail, be invalidated or time out; retry authorization-
            # scoped lookup when it finishes. Bounded wait avoids deadlock.
            if not event.wait(timeout=60):
                raise TimeoutError('Authorized Inbox read is busy; retry request')
            continue
        try:
            result=loader()
            with _lock:
                if gen==_generation:
                    _entries[key]=(time.monotonic()+_TTL,copy.deepcopy(result),gen)
                    _entries.move_to_end(key)
                    while len(_entries)>_MAX:_entries.popitem(last=False)
            return result
        finally:
            with _lock:
                current=_inflight.get(key)
                if current and current[1] is event:
                    _inflight.pop(key,None)
                    event.set()

def statistics():
    with _lock:
        return {'entries':len(_entries),'ttl_seconds':_TTL,'max_entries':_MAX}
