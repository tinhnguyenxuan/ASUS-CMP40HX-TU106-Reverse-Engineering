# Coordinator review

Job `gsp_callback_target_v1` completed with runner exit code 0. The report's caller, helper, callback load/call, and raw-byte mapping are supported by the saved input checks. The callback target remains an indirect value loaded from context+0x30. The first-entry `a1` value is call-clobbered; the helper-return value reaches `a1` on the back edge. `a2` comes from a stack slot whose helper alias effect is unresolved.

The conclusion that no in-function store reaches context+0x30 is narrower than it sounds: zero syntactic stores to `s3+0x30` does not exclude writes through aliases or callees. The producer of `s3` at 0x04F5739C/0x04F573A0 and context+0x30 writer require further tracing. Job `gsp_context_writer_v1` handles that link. Do not assign a static callback target yet.
