// /observable/data/playlists.js

export async function getPlaylists(apiBaseUrl) {
  const res = await fetch(`${apiBaseUrl}/api/playlists`);
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}
