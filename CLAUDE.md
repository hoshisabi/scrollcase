# scrollcase

Personal TTRPG session chronicle tool. Turns session recordings into a living campaign record.

## What it does

1. **Transcript** — pulls from whisper-transcribe (../whisper-transcribe) with speaker diarization
2. **Session summary** — Claude generates a human-readable recap from the corrected transcript
3. **Wiki** — extracts and maintains characters, locations, factions, plot threads across sessions
4. **Achievements** — fun callouts for memorable moments
5. **Site** — publishes everything to GitHub Pages for players to read (no account needed)

## Campaign

- **DM**: Bryan
- **Players**: Brian (Kaelisa), Dan (Oskar), Trey (Cinder), Ken (Araken)
- **System**: D&D 5e

## Design principles

- Each stage is a checkpoint — transcript can be corrected before summary runs, summary before wiki updates
- Errors get caught at the source, not baked in silently
- Audio stays local; only text/images go to GitHub Pages
- No third-party hosting dependency
- `dm/` vs `public/` is the hard privacy boundary — DM notes, full NPC details, raw transcripts, and the DM assistant reports all live under `dm/`; only the player-facing recap and selectively published characters/NPCs/locations go under `public/`
