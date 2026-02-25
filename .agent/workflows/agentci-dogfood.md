---
description: Standard per-step workflow for all AgentCI demo agent projects
---

# AgentCI Dogfooding Workflow

> **🎯 AgentCI is the product.** Demo agents are dogfooding vehicles. Every step exists to improve AgentCI.

## Per-Step Workflow

After each implementation step, follow this exact sequence:

### 1. Build → Test (pytest)
- Implement the feature
- Write and run tests (`make test` or `pytest tests/ -v`)
- Fix any failures until all tests pass

### 2. 💥 Intentional Break Demo
- Inject a realistic break (prompt change, agent removal, tool swap, etc.)
- Run `pytest` to show the failure
- Run `python chat.py` for manual interactive testing
- **⏸️ Ask the user to verify the break before reverting**

### 3. 🔄 Apply Learnings to AgentCI
- Ask: "What did we learn about AgentCI? What's missing, broken, or awkward?"
- If there are learnings, **implement them in the AgentCI codebase** (not just note them)
- Examples: new assertions, model fields, adapter fixes, diff engine improvements
- If no learnings, explicitly note "no learnings" and move on

### 4. Revert → Commit → Push
- Revert the intentional break
- Commit both repos (AgentCI + DemoAgents)
- Push to GitHub
- Verify the push landed

## Key Reminders
- Always push to GitHub — local commits are not enough
- Always ask user before reverting break demos
- Learnings must be code, not just notes
- Update `task.md` after each step

## Ad-hoc Improvements

> **AgentCI improvements don't have to wait for the per-step workflow.**
> Any time we discover a gap, bug, or improvement opportunity — during testing, demos, conversation, or manual chat.py exploration — apply it immediately:
> 1. Implement the improvement in AgentCI code
> 2. Add a test in the demo agent if applicable
> 3. Commit and push both repos
