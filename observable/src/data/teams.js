// /observable/data/teams.js

export async function getTeams(apiBaseUrl) {
  const res = await fetch(`${apiBaseUrl}/api/teams`);
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}
