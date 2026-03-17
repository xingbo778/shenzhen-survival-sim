/**
 * BotCard - Bot 状态卡片
 * 现代 dashboard 风格，玻璃拟态 + ring 选中态
 */

import { memo } from "react";
import { BOT_COLORS, BOT_ROLES, getDominantEmotion } from "@/types/world";
import type { BotState } from "@/types/world";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

interface Props {
  botId: string;
  bot: BotState;
  isSelected: boolean;
  onClick: () => void;
}

export default memo(function BotCard({ botId, bot, isSelected, onClick }: Props) {
  const color = BOT_COLORS[botId] || "#4d96ff";
  const role = BOT_ROLES[botId] || "居民";
  const emotion = getDominantEmotion(bot.emotions);
  const isDead = bot.status === "dead";
  const hpPct = bot.hp;

  const hpColor = hpPct > 60 ? "bg-green-400" : hpPct > 30 ? "bg-yellow-300" : "bg-red-400";

  return (
    <div
      onClick={onClick}
      className={`relative glass-card p-2.5 cursor-pointer select-none transition-all duration-200 ${
        isSelected
          ? "ring-1 shadow-lg"
          : "hover:bg-white/[0.05]"
      } ${isDead ? "opacity-40" : ""}`}
      style={{
        ...(isSelected ? {
          ringColor: color,
          boxShadow: `0 0 16px ${color}20, 0 0 4px ${color}15`,
          borderColor: `${color}50`,
        } : {}),
      }}
    >
      {/* 头部：头像 + 名字 + 情绪 */}
      <div className="flex items-center gap-2 mb-2">
        {/* 像素头像 */}
        <div
          className="relative shrink-0 flex items-center justify-center rounded-md"
          style={{
            width: 32, height: 32,
            background: `${color}12`,
            border: `1px solid ${color}30`,
          }}
        >
          <svg width="20" height="20" viewBox="0 0 10 10" style={{ imageRendering: "pixelated" }}>
            <rect x="3" y="0" width="4" height="3" fill={color} />
            <rect x="2" y="3" width="6" height="4" fill={color} />
            <rect x="2" y="7" width="2" height="3" fill={color} />
            <rect x="6" y="7" width="2" height="3" fill={color} />
          </svg>
          {bot.is_sleeping && (
            <span className="absolute -top-1 -right-1 text-[10px]">💤</span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            <span className="text-[13px] font-medium truncate" style={{ color }}>
              {bot.name}
            </span>
            <span className="text-[10px] text-muted-foreground">
              {bot.age}岁
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 font-normal" style={{ color, borderColor: `${color}40` }}>
              {role}
            </Badge>
            <span className="text-[11px]">{emotion.emoji}</span>
          </div>
        </div>

        {/* 金钱 */}
        <div className="text-right shrink-0">
          <div className="text-[11px] font-mono-data text-yellow-300">
            ¥{bot.money}
          </div>
          <div className="text-[10px] text-muted-foreground">
            {bot.location?.slice(0, 4)}
          </div>
        </div>
      </div>

      {/* HP 条 (主要指标) */}
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-mono-data w-5 shrink-0 text-muted-foreground">HP</span>
        <Progress
          value={Math.max(0, Math.min(100, hpPct))}
          className={`h-1.5 bg-white/[0.06] [&>[data-slot=progress-indicator]]:${hpColor}`}
        />
        <span className="text-[10px] font-mono-data w-5 text-right shrink-0 text-muted-foreground">
          {Math.round(hpPct)}
        </span>
      </div>

      {/* 能量/饱腹 - 小号辅助指标 */}
      <div className="flex items-center gap-3 mt-1">
        <div className="flex items-center gap-1 flex-1">
          <span className="text-[10px] text-muted-foreground">能</span>
          <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full rounded-full bg-blue-400 transition-all duration-500" style={{ width: `${Math.max(0, Math.min(100, bot.energy))}%` }} />
          </div>
        </div>
        <div className="flex items-center gap-1 flex-1">
          <span className="text-[10px] text-muted-foreground">饱</span>
          <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden">
            <div className="h-full rounded-full bg-orange-400 transition-all duration-500" style={{ width: `${Math.max(0, Math.min(100, bot.satiety))}%` }} />
          </div>
        </div>
      </div>

      {/* 当前活动 */}
      {bot.current_activity && (
        <div className="mt-2 text-[10px] truncate text-muted-foreground" title={bot.current_activity}>
          {bot.current_activity}
        </div>
      )}

      {/* 死亡遮罩 */}
      {isDead && (
        <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-black/50">
          <span className="text-xs text-red-400">已离开</span>
        </div>
      )}
    </div>
  );
})
