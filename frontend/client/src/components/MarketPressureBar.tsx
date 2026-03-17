import type { MarketSummary } from "@/hooks/useMarketData";

const SKILL_LABELS: Record<string, string> = {
  none:     '体力',
  tech:     '技术',
  social:   '社交',
  creative: '创意',
  physical: '体力',
};

const LOCATION_SHORT: Record<string, string> = {
  '宝安城中村': '宝安',
  '南山科技园': '南山',
  '福田CBD':   'CBD',
  '华强北':    '华强北',
  '东门老街':  '东门',
  '南山公寓':  '公寓',
  '深圳湾公园':'湾公园',
};

interface Props {
  market: MarketSummary;
}

export function MarketPressureBar({ market }: Props) {
  const entries = Object.entries(market).flatMap(([loc, skills]) =>
    Object.entries(skills).map(([skill, pressure]) => ({ loc, skill, pressure }))
  ).filter(e => e.pressure > 0.5).sort((a, b) => b.pressure - a.pressure).slice(0, 6);

  if (entries.length === 0) return null;

  const maxPressure = Math.max(...entries.map(e => e.pressure), 1);

  return (
    <div className="space-y-1.5">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider">竞争压力</div>
      {entries.map((e, i) => (
        <div key={i} className="flex items-center gap-2">
          <div className="w-14 text-[10px] text-gray-400 truncate">
            {LOCATION_SHORT[e.loc] ?? e.loc}
          </div>
          <div className="w-8 text-[10px] text-gray-500">
            {SKILL_LABELS[e.skill] ?? e.skill}
          </div>
          <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${(e.pressure / maxPressure) * 100}%`,
                backgroundColor: e.pressure > 3 ? '#ff6b6b' : e.pressure > 1.5 ? '#ffd93d' : '#6bcb77',
              }}
            />
          </div>
          <div className="w-6 text-[10px] text-right" style={{
            color: e.pressure > 3 ? '#ff6b6b' : e.pressure > 1.5 ? '#ffd93d' : '#6bcb77'
          }}>
            {e.pressure.toFixed(1)}
          </div>
        </div>
      ))}
    </div>
  );
}
