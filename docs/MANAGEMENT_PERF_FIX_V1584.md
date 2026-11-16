# v158.4 connection-only SQLAlchemy event compatibility fix

The initial v158.3 CI build failed because SQLAlchemy 2.x does not support handle_error listeners on a Connection; they are dialect-level. Removed the invalid listener and retained connection-local before/after execution timing, with guaranteed cleanup on exit. The measured query count only covers completed statements; a DB exception prevents a successful diagnostic response. No default enablement, report data changes, production database writes or manual acceptance changes.
