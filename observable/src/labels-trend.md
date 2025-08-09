---
theme: dashboard
title: Label Trends Over Time
toc: false
---

# Label Trends Over Time

```js
import * as Plot from "@observablehq/plot";

const data = [
  { date: new Date(2025, 0, 1), count: 10 },
  { date: new Date(2025, 1, 1), count: 15 },
  { date: new Date(2025, 2, 1), count: 7 },
];

function labelTrends(data, { width }) {
  return Plot.plot({
    width,
    height: 300,
    x: { label: "Date", tickFormat: "%b %Y" },
    y: { label: "Label Count", grid: true },
    marks: [
      Plot.line(data, { x: "date", y: "count" }),
      Plot.dot(data, { x: "date", y: "count" }),
    ],
  });
}
```

<div class="grid grid-cols-1">
  <div class="card">
    ${resize((width) => labelTrends(data, {width}))}
  </div>
</div>
