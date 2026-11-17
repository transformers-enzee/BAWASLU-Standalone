# v162.1 — Negative QA fixture correction

The v162.0 release build passed frontend checks and 1,206 backend checks, but
one negative test attempted to construct `answer_message_index=0`, correctly
rejected by Pydantic before entering the batch function. The fixture now uses
a schema-valid index of 2 that falls outside the two-message saved conversation,
so it tests the intended `INVALID_ANSWER_TURN` ineligibility handling. The
underlying access-control logic and selection semantics are unchanged.
