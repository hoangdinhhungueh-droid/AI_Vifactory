/**
 * voxGeo.ts — Vox Motion Engine 2.0 Pure Mathematical Projection & Route Geometry
 * Deterministic: pure mathematical functions without DOM dependencies or async network calls.
 * 100% Remotion safe for parallel rendering.
 */

export type LonLat = [number, number];
export type Px = [number, number];

export type WaypointKind = 'hub' | 'port' | 'sea' | 'strait' | 'quarantine';

export interface Waypoint {
  id: string;
  labelJa: string;
  labelEn: string;
  coord: LonLat;
  kind: WaypointKind;
  appearFrame: number;
  callout?: {
    valueJa: string;
    noteJa?: string;
    sourceJa?: string;
  };
}

/* ─────────────────────────────────────────────────────────────────────────
 * HẢI TRÌNH THỰC TẾ TRUNG - NHẬT (JP_EP0004: WGS84, [lon, lat])
 * ───────────────────────────────────────────────────────────────────────── */
export const EAST_ASIA_ROUTE: Waypoint[] = [
  {
    id: 'fujian',
    labelJa: '福建省・南平',
    labelEn: 'Nanping, Fujian',
    coord: [118.17, 26.64],
    kind: 'hub',
    appearFrame: 0,
    callout: { valueJa: '原竹供給拠点', noteJa: '竹林集積地', sourceJa: '中国林業統計' },
  },
  {
    id: 'zhejiang',
    labelJa: '浙江省・安吉',
    labelEn: 'Anji, Zhejiang',
    coord: [119.68, 30.64],
    kind: 'hub',
    appearFrame: 15,
    callout: { valueJa: '竹材加工工場', noteJa: '硫黄燻蒸・漂白処理' },
  },
  {
    id: 'ningbo',
    labelJa: '寧波舟山港',
    labelEn: 'Ningbo Port',
    coord: [121.95, 29.94],
    kind: 'port',
    appearFrame: 35,
    callout: { valueJa: '輸出コンテナ積込', noteJa: '対日定期航路' },
  },
  {
    id: 'shanghai',
    labelJa: '上海港・洋山',
    labelEn: 'Shanghai Port',
    coord: [122.06, 30.62],
    kind: 'port',
    appearFrame: 50,
  },
  {
    id: 'east_china_sea',
    labelJa: '東シナ海',
    labelEn: 'East China Sea',
    coord: [126.50, 31.20],
    kind: 'sea',
    appearFrame: 70,
  },
  {
    id: 'osumi',
    labelJa: '大隅海峡',
    labelEn: 'Osumi Strait',
    coord: [130.90, 30.90],
    kind: 'strait',
    appearFrame: 90,
  },
  {
    id: 'kobe',
    labelJa: '神戸港',
    labelEn: 'Port of Kobe',
    coord: [135.19, 34.66],
    kind: 'port',
    appearFrame: 110,
    callout: { valueJa: '第2輸入拠点', sourceJa: '国土交通省 港湾統計' },
  },
  {
    id: 'yokohama',
    labelJa: '横浜港 本牧埠頭',
    labelEn: 'Port of Yokohama',
    coord: [139.66, 35.45],
    kind: 'port',
    appearFrame: 130,
    callout: { valueJa: '対日輸入の41%', noteJa: 'コンテナ通関' },
  },
  {
    id: 'quarantine',
    labelJa: '横浜検疫所・輸入食品検査',
    labelEn: 'Yokohama Quarantine Station',
    coord: [139.68, 35.44],
    kind: 'quarantine',
    appearFrame: 150,
    callout: {
      valueJa: '二酸化硫黄 24倍検出',
      noteJa: '食品衛生法 違反摘発',
      sourceJa: '厚生労働省 検疫所検査記録',
    },
  },
];

/* ─────────────────────────────────────────────────────────────────────────
 * MATHEMATICAL MERCATOR PROJECTION (Zero-Dependency & 100% Deterministic)
 * ───────────────────────────────────────────────────────────────────────── */
export const EAST_ASIA_BBOX = {
  lonMin: 116.0,
  lonMax: 142.5,
  latMin: 24.0,
  latMax: 38.5,
};

export function mercatorProject(
  coord: LonLat,
  width: number,
  height: number,
  padding: number = 80
): Px {
  const [lon, lat] = coord;
  const rad = (d: number) => (d * Math.PI) / 180;
  const mercY = (latDeg: number) => Math.log(Math.tan(Math.PI / 4 + rad(latDeg) / 2));

  const xNorm = (lon - EAST_ASIA_BBOX.lonMin) / (EAST_ASIA_BBOX.lonMax - EAST_ASIA_BBOX.lonMin);
  const yMin = mercY(EAST_ASIA_BBOX.latMin);
  const yMax = mercY(EAST_ASIA_BBOX.latMax);
  const yNorm = (mercY(lat) - yMin) / (yMax - yMin);

  const innerW = width - padding * 2;
  const innerH = height - padding * 2;

  const x = padding + xNorm * innerW;
  const y = height - padding - yNorm * innerH; // Flip Y for screen coordinates

  return [x, y];
}

export interface RoutePolyline {
  points: Px[];
  cumulative: number[];
  totalLength: number;
  svgPathString: string;
}

export function buildRoutePolyline(
  waypoints: Waypoint[],
  width: number,
  height: number,
  padding: number = 80
): RoutePolyline {
  const points: Px[] = waypoints.map((w) => mercatorProject(w.coord, width, height, padding));

  const cumulative: number[] = new Array(points.length).fill(0);
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0];
    const dy = points[i][1] - points[i - 1][1];
    cumulative[i] = cumulative[i - 1] + Math.hypot(dx, dy);
  }

  const totalLength = cumulative[cumulative.length - 1] || 1;
  const svgPathString = points
    .map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`)
    .join(' ');

  return { points, cumulative, totalLength, svgPathString };
}

export function pointAtProgress(
  route: RoutePolyline,
  progress: number
): { pos: Px; headingDeg: number } {
  const { points, cumulative, totalLength } = route;
  if (points.length < 2) return { pos: points[0] || [0, 0], headingDeg: 0 };

  const s = Math.max(0, Math.min(1, progress)) * totalLength;

  let lo = 0;
  let hi = cumulative.length - 1;
  while (lo < hi - 1) {
    const mid = (lo + hi) >> 1;
    if (cumulative[mid] <= s) lo = mid;
    else hi = mid;
  }

  const seg = cumulative[hi] - cumulative[lo];
  const t = seg > 1e-6 ? (s - cumulative[lo]) / seg : 0;
  const pos: Px = [
    points[lo][0] + (points[hi][0] - points[lo][0]) * t,
    points[lo][1] + (points[hi][1] - points[lo][1]) * t,
  ];

  const dx = points[hi][0] - points[lo][0];
  const dy = points[hi][1] - points[lo][1];
  const headingDeg = (Math.atan2(dy, dx) * 180) / Math.PI;

  return { pos, headingDeg };
}
