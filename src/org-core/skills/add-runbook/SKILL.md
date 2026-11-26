---
name: add-runbook
description: Write the runbook for an alarm before the alarm is turned on, in docs/runbooks/ of the repository that owns it, and link the alarm to it. Use when adding or changing an alarm, a page, or an SLO burn alert, or when an incident shows a runbook was wrong.
---

# Add a runbook

An alarm is not turned on until its runbook exists. The runbook lives in the repository that defines the alarm.

1. Create `docs/runbooks/<alarm-name>.md`, named exactly like the alarm.
2. Fill in every section below. Write commands a tired person can paste. Do not include secrets, account IDs, or customer data.
3. Put the runbook's path or URL in the alarm's description, so the page carries it.
4. If the alarm is an SLO burn alert, name the SLO, the burn rate, both windows, and the minimum event count.
5. After an incident, fix any step that did not work as written, in the postmortem's pull request.

```markdown
# <Alarm name>

## What it means
<the SLO or condition it watches, the user impact, and the severity it starts at>

## Check first
<dashboards, queries, and commands, in order. Avoid steps that keep a scale-to-zero
database awake longer than needed.>

## Safe mitigations
<each with its command: move the `live` alias back, turn a feature flag off, raise a limit,
fail over, restore. Say which ones are safe to try before the cause is known.>

## Escalate when
<conditions that raise the severity, and who to bring in>

## Related
<threat model rows, the dependency it watches, past incidents>
```
