---
type: Convention
title: Design forks are decided with the maintainer
description: On consequential design choices, lay out the mechanics and honest trade-offs and let the maintainer choose before building.
tags: [process, decisions]
timestamp: 2026-07-27T18:00:41Z
---

# Norm

For a consequential design fork — an architecture choice, a cost/robustness
trade-off, anything hard to reverse — **do not silently pick**:

1. Explain how the options actually work — mechanics, not just labels.
2. Give the honest trade-offs: cost, complexity, failure modes.
3. Offer a recommendation, then let the maintainer choose.

A short clarifying dialogue *before* implementation is welcome and expected.

# Why

The maintainer engages with architecture and wants to understand trade-offs
rather than approve a black-box plan. Building the wrong variant wastes far more
than the conversation costs.

# Example

Deciding how much transcript to feed the classifier, the maintainer paused a
multiple-choice prompt to ask how each option actually worked (token cost, how
date extraction is processed, whole-transcript vs. intro) before choosing the
focused 15–20 min intro. That exploration changed the design — it dropped a
brittle regex date-sweep in favour of letting the model read the prose, because
auto-captions garble exact numbers.

See also [metered-API cost discipline](/conventions/metered-api-cost-discipline.md).
