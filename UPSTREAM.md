# Upstream Tracking

This project is a fork of [okta-mcp-server](https://github.com/okta/okta-mcp-server).

All customizations are tracked in `customizations/manifest.yaml` and applied via `custom_server.py`.
The `src/okta_mcp_server/` directory mirrors the upstream source and should not be modified directly —
exceptions must be documented in the manifest with type `patch_file`.

## Upstream Source

| Field | Value |
|-------|-------|
| Repository | https://github.com/okta/okta-mcp-server |
| Last synced tag | v1.1.0 |
| Last synced commit | 05121c9 |
| Synced date | 2026-05-16 |

## Sync Process

When a new upstream release is available:

1. Review the upstream changelog and release notes.
2. Compare upstream changes against your customizations in `customizations/manifest.yaml`:
   - Check that `override_tool` entries still make sense given upstream changes to the base tool.
   - Check that `remove_tool` entries haven't been made obsolete.
   - Check that `add_tool` entries don't duplicate newly added upstream tools.
3. Apply upstream changes to `src/okta_mcp_server/` (copy/patch from the upstream release).
4. Run tests: `uv run pytest`
5. Update the table above with the new tag, commit, and date.
6. Commit: `git commit -m "chore: sync upstream v<version>"`
