# Security policy

## Supported versions

Security fixes are applied to the latest release and the main development
branch. Pre-1.0 releases may change their API between minor versions.

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Report a vulnerability

Use GitHub's private vulnerability reporting form for this repository. Do not
open a public issue for an undisclosed vulnerability.

Include the affected version, Python version, platform, a minimal synthetic
reproduction, expected behaviour, and observed impact. Do not submit real
credentials, customer data, production traces, or third-party personal data.

## Security boundary

The package performs local deterministic computation and writes only to an
explicit `--output` path. It makes no network requests and collects no
telemetry. The random seed is not secret, and the pseudorandom generator is not
suitable for security-sensitive randomness.

Configuration can affect CPU and memory consumption. Do not expose the library
as an unauthenticated multi-tenant service without independent input, resource,
and process isolation controls.
