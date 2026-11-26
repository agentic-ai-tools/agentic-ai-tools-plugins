---
name: add-model-call
description: Add a model call behind a port with untrusted-input handling, schema-validated output, token and spend limits, provenance, and tests including prompt-injection probes. Use when code needs to call an LLM, add a prompt template, add a retrieval source to a prompt, or give a model a tool.
---

# Add a model call

1. **Threat model first.** A new model, prompt family, tool, or retrieval source updates the threat model. Use the `threat-model` skill from `org-core` and fill the STRIDE-AI rows for this call.
2. **Port.** Put the call behind a port (a `typing.Protocol` or TypeScript interface) that takes and returns domain types. Only the adapter imports the provider SDK. Add an in-memory fake that returns scripted outputs for tests.
3. **Prompt template.** Store it in the repository with a version. Build the prompt from the template, the person's text, and retrieved content, each delimited and labelled. Put no secrets and no other tenant's data in it.
4. **Limits before the call.** Check the input size, check the spend cap, and set the timeout and the maximum output tokens.
5. **Output.** Parse into a schema and reject what does not fit. Keep proposed values separate from confirmed ones. Check each value in code before it is used.
6. **Tools.** If the model can call tools, allowlist them for this task and authorize each call in code for the person and tenant.
7. **Provenance and telemetry.** Record the model id, template version, sources, and token counts with the result. Log no prompt or completion text.
8. **Failure.** Decide what happens on timeout, throttling, refusal, and an invalid schema: retry only throttling and transient errors, otherwise fail visibly.
9. **Tests.** Unit tests against the fake for each failure. Add cases to the evaluation set, including an attempt to make the model supply an authoritative value, and add prompt-injection probes through every retrieval source this call reads.
