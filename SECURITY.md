# Security policy

## Reporting a vulnerability

Please do not open a public issue for a security vulnerability. Use GitHub's
**Report a vulnerability** option under the repository's **Security** tab, or
contact the repository owner privately through GitHub.

Include the affected version, reproduction steps, impact, and relevant logs.
Remove proprietary model data and credentials before sharing.

The add-on launches a native executable and loads bundled runtime DLLs. Treat
third-party binaries and STL/STEP files as untrusted input, and download
releases only from this repository's GitHub release page.
