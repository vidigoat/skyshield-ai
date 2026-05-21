/**
 * Synthetic Starlink-like LEO catalog for the demo globe before the live
 * Celestrak feed is wired up. Generates ~3000 satellites distributed across
 * the Starlink shells (550 km, 53° inclination + variants).
 *
 * Output: array of {norad_id, lat, lng, alt} ready to feed globe.gl.
 */

export type SatPoint = {
  id: number;
  name: string;
  lat: number;
  lng: number;
  alt: number;       // altitude / Earth radius (globe.gl convention)
  risk: number;      // 0..1, fraction used for color
};

const EARTH_R_KM = 6378.137;

export function generateStarlinkCatalog(seed = 42, n = 3000): SatPoint[] {
  // Simple PRNG (mulberry32) for deterministic output
  let s = seed >>> 0;
  const rand = () => {
    s |= 0;
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const shells = [
    { alt: 550, inc: 53.0, share: 0.40 },
    { alt: 540, inc: 53.2, share: 0.20 },
    { alt: 570, inc: 70.0, share: 0.15 },
    { alt: 560, inc: 97.6, share: 0.15 }, // sun-synchronous
    { alt: 350, inc: 38.0, share: 0.10 },
  ];

  const out: SatPoint[] = [];
  for (let i = 0; i < n; i++) {
    let pick = rand();
    let shell = shells[0];
    for (const s of shells) {
      if (pick < s.share) { shell = s; break; }
      pick -= s.share;
    }
    // True anomaly + RAAN uniform on circle
    const meanAnom = rand() * 360;
    const raan = rand() * 360;
    const inc = shell.inc + (rand() - 0.5) * 0.5;

    // Convert orbital elements to (lat, lng) at this instant (simplified — no time evolution)
    const lat = Math.asin(Math.sin(inc * Math.PI / 180) * Math.sin(meanAnom * Math.PI / 180)) * 180 / Math.PI;
    const lng = ((raan + meanAnom * Math.cos(inc * Math.PI / 180)) % 360) - 180;
    out.push({
      id: 30000 + i,
      name: `STARLINK-${30000 + i}`,
      lat,
      lng,
      alt: shell.alt / EARTH_R_KM,
      risk: 0,
    });
  }

  // Sprinkle in some "high-risk" conjunctions (red dots)
  for (let i = 0; i < 20; i++) {
    const v = out[Math.floor(rand() * out.length)];
    v.risk = 0.6 + rand() * 0.4;
  }
  return out;
}

export function satColor(risk: number): string {
  // 0 = cyan (safe), 1 = red (danger)
  if (risk < 0.05) return "#3aa9ff";
  if (risk < 0.5) return "#ffae42";
  return "#ff3b3b";
}
