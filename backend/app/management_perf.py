"""Connection-local management SQL timings, no query text or private values."""
from contextlib import contextmanager
from time import perf_counter
from sqlalchemy import event


@contextmanager
def measure_sql(db):
    # Events attach to this session's dedicated SQLAlchemy Connection, never
    # the shared Engine. Concurrent requests are not included in this sample.
    conn=db.connection()
    state={"query_count":0,"db_driver_elapsed_ms":0.0,"max_query_elapsed_ms":0.0}
    starts=[]
    def before(connection,cursor,statement,parameters,context,executemany):
        starts.append(perf_counter())
    def after(connection,cursor,statement,parameters,context,executemany):
        query_ms=(perf_counter()-starts.pop())*1000
        state["query_count"]+=1
        state["db_driver_elapsed_ms"]+=query_ms
        state["max_query_elapsed_ms"]=max(state["max_query_elapsed_ms"],query_ms)
    # SQLAlchemy handle_error is a dialect-wide event, not connection-local.
    # Do not register it here: avoid cross-request contamination.
    event.listen(conn,"before_cursor_execute",before)
    event.listen(conn,"after_cursor_execute",after)
    beginning=perf_counter()
    try:
        yield state
    finally:
        elapsed=(perf_counter()-beginning)*1000
        for name,fn in (
                ("before_cursor_execute",before),
                ("after_cursor_execute",after)):
            event.remove(conn,name,fn)
        db_time=round(state["db_driver_elapsed_ms"],3)
        state["db_driver_elapsed_ms"]=db_time
        state["max_query_elapsed_ms"]=round(state["max_query_elapsed_ms"],3)
        state["average_query_elapsed_ms"]=round(
            db_time/state["query_count"],3) if state["query_count"] else 0.0
        state["total_elapsed_ms"]=round(elapsed,3)
        state["non_db_elapsed_ms"]=round(max(0.0,elapsed-db_time),3)
