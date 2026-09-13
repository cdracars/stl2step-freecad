# Engine bundles

Release packaging places `stl2step` and its runtime libraries under
`windows-x86_64`, `macos-arm64`, `macos-x86_64`, or `linux-x86_64`.

On Windows, use `scripts\\bundle-engine.ps1 -EngineDirectory <directory>` to
copy `stl2step.exe` and all adjacent OCCT/runtime DLLs into the add-on bundle.
The script validates that the copied engine responds to `--version`.

For development, set `STL2STEP_EXECUTABLE` to a locally built engine.
