# Agent Prompts

Each file in this directory is a prompt for a specific Claude Code agent session. Agents should be run in order.

## Agent Sequence

| # | File | Purpose | Status |
|---|------|---------|--------|
| 00 | `00_RESEARCH_AGENT.md` | Project blueprint, schema, folder structure | COMPLETE |
| 01 | `01_MIGRATION_AGENT.md` | QuickBooks Online CSV import (run once) | TODO |
| 02 | `02_BUILDER_AGENT_TEMPLATE.md` | Template for all module builders | TEMPLATE |
| 03 | `03_REVIEW_AGENT.md` | QA review of Research Agent output | TODO |
| 04 | `04_GEORGIA_TAX_RESEARCH_AGENT.md` | Georgia DOR rates and form specs | TODO |
| 05 | `05_QB_FORMAT_RESEARCH_AGENT.md` | QuickBooks Online export format analysis | TODO |

## How to Use

1. Open a new Claude Code session
2. Run `/init` to load CLAUDE.md
3. Copy the relevant agent prompt into the conversation
4. The agent will follow its instructions autonomously
5. After completion, check AGENT_LOG.md for the session summary

## Builder Agent Usage

For modules (TASK-001 through TASK-043), copy `02_BUILDER_AGENT_TEMPLATE.md` and fill in the `[BRACKETS]` with the specific module info from WORK_QUEUE.md.
