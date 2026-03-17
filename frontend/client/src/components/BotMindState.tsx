import type { BotState } from "@/types/world";
import { getLifeStance, getLifeStanceLabel } from "@/types/world";

interface Props {
  bot: BotState;
}

export function BotMindState({ bot }: Props) {
  const aspiration = bot.aspiration_level ?? 30;
  const riskTolerance = bot.risk_tolerance ?? 0.5;
  const lowTicks = bot._low_motivation_ticks ?? 0;
  const stance = getLifeStance(riskTolerance, lowTicks);
  const stanceInfo = getLifeStanceLabel(stance);

  const opportunities = bot.known_opportunities ?? [];

  return (
    <div className="space-y-3 text-xs">
      {/* 人生态度 */}
      <div className="flex items-center justify-between">
        <span className="text-gray-400">人生态度</span>
        <span style={{ color: stanceInfo.color }} className="font-bold">
          {stanceInfo.emoji} {stanceInfo.label}
        </span>
      </div>

      {/* 期望收入 */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="text-gray-400">期望收入</span>
          <span className="text-white">¥{aspiration.toFixed(0)}/次</span>
        </div>
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(100, (aspiration / 80) * 100)}%`,
              backgroundColor: aspiration > 60 ? '#c77dff' : aspiration > 30 ? '#4d96ff' : '#6bcb77',
            }}
          />
        </div>
      </div>

      {/* 风险偏好 */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="text-gray-400">进取心</span>
          <span className="text-white">{(riskTolerance * 100).toFixed(0)}%</span>
        </div>
        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${riskTolerance * 100}%`,
              backgroundColor: riskTolerance > 0.6 ? '#4d96ff' : riskTolerance > 0.3 ? '#ffd93d' : '#9b59b6',
            }}
          />
        </div>
      </div>

      {/* 已知机会 */}
      {opportunities.length > 0 && (
        <div>
          <div className="text-gray-400 mb-1.5">已知工作机会</div>
          <div className="space-y-1">
            {opportunities.slice(0, 3).map((op, i) => (
              <div key={i} className="flex justify-between items-center bg-gray-800/50 rounded px-2 py-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-gray-300">{op.location}</span>
                  <span className="text-gray-500">·</span>
                  <span className="text-white">{op.title}</span>
                  {op.source !== 'direct' && (
                    <span className="text-gray-500 text-[10px]">({op.source}介绍)</span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-green-400">¥{op.wage_estimate}</span>
                  <div
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: op.confidence > 0.7 ? '#6bcb77' : op.confidence > 0.4 ? '#ffd93d' : '#ff6b6b' }}
                    title={`置信度 ${(op.confidence * 100).toFixed(0)}%`}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
