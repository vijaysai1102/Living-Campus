# Living Campus — implementation handoff

Continue implementing the remaining tickets. **Do not stop until 2.4–4.7 are done.** After every ticket: run tests, `git commit`, `git push origin HEAD`. If context fills again, update this file and spawn another session the same way.

Repo: `C:\Living-Campus`  
Branch: `main`  
Remote: `https://github.com/vijaysai1102/AI_NPC_Agent.git` (canonical is `Living-Campus`)  
HEAD when this was written: `34d66d9` (2.3 memory retrieval)  
Tests: `C:\Users\vijay\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -v`

PowerShell commit:

```powershell
git commit -m @"
TICKET: short why-focused message.

One more sentence of context.
"@
git push origin HEAD
```

---

## Product

Streamlit campus sim at Westbrook University. Three NPCs (Webb/`professor`, Batman/`friend`, Kevin/`ta`) remember the student, feel emotions, gossip, and now share a social graph. Stack stays **Streamlit + SQLite + Groq**. Do not rewrite the UI framework. Simulate outcomes; do not generate NPC–NPC chats. Author world content in JSON. Every system should be visible in the UI.

Locked defaults: player sets name on welcome; time skip will be visible plus small auto-advance; meters stay visible.

Canon: **Batman** runs `@CSHallwayDrama`. Priya is the decoy rumor.

---

## Done

| Ticket | SHA hint | What landed |
|---|---|---|
| F1 | Honest reset | `core/reset.py` wipes chat, memories, emotions, relationships. Campus reset too. |
| F2 | Relationship deltas | LLM returns `relationship_delta`; clamped −10..10. |
| F3 | Canon | Batman owns the Instagram; Priya is the rumor. |
| 1.1 | Social graph schema | `npc_opinions`, `campus_facts`, `npc_knowledge`. Seeds in `data/npc_opinions.json`. |
| 1.2 | Shareable facts | Prompt + `core/fact_extractor.py`. |
| 1.3 | Gossip rules | `core/gossip_engine.py` `will_share` / `propagate_facts` (immediate, tests). |
| 1.4 | Gossip in prompts | `format_heard_around_campus`. |
| 1.5 | Delayed spread | `pending_gossip`, `campus_state.tick`, `advance_and_resolve` on message start + NPC switch; `queue_new_gossip` after ingest. |
| 1.6 | Campus Pulse | `ui/pulse.py` + `player_pulse()`. Not omniscient. |
| 1.7 | Cross-NPC color | Opinions in prompts; insults tag `about_npc_id`; target sours when they hear. |
| 2.1 | Player identity | `core/player.py`, welcome form, `player_text` in prompts. |
| 2.2 | Typed memories | `kind` (`fact/promise/secret/grievance/favor`), `importance`, `tags`. |
| 2.3 | Retrieval | `get_relevant_memories(npc_id, query, n)` used in chat + openings. Timeline still uses `get_recent_memories`. |

---

## Chat loop (app.py) — do not break this order

On user message:

1. `advance_and_resolve()` (tick + deliver due gossip + queue next hops)
2. Persist user message
3. Build prompt: emotions, relationship, **relevant** memories, RAG, gossip, opinions, player identity
4. Groq JSON: reply, emotion_delta, relationship_delta, memory_*, shareable_facts, keep_secret
5. Apply deltas, increment interactions, optional +2 trust / +1 respect every 5
6. `save_memory` if note
7. `ingest_shareable_facts` then `queue_new_gossip`
8. Save NPC reply, rerun

NPC switch with a previous NPC also calls `advance_and_resolve()`.

Reset hooks live in `core/reset.py`. **Extend them whenever you add tables.** Use `_ensure_column` in `core/database.py` for migrations on existing `data/campus.db`.

Tests patch `config.settings.DB_PATH` **and** `core.database.DB_PATH`, call `init_db()`, use a temp sqlite file. Copy that pattern.

---

## Remaining tickets — implement in this order

### 2.4 Observed traits
Table `player_traits_observed (npc_id, trait, created_at)` unique on (npc_id, trait).  
After a turn, parser field `observed_trait` (optional one adjective). Persist if new.  
Inject into prompt: “How you currently see this student: diligent, untrustworthy”.  
UI on NPC card or under meters: “How they see you”.  
Reset NPC clears that NPC’s traits.  
Webb and Batman can disagree. Tests: two NPCs store different traits; prompt includes them.

### 2.5 Promise tracking
Table `promises (id, npc_id, content, status pending|kept|broken, created_tick, due_tick, memory_id)`.  
When `memory_kind==promise`, insert pending with `due_tick = get_tick()+3` (or parse “Thursday” loosely later).  
On `advance_and_resolve`, if still pending and `due_tick <= tick` and student didn’t visit that NPC in between: mark **broken**, `update_relationship` trust−8, save grievance memory.  
If student talks to that NPC before due and model/heuristic says they followed through (`promise_update: kept`): mark kept, trust+4.  
Simplest heuristic for v1: a later `memory_kind==promise` with tags containing `kept`, or parser field `promise_status`. Prefer an explicit `promise_status` in JSON (`""|"kept"|"broken"`).  
Hook broken-promise checks into `advance_and_resolve` or a `core/promises.py` called from there.

### 2.6 Memory timeline upgrade
`ui/meters.py` `render_memory_timeline`: show kind badge, filter chips (all/promise/secret/grievance), stars for importance≥7, secrets visually distinct (e.g. lock color). Timeline should select `kind` in SQL (already on `get_recent_memories`).

### 2.7 Consequence toast
After a turn, if any relationship axis moved ≥5 **or** gossip was queued/delivered this action, show a Streamlit toast/info: “Kevin’s trust −8” / “Batman might talk”.  
Store previous relationship snapshot before deltas; diff after. Use `st.session_state.last_gossip` already set on ticks. Sidebar or chat column is fine. Tests can unit-test a `format_consequences(before, after, gossip_events)` helper.

---

### Feature 3 — Campus Clock & Places

Simulated time. No real-time waiting. Expand `campus_state` (already has `tick`) with `week`, `weekday`, `period`.

Suggested mapping: start Week 6, Thursday, afternoon (matches the JSON deadlines around May 10–15 — treat week 6 as midterm week).  
Periods: `morning | afternoon | evening | night`. 4 periods = 1 day. 5 weekdays (Mon–Fri) then weekend optional; keep it simple: Mon–Fri only, 12 weeks then finals.

**3.1 Campus clock**  
Columns on `campus_state`: week, weekday, period. Display in sidebar. Persist. Skip-day button. Resume on new sessions. `core/clock.py`. Reset campus restores week 6 Thursday afternoon.

**3.2 Time cost of actions**  
Chat message: +1 period (or +0 if we already ticked via gossip — **do not double-count**). Best: make `advance_and_resolve` the single time source and have clock derive week/day/period from `tick`.  
E.g. tick 0 = W6 Thu afternoon. Each tick = one period. 4 ticks = next weekday.  
Switching NPCs already ticks once (travel). Long chat with Webb can make you miss Kevin’s hours.  
Visible “Leave / next period” and “Skip to next day” buttons.

**3.3 NPC schedules & availability**  
`data/schedules.json`: for each npc_id, list `{weekday, period, location, interruptible}`.  
Locations: Webb’s office, Lab 204, The Dungeon, Quad, Kevin’s cubicle (Room 203), lecture hall.  
If NPC is not interruptible, chat is a short caught-in-the-hall line or a note — gate in `app.py` before full `generate_response`. Opening still allowed if interruptible.

**3.4 Time-aware RAG**  
Add `week` / `due_week` (int) to events.json and assignments.json items. Retriever boosts due-soon (`due_week == current or current+1`) and hides expired (`due_week < current`). Openings should be able to mention this week’s midterm. Update JSON; don’t leave May dates as the only signal.

**3.5 Schedule-driven mood**  
Before prompt, apply temporary modifiers (do not persist unless you also store a `base` — easiest: compute `effective_emotions = base + schedule_mod` for the prompt only). Kevin +stress on grading days; Batman +excited Friday evening; Webb +annoyed midterm week (week>=6). `core/emotion_engine.py` helper `mood_for_prompt(npc_id, emotions, clock)`.

**3.6 Campus map strip**  
Location chips. Who is here now. Clicking a place lists NPCs present; talk to them. This becomes the primary way to start a chat; keep sidebar NPC list as fallback.

**3.7 While you were away**  
On session start or skip-day: 2–4 lines from gossip_log + approaching deadlines + clock. `st.info` or welcome panel. Generate from data, not an extra LLM call (optional one-liner LLM later — skip if it costs).

---

### Feature 4 — Secrets, Favors, Endings

Content-driven. LLM performs; JSON authors beats.

**4.1 Flags + secrets**  
`data/story/secrets.json` + table `flags (key TEXT PRIMARY KEY, value TEXT)`.  
Secrets: id, holder, discovery_conditions, leak_consequences, campus_fact template. States: unknown / suspected / known / leaked.  
Include Batman Instagram secret (player can learn without reading JSON).

**4.2 Favors**  
`data/story/favors.json`: requested_by, conditions (relationship thresholds + week), success/fail effects.  
Kevin: stop 2am emails. Batman: don’t tell. Webb: attend the BBQ.  
NPCs ask once when conditions pass (inject into prompt as a hook). Track `favor_status` table.

**4.3 Prompt hooks**  
`core/story_engine.py` at conversation start: if flags/conditions match, append a HOOK block (“If trust>60 and week>=5, you almost slip about the Instagram”). Never invent new quests.

**4.4 Author four arcs** in `data/story/`  
1. Webb — recommendation / MOSS / Dean AI fight  
2. Kevin — real help vs dumping work; leaked study guide  
3. Batman — Instagram identity; expose / join / get posted  
4. Campus-wide — midterm week + hackathon  
Each arc ≥3 beats: hook, pressure, resolution. Existing NPCs only.

**4.5 Player journal**  
UI: open favors, known secrets, upcoming deadlines. Make the game legible. Sidebar expander is enough.

**4.6 Semester ending**  
When clock hits finals week (week>=12 or week==11 Friday night): recap screen from flags + relationships + key memories. One LLM recap prompt citing real flags is OK. Then “Start a new semester” = `reset_campus()` (keep player name).

**4.7 Playtest / thresholds**  
Tune: pleasing-everyone vs chaos runs should differ; Instagram learnable in play; gossip delays still let you beat Webb; promises can break overnight. Add tests for story flag transitions and ending tags rather than live Groq. Document thresholds in `data/story/thresholds.json` if you touch magic numbers.

---

## Design rules

1. Simulate outcomes; don’t generate a whole campus of extra LLM calls.  
2. New rumors/favors/secrets go in data files.  
3. If trust dropped or a rumor spread, show it.  
4. One player, local SQLite.  
5. Stay on Streamlit.  
6. Extend `reset.py` for every new table.  
7. Unit tests with temp DB; no Groq in tests.

## After 4.7

Update README to describe the living campus (gossip, clock, story). Leave HANDOFF with “all tickets complete”.
