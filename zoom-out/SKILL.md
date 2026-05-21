---
name: zoom-out
description: >-
  Zoom out and give broader context or a higher-level perspective on code.
  Use when unfamiliar with a section of code, need to understand how it fits
  into the bigger picture, or navigating vLLM / SGLang / TRT-LLM scheduler,
  KV cache, or serving stack modules.
disable-model-invocation: true
license: MIT
metadata:
  author: Matt Pocock
  upstream: https://github.com/mattpocock/skills/tree/main/skills/engineering/zoom-out
  adapted_for: Saddss/cursor-skills (inference triggers added; otherwise verbatim)
---

> **Vendored from [mattpocock/skills](https://github.com/mattpocock/skills) under MIT.** See `LICENSE-MIT-Matt-Pocock.txt`.

Go up a layer of abstraction. Give a map of all the relevant modules and callers, using the project's domain glossary vocabulary.
