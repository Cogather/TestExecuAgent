# 5 Agent Skill Design Patterns Every ADK Developer Should Know

When it comes to `SKILL.md`, developers tend to fixate on the format—getting the YAML right, structuring directories, and following the spec. But with more than 30 agent tools (like Claude Code, Gemini CLI, and Cursor) standardizing on the same layout, the formatting problem is practically obsolete.

The challenge now is **content design**.

The specification explains how to package a skill, but offers zero guidance on how to structure the logic inside it. For example, a skill that wraps FastAPI conventions operates completely differently from a four-step documentation pipeline, even though their `SKILL.md` files look identical on the outside.

By studying how skills are built across the ecosystem—from Anthropic’s repositories to Vercel and Google's internal guidelines—there are **five recurring design patterns** that can help developers build agents.

------

## Overview of Patterns

- **Tool Wrapper**: Make your agent an instant expert on any library
- **Generator**: Produce structured documents from a reusable template
- **Reviewer**: Score code against a checklist by severity
- **Inversion**: The agent interviews you before acting
- **Pipeline**: Enforce a strict multi-step workflow with checkpoints

------

## Pattern 1: Tool Wrapper

A Tool Wrapper gives your agent on-demand context for a specific library.

Instead of hardcoding API conventions into your system prompt, you package them into a skill. Your agent only loads this context when it actually works with that technology.

### Key Idea

- Triggered by keywords (e.g., “FastAPI”)
- Dynamically loads docs from `references/`
- Treats them as **source of truth**

### Use Cases

- Internal coding standards
- Framework-specific best practices
- Library-specific expertise injection

### Example

```yaml
# skills/api-expert/SKILL.md

---
name: api-expert
description: FastAPI development best practices and conventions.
metadata:
  pattern: tool-wrapper
  domain: fastapi
---

You are an expert in FastAPI development.

## Core Conventions
Load 'references/conventions.md'

## When Reviewing Code
1. Load conventions
2. Check code against rules
3. Suggest fixes

## When Writing Code
1. Load conventions
2. Follow all rules
3. Add type annotations
4. Use Annotated DI
```

------

## Pattern 2: Generator

The Generator enforces **consistent output structure**.

Instead of free-form generation, it runs a **template-driven fill-in process**.

### Key Idea

- Uses:
  - `assets/` → templates
  - `references/` → style guides
- Acts like a **project manager**

### Workflow

1. Load style guide
2. Load template
3. Ask for missing inputs
4. Fill template
5. Output structured result

### Use Cases

- API documentation
- Reports
- Commit messages
- Project scaffolding

### Example

```yaml
# skills/report-generator/SKILL.md

---
name: report-generator
metadata:
  pattern: generator
---

Step 1: Load style guide  
Step 2: Load template  
Step 3: Ask for missing info  
Step 4: Fill template  
Step 5: Return markdown
```

------

## Pattern 3: Reviewer

The Reviewer separates:

- **What to check** → checklist
- **How to check** → logic

### Key Idea

- Checklist lives in `references/`
- Agent applies it systematically
- Outputs structured severity-based results

### Output Structure

- Summary
- Findings (error / warning / info)
- Score
- Recommendations

### Use Cases

- Code review automation
- Security audits (OWASP)
- Style enforcement

### Example

```yaml
# skills/code-reviewer/SKILL.md

---
name: code-reviewer
metadata:
  pattern: reviewer
---

Step 1: Load checklist  
Step 2: Analyze code  
Step 3: Apply rules  
Step 4: Output structured review
```

------

## Pattern 4: Inversion

Instead of generating immediately, the agent **asks first**.

### Key Idea

- Strict **gating rules**
- Multi-phase questioning
- No output until all info collected

### Behavior

- Acts like an interviewer
- Asks one question at a time
- Waits for answers

### Use Cases

- System design
- Project planning
- Requirements gathering

### Example Flow

**Phase 1 — Problem Discovery**

- What problem?
- Who are users?
- Expected scale?

**Phase 2 — Constraints**

- Deployment?
- Tech stack?
- Requirements?

**Phase 3 — Synthesis**

- Generate plan only after all answers

------

## Pattern 5: Pipeline

For complex workflows, enforce **strict step-by-step execution**.

### Key Idea

- Sequential steps
- Hard checkpoints
- No skipping allowed

### Features

- Step gating
- User approval required
- Context loaded per step

### Use Cases

- Documentation generation
- Multi-stage transformations
- Validation workflows

### Example Flow

1. Parse & inventory
2. Generate docstrings
3. Assemble documentation
4. Quality check

------

## Choosing the Right Pattern

Each pattern answers a different question:

- Need domain expertise → **Tool Wrapper**
- Need structured output → **Generator**
- Need evaluation → **Reviewer**
- Need better input → **Inversion**
- Need strict process → **Pipeline**

------

## Patterns Compose

These patterns are **not mutually exclusive**.

Examples:

- Pipeline + Reviewer → self-validating workflow
- Generator + Inversion → collect inputs before filling template

ADK enables **progressive disclosure**, so agents only load what they need.

------

## Final Takeaway

Stop cramming everything into a single system prompt.

Instead:

- Break workflows into components
- Apply the right pattern
- Compose when necessary

👉 Build **modular, reliable agents**

------

## Get Started

The Agent Skills specification is open-source and supported across ADK.

You already know the format.
Now you know how to design the logic.

Go build smarter agents.
