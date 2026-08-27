# Security policy

## Supported versions

Only the latest release on the default branch receives security fixes during the alpha phase.

## Reporting a vulnerability

Do not open a public issue for leaked credentials, arbitrary code execution, sandbox escape,
hidden-information leakage, or a way for candidate code to alter protected evaluation. Use GitHub's
private vulnerability reporting for this repository. If that feature is unavailable, contact the
maintainer through the private address listed on their GitHub profile.

Include a minimal reproduction, affected revision, impact, and any proposed mitigation. You should
receive an acknowledgement within seven days. Please allow time for a fix before public disclosure.

## Operational cautions

- LLM endpoints receive the generated research packet and prompt. Review both before using a
  third-party endpoint.
- Use a restricted API key and never store it in a proposal, checkpoint, trace, or ledger.
- The current release does not execute LLM-generated source code. Future candidate-code sandboxes
  will be treated as untrusted execution environments.
- This project must not be connected to a live game client or used to automate online play.

