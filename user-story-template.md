# Purpose
{{ title or branch }}

# Problem Statement
{{ background or "" }}

# Desired Outcome (Success Criteria)
- [ ] 

# Scope
- In scope: 
- Out of scope: 

# User Story (optional)
As a <role>, I want <capability> so that <benefit>.

# Acceptance Criteria (Given/When/Then)
- Given …
  When …
  Then …

# Codebase Context
- Repo: {{ repo_full_name }}
- Branch: {{ branch }}
- Ticket: {{ ticket or "" }}
- Base branch: {{ master_branch }}
- External APIs: GitHub REST (PRs){% if linear and linear.identifier %}, Linear issue {{ linear.identifier }}{% endif %}

# Technical Requirements
- Interfaces/CLI: 
- Data/Schema changes: 
- API contracts: 
- Security/Privacy: 
- Performance/Constraints: 
- Observability: 

# Rollout & Migration
- Feature flag or env guard: 
- Backward compatibility plan: 
- Migration steps (if any): 
- Rollback plan: 

# Testing Plan
- Unit tests: 
- Integration/e2e/manual checks: 
- Cross-platform notes: 

# Risks & Mitigations
- 

# Implementation Notes (if any)
- 

# Links & References
{% if linear and linear.url -%}
- Linear: {{ linear.url }}
{% endif %}

# Changelog Seed (used to prefill ./changelog/<branch>.md)
Title: {{ title or branch }}
Background:
{{ background or "" }}
Changes:
{{ changes or "- " }}
Testing:
{{ testing or "- " }}

