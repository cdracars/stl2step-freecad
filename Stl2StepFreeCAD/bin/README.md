# Engine bundles

Release packaging places the verified upstream `stl2step` bundle and its
runtime libraries under `windows-x86_64`. Engine bundles are intentionally
not committed to the source repository.

For a published release, `scripts\\vendor-engine.ps1` downloads the pinned
upstream ZIP and verifies its tag, size, SHA-256, archive contents, and engine
version before placing it here. For development, use
`scripts\\bundle-engine.ps1 -EngineDirectory <directory>` to copy a local build.

For development, set `STL2STEP_EXECUTABLE` to a locally built engine.
