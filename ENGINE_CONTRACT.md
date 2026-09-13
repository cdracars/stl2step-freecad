# STL to STEP Engine Contract

This contract is shared by the FreeCAD and Fusion 360 wrappers. The host
integration owns its user interface and document import; the engine owns STL
conversion and emits a final `RESULT` record.

## Modes

- `TrueForm`: reconstruct analytic geometry where possible.
- `Verbatim`: preserve the source mesh as faceted STEP geometry.

## Completion

- Exit code `0` means conversion succeeded.
- Exit code `2` means conversion completed with warnings; it is successful only
  when a usable STEP output file exists.
- Exit code `1` and any other non-zero code mean failure unless the adapter's
  documented warning rule applies.

The adapter must parse the final valid `RESULT` record, tolerate progress text
and earlier RESULT-like lines, and report malformed output, missing output,
stderr, and engine failures clearly.

## Host behavior

Conversion is asynchronous and must not block the host UI. A source mesh is
hidden only after the STEP import succeeds. Temporary output is retained when
recovery is useful and removed after a successful import.
