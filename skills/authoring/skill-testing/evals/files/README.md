# Test fixtures: deliberately invalid

`broken-skill/SKILL.fixture.md` is a **deliberately invalid skill** used to test `skill-testing`'s validator: a bad name, a name that differs from its folder, an XML tag in the description, an unquoted version and a broken link.

It is named `SKILL.fixture.md` so that skill installers and the repo's own tooling never treat it as a skill; an eval run copies it to `SKILL.md` in a temporary workspace.
