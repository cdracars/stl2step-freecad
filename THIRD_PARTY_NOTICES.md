# Third-party notices

## stl2step engine

The bundled `stl2step.exe` is built from the open-source
[`BlinkingSun/stl2step`](https://github.com/BlinkingSun/stl2step) project. The
engine is distributed under the MIT License. Its license text is included in
this repository as `LICENSE.stl2step`.

The executable in this repository is a release binary from the canonical
upstream project; this repository does not claim ownership of the upstream
engine source or its implementation.

## OpenCASCADE Technology (OCCT)

The Windows bundle also contains OCCT runtime libraries required by the engine.
OCCT is a separate dependency distributed under the GNU Lesser General Public
License, version 2.1, with the additional exception described by OCCT. The
official licensing information is available at:

<https://dev.opencascade.org/resources/licensing>

These OCCT libraries are not covered by the add-on's MIT License. Anyone
redistributing or modifying the bundled binaries should review and comply with
the OCCT license, including its requirements for notices and relinking.

## Other runtime libraries

The Windows directory may also contain runtime libraries supplied by the
engine's build toolchain. Their licenses remain those of their respective
projects. The bundle is kept together by the automated engine-update workflow;
inspect the upstream release and binary metadata before repackaging it for a
different platform.
