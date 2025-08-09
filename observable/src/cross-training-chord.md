---
theme: dashboard
title: Cross-Training Chord Diagram
toc: false
---

# Cross-Training Chord Diagram

```js
import * as d3 from "d3";

function CrossTrainingChord() {
  const matrix = [
    [0, 5, 2],
    [5, 0, 3],
    [2, 3, 0],
  ];
  const names = ["Label A", "Label B", "Label C"];

  const width = 400,
    height = 400;
  const outerRadius = Math.min(width, height) / 2 - 20;
  const innerRadius = outerRadius - 20;

  const chord = d3.chord().padAngle(0.05).sortSubgroups(d3.descending)(matrix);
  const color = d3.scaleOrdinal(d3.schemeCategory10);

  const arc = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);
  const ribbon = d3.ribbon().radius(innerRadius);

  const svg = d3
    .create("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", [-width / 2, -height / 2, width, height])
    .attr("style", "max-width: 100%; height: auto;");

  // Outer arcs
  svg
    .append("g")
    .selectAll("path")
    .data(chord.groups)
    .join("path")
    .attr("fill", (d) => color(d.index))
    .attr("stroke", "#000")
    .attr("d", arc);

  // Labels
  svg
    .append("g")
    .selectAll("text")
    .data(chord.groups)
    .join("text")
    .each((d) => {
      d.angle = (d.startAngle + d.endAngle) / 2;
    })
    .attr("dy", "0.35em")
    .attr(
      "transform",
      (d) => `
        rotate(${(d.angle * 180) / Math.PI - 90})
        translate(${outerRadius + 5})
        ${d.angle > Math.PI ? "rotate(180)" : ""}
      `,
    )
    .attr("text-anchor", (d) => (d.angle > Math.PI ? "end" : null))
    .text((d) => names[d.index]);

  // Ribbons
  svg
    .append("g")
    .attr("fill-opacity", 0.7)
    .selectAll("path")
    .data(chord)
    .join("path")
    .attr("fill", (d) => color(d.target.index))
    .attr("stroke", "#000")
    .attr("d", ribbon);

  return svg.node();
}
```

<div class="grid grid-cols-1">
  <div class="card">
    ${resize((width) => CrossTrainingChord())}
  </div>
</div>
