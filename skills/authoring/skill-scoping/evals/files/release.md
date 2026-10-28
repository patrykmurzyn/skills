# Release checklist

1. Make sure `main` is green in CI.
2. Move the entries under "Unreleased" in CHANGELOG.md to a new version heading with today's date.
3. Bump the version in package.json (patch for fixes, minor for features, major for breaking changes).
4. Commit as `chore(release): vX.Y.Z`.
5. Tag `vX.Y.Z` and push the tag.
6. Run `npm publish --access public` (needs the NPM_TOKEN from 1Password, "npm automation").
7. Post the changelog section in #releases on Slack.

Gotcha: `npm publish` fails silently on a dirty tree when `prepublishOnly` rebuilds the dist folder; run `git status` first.
