---
name: okf-check
description: Check an OKF v0.3 bundle for frontmatter errors, index descriptions that drift from their concepts, and broken relative links. Use before committing changes to a design bundle, or when asked to check or lint the bundle.
---

# Check the bundle

Run `check_okf.py`, which sits next to this file, from the bundle root:

```bash
python <this skill's folder>/check_okf.py .
```

It prints one problem per line:

- A concept (a `.md` file with a `type`) whose frontmatter lacks `title` or `description`, or whose `type` is not Overview, Lifecycle Stage, Capability, Decision, Reference, or Flow.
- A concept in a subdirectory missing from that directory's `index.md`, or listed there with a description that differs from its frontmatter.
- A relative Markdown link whose target file does not exist.

Fix every line it reports, then run it again until it prints nothing and exits 0.
