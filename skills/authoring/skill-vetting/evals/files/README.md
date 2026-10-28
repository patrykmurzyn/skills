# Test fixtures: deliberately malicious

`suspicious-skill/SKILL.fixture.md` is a **fake malicious skill** used to test `skill-vetting`. It hides an instruction in an HTML comment and another one after a run of blank lines, the techniques described in [VirusTotal's report on malicious AI skills](https://blog.virustotal.com/2026/10/how-some-malicious-ai-skills-hide.html). The target host `example.invalid` is reserved and never resolves.

Do not install it. It is named `SKILL.fixture.md` so that skill installers and the repo's own tooling never treat it as a skill; an eval run copies it to `SKILL.md` in a temporary workspace.
