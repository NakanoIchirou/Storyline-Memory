# Storyline Memory

**A player-reviewed, three-layer narrative memory workflow.**

Storyline Memory represents a continuing story through exactly three kinds of records:

1. Macro-level objective history.
2. Each character's objective experiences, including experiences they have forgotten.
3. Each character's subjective knowledge, beliefs, memories and interpretations.

Pre-story history (`T < 0`) and later events (`T >= 0`) use the same structure. Worldbooks and character cards can be source material or derived views; they are not separate authoritative settings.

## Design

Players explicitly submit TXT batches. An LLM uses [SKILL.md](SKILL.md) to summarize meaningful changes by scene, event and story time. The player reviews the draft before it becomes a committed version. Events can continue across files, and complete versions can be restored.

Characters receive only their currently available subjective cognition and approved perception. Their objective records remain on the world-management side. Forgotten history can support an approved feeling of familiarity without exposing its hidden cause.

Tracked characters' off-screen experiences are proposed at player-triggered story-time checkpoints. There is no real-time world simulation, automatic cast management, per-turn monitoring, Galgame frontend or personality parameter engine.

## Minimal prototype

The Python standard-library helper provides draft preparation, approval hashes, whole-state snapshots, TXT content deduplication, rollback and filtered character-context export. It does not understand TXT, call an LLM or run character agents. The approval hash binds the reviewed content; it is not user authentication.

Read [the local workflow and JSON format](references/local-workflow.md) for usage. The prototype follows its original Windows project convention of storing working data on drive D.

```powershell
$env:TEMP = 'D:\CodexProject\Storyline-Memory\.tmp'
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
python scripts/test_storyline.py
```

The initial prototype passed **8 mechanical tests**, covering pre-zero initialization, private events, cross-file continuation, approval binding, character-package filtering, complete rollback, cast fade-out without deleting archives, and snapshot integrity.

These authored small fixtures do not establish general LLM summarization accuracy, long-term narrative quality, token savings or hard access isolation. A character package does not prevent a host agent from reading shared files; runtime permissions must enforce that boundary separately. This is a single-player, sequential local prototype.

## 中文说明

三层分别回答：世界发生了什么、这个人实际经历了什么、这个人如何认知自己的人生。T=0 是玩家参与的锚点，不是数据结构分界。

归档由玩家主动触发，AI 提取增量并检查冲突，玩家批准后统一提交。未记载不等于未发生；沉默不自动等于原谅；补录客观历史不自动让角色恢复记忆。审核优先提供证据与简短选项，避免把玩家变成档案录入员。

## Attribution and references

Concept and design direction: **NakanoIchirou**. Initial workflow and prototype prepared with Codex assistance on **2026-10-13**. This publication records this implementation and its design scope; it makes no claim that dynamic memory or three-way information models are unprecedented.

See [sources and design review](references/sources.md) for selectively adopted ideas from Smart Memory and existing agent-memory skills. No upstream implementation was copied into this prototype.
