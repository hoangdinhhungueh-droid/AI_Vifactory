# Sources and rights

## Upstream engine

- Project: **Papertrails — explore an endless paper world**.
- Repository: https://github.com/xikhar/papertrails
- Author/notice: **Copyright (c) 2026 Shikhar**.
- Imported source revision: **5a284f71164ea3bd54ee788553e21f7f21a1b7b7** (`main` at inspection).
- Original license retained unchanged at `engine/LICENSE`: MIT.
- Imported source/asset tree retained in `engine/`; video-specific modules and scripts are adaptation additions. The original game is not replaced.
- Scope: the repository carries an MIT notice; no separate per-asset rights audit was represented by its short README. For distribution requiring a stronger provenance warranty, verify asset authorship with the upstream author. Do not claim trademark/likeness/voice rights from the code license.

## Adaptation

New skill workflow, voice pipeline, timeline director guidance, renderer integration, installer, and tests are distributed under the root MIT LICENSE. This package is an independent adaptation, not an official upstream Papertrails release or endorsement by any agent vendor.

## Dependencies

Dependencies retain their own licenses in installed package distributions. npm/Python locks pin runtime packages; they are not relicensed as original work. Core tools: Three.js, Vite, Playwright, FFmpeg, faster-whisper/CTranslate2, and model weights fetched separately from their providers. FFmpeg binary build options can affect its redistribution terms; this package expects a locally installed binary and does not bundle one.

## Agent compatibility references

The local directory structure follows these official sources, consulted while building this package:

- Claude Code skills: https://code.claude.com/docs/en/skills
- Cursor Agent Skills: https://cursor.com/docs/skills
- Codex/ChatGPT skill authoring: https://developers.openai.com/codex/skills (redirected to https://learn.chatgpt.com/docs/build-skills at inspection)
- Hermes skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Portable Agent Skills format: https://agentskills.io/specification

Only portable frontmatter fields are used in SKILL.md. Runtime execution still requires shell/file/WebGL capabilities in the actual agent environment. A package-format check does not prove that all four applications were launched or can render in every hosted sandbox.

## Audio and output

The user's original voice is copied into each project, never replaced by cloned/synthetic speech. Permission to use that recording is independent of this code license. No stock music is downloaded by this skill. Synthetic speech and silence used during engineering tests are marked as fixtures and excluded from the portable ZIP; they are not a user's narration or a requested creative demo.
