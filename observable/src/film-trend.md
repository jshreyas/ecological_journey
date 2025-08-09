---
theme: dashboard
title: Film Trends Over Time
toc: false
---

# Film Trends Over Time

```js
const API_BASE_URL = "https://ecological-journey.onrender.com";
import * as Plot from "@observablehq/plot";
import * as d3 from "d3";


import {getTeams} from "./data/teams.js";
import {getPlaylists} from "./data/playlists.js";


const teamData = await getTeams(API_BASE_URL);
const playlistData = await getPlaylists(API_BASE_URL);

// Flatten all videos from all playlists
const videos = playlistData.flatMap(p =>
  (p.videos || []).map(v => ({
    ...v,
    playlist_name: p.name
  }))
);


// Aggregate counts per day per playlist
const counts = d3.rollups(
  videos,
  v => v.length,
  d => d.date.slice(0, 10),
  d => d.playlist_name
).flatMap(([date, playlistCounts]) =>
  playlistCounts.map(([playlist_name, count]) => ({
    date: new Date(date),
    playlist_name,
    count
  }))
);


function videoActivityTimeline(data, { width }) {
  return Plot.plot({
    width,
    height: 300,
    x: { label: "Date" },
    y: { label: "Videos", grid: true },
    color: { legend: true },
    marks: [
      // Plot.line(data, { x: "date", y: "count" }),
      Plot.rectY(data, { x: "date", interval: "month", y: "count", fill: "playlist_name", tip: true, })
    ]
  });
}

```

<div class="grid grid-cols-1">
  <div class="card">
    ${resize((width) => JSON.stringify(teamData, null, 2))}
  </div>
</div>

<div class="grid grid-cols-1">
  <div class="card">
    ${resize((width) => videoActivityTimeline(counts, {width}))}
  </div>
</div>
