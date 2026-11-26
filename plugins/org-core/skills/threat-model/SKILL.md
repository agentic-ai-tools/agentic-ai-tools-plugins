---
name: threat-model
description: Create or update a threat model for a system or component with STRIDE, STRIDE-AI for anything that touches a model, likelihood-times-impact scoring, attack chains, and layered defences, written as an OKF concept and checked with check_threat_model.py. Use when adding a repository, a trust boundary, a model, tool, agent, or retrieval source, or an external dependency, or when asked for a threat model or security review of a design.
---

# Threat model

Threat models describe one system, so they live with that system, never in this plugin. This skill keeps every model in the same format so they can be compared and checked.

## Where it goes

- **A system that spans repositories:** the design bundle, next to the product's architecture, as `products/<product>/threat-model.md`. Add the concept's description to that folder's `index.md` in the same change, and set the bundle's slice key (for example `x-d3-slice`).
- **One component:** `docs/threat-model.md` in that component's repository. Link to the system model it belongs to and do not repeat its threats.
- **Updating:** change only the rows the change affects, keep the IDs of rows that still apply, and add a line to Review.

Start from `template.md` next to this file. Keep its headings and table columns exactly.

## Steps

1. **Scope.** The system, the release, and what is out of scope.
2. **Assets.** What an attacker wants: data bodies, credentials and tokens, configuration, decision records, spend, prompts and templates, evaluation sets, the deploy pipeline.
3. **Data flow.** A Mermaid flowchart. Each trust boundary is a `subgraph`. A flow that carries model input or output is dashed (`-.->`), because whoever controls any text reaching the model can steer it.
4. **STRIDE.** For every component and boundary, ask:
   - Spoofing: can a caller claim to be someone it is not?
   - Tampering: can data or code change in transit, at rest, or in the pipeline?
   - Repudiation: can someone deny an action because nothing records it?
   - Information disclosure: can data reach someone who should not see it?
   - Denial of service: can it be made unavailable or too expensive?
   - Elevation of privilege: can a caller gain rights it was not given?
5. **STRIDE-AI**, for every component that builds a prompt or context, calls a model, parses or acts on model output, or stores what a model produced. If none does, write `No component touches a model.` under the heading instead of the table. Ask each question at each layer the component has (User interface, Application, Model, Infrastructure, Data sources):

   | Category | The question | OWASP LLM (2025) |
   | --- | --- | --- |
   | Model Impersonation | Can something pose as a trusted model, model API, or model-backed module? | LLM03 |
   | Data/Model Poisoning | Can someone change what the model learns from or reads at inference time? | LLM04, LLM08 |
   | Provenance Loss | Can an output be traced to the model, prompt, inputs, and sources that produced it? | LLM09 |
   | Model Inversion | Can the model reveal its context, system prompt, or another tenant's data? | LLM02, LLM07 |
   | Resource Exhaustion | Can someone make inference slow or costly? | LLM10 |
   | Alignment Bypass | Can text make the model do what its rules forbid, or act with more authority than the person? | LLM01, LLM05, LLM06 |

   Always add these rows when they apply: Direct prompt injection, Indirect prompt injection (retrieved pages, documents, tool results), Improper output handling (model output rendered, queried, passed to a tool, or stored as confirmed), Excessive agency, Model and prompt supply chain.

   The six categories, the five layers, and the scoring come from STRIDE-AI (Cyrille and Schwarz, 2026, arXiv:2605.17163). The added rows and the control guidance are this skill's.
6. **Score** each row after its listed controls. Likelihood (L) and impact (I) are 1 to 5. Risk is L × I, written as the number and its band:

   | Risk | Band |
   | --- | --- |
   | 20 to 25 | Critical |
   | 12 to 19 | High |
   | 6 to 11 | Medium |
   | 1 to 5 | Low |

   Likelihood 5 is automated and needs almost no skill (direct prompt injection). Impact 5 is data across tenants, credentials, a full safety bypass, or control of the deploy pipeline.
7. **Chains.** Work back from each asset to an entry point, follow every dashed flow to where its output lands (a browser, a query, a tool, a stored value), and pair each threat's end state with the threats of the next component. Score a chain by its end-state impact and its easiest complete path. Common chains: indirect injection to tool misuse; injection to unsafe rendering to token theft; SSRF to the cloud metadata service; a leaked CI token to an infrastructure apply; a secret in a log line.
8. **Layered defences.** A chain whose impact is 5, or whose risk is Critical, names at least two breaking controls on different layers, written `control (Layer); control (Layer)`, using Edge, Identity, Application, Model, Data, or Infrastructure, plus a detection. Independent means one bug, misconfiguration, or bypassed instruction cannot defeat both. A model instruction is never a breaking control.
9. **Controls and tests.** Every row names a control, or `Accepted: <reason>` for Medium and Low. High and Critical rows and chains name a test.
10. **Residual risk.** Every row or chain still High or Critical is listed with its risk register entry.
11. **Review.** The date, the reviewers, and the pull request. High and Critical rows need a second reviewer.

## Check it

```bash
python <this skill's folder>/check_threat_model.py <path to threat-model.md>
```

It checks the frontmatter, the headings, the table columns, the IDs, the scores and bands, chain steps that name real rows, the layered-defence rule, tests on High and Critical rows, and the residual-risk list. Fix every line it prints and run it again until it exits 0. If the model is in an OKF bundle, run the bundle's `okf-check` too.
