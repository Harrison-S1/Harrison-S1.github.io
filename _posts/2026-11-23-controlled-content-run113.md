---
layout: post
title: "Controlled publishing check: bounded arithmetic"
date: 2026-11-23 08:00:00 +0000
categories: [engineering]
tags: [automation, validation]
description: "A labelled production integration-test fixture for code, images and passive examples."
render_with_liquid: false
---

## Controlled integration test

This is an intentionally published engineering test fixture, not a production operations guide. Marker: LIVE-CONTENT-RUN113-POSITIVE. The bounded example checks integer arithmetic without importing modules, accessing files, or contacting services. Inline code such as `total = 6 * 7` must remain code when rendered.

## Bounded example

```python
total = 6 * 7
assert total == 42
```

The downloadable [arithmetic example](/examples/posts/controlled-content-run113/check.py) and [numeric data](/examples/posts/controlled-content-run113/data.json) are passive companion assets. The validator interprets only its narrow arithmetic grammar; it does not execute arbitrary contributor programs.

```json
[6, 7, 42, true]
```

## Literal template example

The following template is displayed literally because this post disables Liquid rendering. It is not evaluated by this integration test.

```jinja
{{ total }}
{% if enabled %}bounded-example{% endif %}
```

## Passive image

![Generated blue and green integration test pattern](/assets/img/posts/controlled-content-run113/check.png)

This generated raster is a test pattern, not a screenshot or claimed command output. Its public bytes are checked against the exact merged Git blob and native Pages artifact.
