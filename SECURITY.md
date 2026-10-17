# Security

People adopt this baseline to secure real deployments, so a wrong recommendation can weaken an organization's posture. Please report anything that could cause harm.

## Reporting a problem

Use GitHub's private reporting: open the **Security** tab of this repository and choose **Report a
vulnerability**. Only the maintainer can see the report. Do not open a public issue for a security
problem, and leave details of your own systems (hostnames, usernames, tokens, logs) out of any
report.

You should get a first answer within a week. This is a one-person project, so a fix may take longer.

## What counts

- A recommendation that, if followed, would weaken security or expose data.
- `examples/managed-settings.json` or another example that does not do what the baseline says.
- A problem in the automation, such as the weekly watcher acting on untrusted content in a way that could change the repository.

A setting that has changed name or moved is a correction, not a security problem. Open a normal issue or pull request for those.

## Before you adopt it

The baseline is provided as is, without warranty (see [LICENSE](LICENSE)). Validate every setting against your own tenant before you rely on it.
