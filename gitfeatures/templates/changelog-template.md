# {{ branch }}

## Purpose
{{ title or branch }}

{% if linear or background %}
## Background
{% if linear %}
### Ticket
- Identifier: {{ linear.identifier }}
- Title: {{ linear.title }}
{% if linear.state %}- State: {{ linear.state.name }}{% if linear.state.type %} ({{ linear.state.type }}){% endif %}{% endif %}
{% if linear.priority is not none %}- Priority: {{ linear.priority }}{% endif %}
{% if linear.estimate is not none %}- Estimate: {{ linear.estimate }}{% endif %}
{% if linear.team %}- Team: {{ linear.team.key }} — {{ linear.team.name }}{% endif %}
{% if linear.assignee %}- Assignee: {{ linear.assignee.displayName or linear.assignee.name }}{% if linear.assignee.email %} <{{ linear.assignee.email }}>{% endif %}{% endif %}
{% if linear.labels and linear.labels|length > 0 -%}
- Labels: {% for l in linear.labels -%}{{ l.name }}{% if not loop.last %}, {% endif %}{%- endfor %}
{%- endif %}
{% endif %}
{% if background %}
{{ background }}
{% endif %}
{% endif %}

## Changes
{{ changes or "- " }}

## Testing
{{ testing or "- " }}

{% if issue and issue.url %}
## Links
- {{ issue.provider|capitalize }}: {{ issue.url }}
{% endif %}

