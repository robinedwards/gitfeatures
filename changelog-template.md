# {{ branch }}

## Purpose
{{ title or branch }}

{% if background %}
## Background
{{ background }}
{% endif %}

## Changes
{{ changes or "- " }}

## Testing
{{ testing or "- " }}

{% if issue and issue.url %}
## Links
- {{ issue.provider|capitalize }}: {{ issue.url }}
{% endif %}

