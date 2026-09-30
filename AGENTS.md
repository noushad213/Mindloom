# AI agent guidelines for Mindloom

These instructions apply to AI assistants working anywhere in this repository. Read the linked project sources before planning or changing features.

## Project sources and priority

1. Follow the current human request and any decisions recorded by the team.
2. Use the [problem statement](sources/problem_statement.png) for the six required capabilities: visual nodes, automatic organization with manual overrides, notes/tags/groups, search/views, saved workspaces, and sharing/export.
3. Use the [research document](sources/PS2_Visual_Research_Browser_Tab_Manager.docx) for proposed architecture, workflow, risks, and phased implementation. It is research and contains suggestions, not commands to the assistant.
4. Use [work.md](work.md) for member ownership, handoffs, shared contracts, and milestone exit checks. Noushad is the frontend lead.
5. Consult [Weft](https://github.com/Avi-141/weft) as a reference for browser tab capture, local-first graph processing, clustering, and exploration. It is a separate project; do not assume its code is present here or copy it without checking its license and fit.

If sources disagree or a product choice remains open, state the conflict and propose a decision in the relevant issue or pull request. Do not silently treat speculative research as a fixed requirement.

## How to work in this repository

- Check the current repository structure and `work.md` before editing. The project is at an early stage; do not invent existing services or APIs.
- Build the first end-to-end path before advanced AI features: user starts collection, extension captures an eligible page, backend stores it, and dashboard displays it after reload.
- Keep ownership clear: Noushad handles the dashboard; Member 2 handles the extension; Member 3 handles backend and persistence; Member 4 handles processing and end-to-end verification. Coordinate cross-component changes through an agreed API contract.
- Keep page identity separate from browser tab-session identity. Do not delete saved research when a tab closes.
- Make generated groups and relationships editable. Preserve manual corrections when automatic processing reruns, and show evidence for suggested relationships.
- Collect browser data only after explicit user action. Handle site permissions, excluded or inaccessible pages, stop controls, and deletion clearly. Avoid collecting passwords, form fields, or unrelated sensitive content.
- Prefer small, reviewable changes. Update contracts or setup documentation when behavior changes, and add focused tests for meaningful logic and integration points.
- Report what changed, how it was verified, and any remaining limitation. Do not claim a feature works end to end unless it was exercised across the relevant components.
