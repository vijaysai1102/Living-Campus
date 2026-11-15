# Living Campus — implementation handoff

**All tickets are complete.** F1–F3, 1.1–1.7, 2.1–2.7, 3.1–3.7, and 4.1–4.7 are on `main`.

Repo: `C:\Living-Campus`  
Branch: `main`  
Remote: `https://github.com/vijaysai1102/AI_NPC_Agent.git` (canonical is `Living-Campus`)  
Tests: `C:\Users\vijay\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -v`

Stack stays **Streamlit + SQLite + Groq**. Canon: **Batman** runs `@CSHallwayDrama`. Priya is the decoy rumor.

---

## Done

| Ticket | What landed |
|---|---|
| F1–F3, 1.1–1.7, 2.1–2.3 | Reset, relationship deltas, canon, social graph, gossip, pulse, player identity, typed memories, retrieval |
| 2.4 | Observed traits per NPC (`core/traits.py`) |
| 2.5 | Promises break after 3 ticks (`core/promises.py`) |
| 2.6 | Memory timeline badges, filters, secret lock color |
| 2.7 | Consequence toasts |
| 3.1 | Campus clock, Week 6 Thursday afternoon |
| 3.2 | Chat/leave spend one period; no double-tick |
| 3.3 | Schedules + interruptible gating |
| 3.4 | Time-aware RAG (`due_week`) |
| 3.5 | Schedule-driven mood (prompt-only) |
| 3.6 | Campus map strip |
| 3.7 | While-you-were-away digest |
| 4.1 | Flags + secrets (Instagram learnable in play) |
| 4.2 | Favors (Kevin / Batman / Webb) |
| 4.3 | Prompt hooks from flags |
| 4.4 | Four authored arcs in `data/story/arcs.json` |
| 4.5 | Player journal |
| 4.6 | Finals-week recap + new semester |
| 4.7 | Thresholds in `data/story/thresholds.json` + playtest tests |

Nothing remaining from this handoff.
