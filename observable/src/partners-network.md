---
theme: dashboard
title: Partner–Label Network
toc: false
---

# Partner–Label Network

```js
import * as Plot from "@observablehq/plot";
import * as d3 from "d3";

const data = {
  name: "Partners",
  children: [
    { name: "Partner A", children: [{ name: "Label X" }, { name: "Label Y" }] },
    { name: "Partner B", children: [{ name: "Label Y" }, { name: "Label Z" }] },
  ],
};

function partnerLabelNetwork(data, { width = 600 }) {
  const root = d3.hierarchy(data);
  const treeLayout = d3.tree().size([width - 40, 400 - 40]);
  treeLayout(root);

  const nodes = root
    .descendants()
    .map((d) => ({ x: d.x, y: d.y, name: d.data.name }));
  const links = root
    .links()
    .map((l) => ({ source: l.source, target: l.target }));

  return Plot.plot({
    width,
    height: 400,
    marks: [
      Plot.link(links, {
        x1: (d) => d.source.x,
        y1: (d) => d.source.y,
        x2: (d) => d.target.x,
        y2: (d) => d.target.y,
        stroke: "#999",
      }),
      Plot.dot(nodes, { x: "x", y: "y", r: 4, fill: "steelblue", tip: true }),
      Plot.text(nodes, { x: "x", y: "y", text: "name", dy: -8 }),
    ],
  });
}
```

<div class="grid grid-cols-1">
  <div class="card">
    ${resize((width) => partnerLabelNetwork(data, {}))}
  </div>
</div>
