# Traces Folder Layout

This folder stores generated company briefs grouped by company slug.

## Structure

- `traces/<company>/enrichment_sample.json`
- `traces/<company>/hiring_signal_brief.json`
- `traces/<company>/competitor_gap_brief.json`

## Why this layout

- Keeps all artifacts for one company together.
- Avoids long duplicated filename prefixes.
- Makes it easier to archive, diff, or delete per-company traces.
