# transcripts/

Transcript files corresponding to the reference audio segments.

## Current usage

These transcripts are used for:
- **XTTS v2 fine-tuning** (experimental, via `finetune.py --prepare`) — Whisper re-transcribes the audio but these serve as reference/verification
- Context for the announcer persona — the content demonstrates the tone and style the system prompt is based on

## Naming convention

Transcript filenames describe their content type:

```
Speech_ ...    — Achievement announcement speeches
Discussion_ ...— Item/mechanic explanations
Report_ ...    — Character/creature analyses
Training_ ...  — Skill level-up narrations
```

## Notes

- Plain text, UTF-8 encoded
- Small files, safe to commit to git
