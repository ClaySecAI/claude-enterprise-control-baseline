# Contributing

Corrections are the most useful contribution: a setting that has changed, a control that maps to the
wrong NIST identifier, a recommendation that does not hold in your tenant.

## Cite a primary source

Every claim in the baseline should trace to a primary source: Anthropic's own documentation, release
notes or changelog, or the NIST publication itself. A correction without a source is hard to
accept, because the point of the baseline is that it can be checked. Put the link in the pull
request.

## Run the validators

CI runs these on every pull request. Run them first:

```bash
python3 automation/check_tables.py
python3 automation/check_nist.py
python3 automation/check_settings.py
```

## The weekly watcher

A scheduled workflow checks Anthropic's release notes and changelogs and flags candidates for review
when something may affect the baseline (see [automation/README.md](automation/README.md)). Its files under
`automation/state/` are generated; do not edit them by hand.

## Keep your tenant out of it

Do not paste details of your own deployment: organization IDs, user emails, domain names, policy
exports or screenshots of admin pages. Describe the setting and what you observed.

Security problems are reported privately; see [SECURITY.md](SECURITY.md). Everyone taking part
follows the [code of conduct](CODE_OF_CONDUCT.md).
