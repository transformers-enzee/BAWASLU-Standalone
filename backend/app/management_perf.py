"""Connection-local management SQL timings, no query text or private values."""
from contextlib import contextmanager
from time import perf_counter
from sqlalchemy import event


@contextmanager
def measure_sql(db):
    # Events attach to this session's dedicated SQLAlchemy Connection, never
    # the shared Engine. Concurrent requests are not included in this sample.
    conn=db.connection()
    state={"query_count":0,"db_driver_elapsed_ms":0.0}
    starts=[]
    def before(connection,cursor,statement,parameters,context,executemany):
        starts.append(perf_counter())
    def after(connection,cursor,statement,parameters,context,executemany):
        state["query_count"]+=1
        state["db_driver_elapsed_ms"]+=(
            perf_counter()-starts.pop())*1000
    # Track failures as attempted queries, including DBAPI failures.
    def error(context):
        if starts:
            state["query_count"]+=1
            state["db_driver_elapsed_ms"]+=(
                perf_counter()-starts.pop())*1000
    event.listen(conn,"before_cursor_execute",before)
    event.listen(conn,"after_cursor_execute",after)
    event.listen(conn,"handle_error",error)
    beginning=perf_counter()
    try:
        yield state
    finally:
        elapsed=(perf_counter()-beginning)*1000
        for name,fn in (
                ("before_cursor_execute",before),
                ("after_cursor_execute",after),("handle_error",error)):
            event.remove(conn,name,fn)
        db_time=round(state["db_driver_elapsed_ms"],3)
        state["db_driver_elapsed_ms"]=db_time
        state["total_elapsed_ms"]=round(elapsed,3)
        state["non_db_elapsed_ms"]=round(max(0.0,elapsed-db_time),3)
