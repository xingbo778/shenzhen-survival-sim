/**
 * RightPanel - 右侧信息面板
 * 标签页：事件流 / 朋友圈 / 地点详情
 */

import type { WorldState, Moment } from "@/types/world";
import { BOT_COLORS, LOCATION_MAP_CONFIG } from "@/types/world";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Zap, Smartphone, MapPin } from "lucide-react";
import { useState, useMemo, memo } from "react";
import { MarketPressureBar } from "./MarketPressureBar";
import { useMarketData } from "@/hooks/useMarketData";

const LOC_NAMES = Object.keys(LOCATION_MAP_CONFIG);

interface Props {
  world: WorldState | null;
  moments: Moment[];
  selectedLocation: string | null;
  onBotClick: (botId: string) => void;
}

function RightPanel({ world, moments, selectedLocation, onBotClick }: Props) {
  const market = useMarketData();
  return (
    <Tabs defaultValue="events" className="h-full flex flex-col gap-0 glass-panel-solid border-0">
      {/* 标签栏 */}
      <TabsList className="w-full rounded-none border-b border-white/[0.06] bg-transparent h-9 p-0 shrink-0">
        <TabsTrigger value="events" className="flex-1 rounded-none text-xs gap-1.5 data-[state=active]:bg-white/[0.04] data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary">
          <Zap className="size-3.5" /> 事件流
        </TabsTrigger>
        <TabsTrigger value="moments" className="flex-1 rounded-none text-xs gap-1.5 data-[state=active]:bg-white/[0.04] data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary">
          <Smartphone className="size-3.5" /> 朋友圈
        </TabsTrigger>
        <TabsTrigger value="location" className="flex-1 rounded-none text-xs gap-1.5 data-[state=active]:bg-white/[0.04] data-[state=active]:shadow-none border-b-2 border-transparent data-[state=active]:border-primary">
          <MapPin className="size-3.5" /> 地点
        </TabsTrigger>
      </TabsList>

      {/* 内容区 */}
      <TabsContent value="events" className="flex-1 overflow-y-auto mt-0">
        <EventsTab world={world} onBotClick={onBotClick} />
      </TabsContent>
      <TabsContent value="moments" className="flex-1 overflow-y-auto mt-0">
        <MomentsTab moments={moments} world={world} />
      </TabsContent>
      <TabsContent value="location" className="flex-1 overflow-y-auto mt-0">
        <LocationTab world={world} selectedLocation={selectedLocation} onBotClick={onBotClick} market={market} />
      </TabsContent>
    </Tabs>
  );
}

export default memo(RightPanel)

// ===== 事件流 =====
function EventsTab({ world, onBotClick }: { world: WorldState | null; onBotClick: (id: string) => void }) {
  const events = useMemo(() => {
    if (!world) return [];
    const result: { time: string; botId: string; botName: string; text: string; color: string }[] = [];
    Object.entries(world.bots).forEach(([botId, bot]) => {
      if (bot.status !== "alive") return;
      const color = BOT_COLORS[botId] || "#4d96ff";
      const logs = bot.action_log || [];
      if (logs.length > 0) {
        const last = logs[logs.length - 1];
        result.push({
          time: last.time?.slice(11, 16) || "",
          botId,
          botName: bot.name,
          text: last.result?.narrative || last.plan || bot.current_activity || "...",
          color,
        });
      } else if (bot.current_activity) {
        result.push({
          time: "",
          botId,
          botName: bot.name,
          text: bot.current_activity,
          color,
        });
      }
    });
    return result;
  }, [world]);

  if (!world) return <EmptyState text="等待连接..." />;

  const worldEvents = world.events || [];

  return (
    <div className="p-2 space-y-1.5">
      {/* 世界事件 */}
      {worldEvents.slice(-3).reverse().map((ev, i) => (
        <div
          key={`we-${i}`}
          className="p-2.5 rounded-md glass-card animate-fade-in-up"
          style={{ borderColor: "rgba(255,217,61,0.15)" }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-xs text-yellow-300">🌐 世界事件</span>
            <span className="text-[10px] text-muted-foreground/40">{ev.time?.slice(11, 16)}</span>
          </div>
          <div className="text-xs text-foreground/70">{ev.desc || ev.event}</div>
        </div>
      ))}

      {/* Bot 行动 */}
      {events.map((ev, i) => (
        <div
          key={i}
          className="p-2.5 rounded-md glass-card cursor-pointer transition-colors animate-fade-in-up"
          onClick={() => onBotClick(ev.botId)}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-xs font-medium" style={{ color: ev.color }}>{ev.botName}</span>
            {ev.time && <span className="text-[10px] text-muted-foreground/40">{ev.time}</span>}
          </div>
          <div className="text-xs leading-relaxed text-foreground/60">
            {ev.text.slice(0, 80)}
          </div>
        </div>
      ))}

      {events.length === 0 && <EmptyState text="暂无事件" />}
    </div>
  );
}

// ===== 朋友圈 =====
function MomentsTab({ moments, world }: { moments: Moment[]; world: WorldState | null }) {
  const recentMoments = useMemo(() => [...moments].reverse().slice(0, 20), [moments]);

  if (moments.length === 0) return <EmptyState text="朋友圈空空如也..." />;

  return (
    <div className="p-2 space-y-2">
      {recentMoments.map(moment => {
        const bot = world?.bots[moment.bot_id];
        const color = BOT_COLORS[moment.bot_id] || "#4d96ff";

        return (
          <div key={moment.id} className="p-2.5 rounded-md glass-card animate-fade-in-up">
            {/* 发布者 */}
            <div className="flex items-center gap-2 mb-2">
              <div
                className="flex items-center justify-center rounded-md"
                style={{ width: 24, height: 24, background: `${color}12`, border: `1px solid ${color}30` }}
              >
                <svg width="14" height="14" viewBox="0 0 10 10" style={{ imageRendering: "pixelated" }}>
                  <rect x="3" y="0" width="4" height="3" fill={color} />
                  <rect x="2" y="3" width="6" height="4" fill={color} />
                  <rect x="2" y="7" width="2" height="3" fill={color} />
                  <rect x="6" y="7" width="2" height="3" fill={color} />
                </svg>
              </div>
              <div>
                <div className="text-xs font-medium" style={{ color }}>{moment.bot_name}</div>
                <div className="text-[10px] text-muted-foreground/40">
                  {moment.time?.slice(11, 16)} · {bot?.location || ""}
                </div>
              </div>
            </div>

            {/* 内容 */}
            <div className="text-xs leading-relaxed mb-2 text-foreground/75">
              {moment.content}
            </div>

            {/* 互动 */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground/40">
                ❤️ {moment.likes?.length || 0}
              </span>
              <span className="text-xs text-muted-foreground/40">
                💬 {moment.comments?.length || 0}
              </span>
            </div>

            {/* 评论 */}
            {moment.comments && moment.comments.length > 0 && (
              <div className="mt-2 p-2 rounded-md space-y-1 bg-white/[0.02] border border-white/[0.06]">
                {moment.comments.slice(-2).map((c, i) => (
                  <div key={i} className="text-xs">
                    <span style={{ color: BOT_COLORS[c.bot_id] || "#4d96ff" }}>{c.bot_name}: </span>
                    <span className="text-foreground/55">{c.content}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ===== 地点详情 =====
function LocationTab({
  world, selectedLocation, onBotClick, market
}: {
  world: WorldState | null;
  selectedLocation: string | null;
  onBotClick: (id: string) => void;
  market: import("@/hooks/useMarketData").MarketSummary;
}) {
  const [viewLoc, setViewLoc] = useState<string | null>(null);
  const displayLoc = viewLoc || selectedLocation;

  if (!world) return <EmptyState text="等待连接..." />;

  return (
    <div className="p-2">
      {/* 地点选择 */}
      <div className="flex flex-wrap gap-1 mb-3">
        {LOC_NAMES.map(loc => {
          const cfg = LOCATION_MAP_CONFIG[loc];
          const count = world.locations[loc]?.bots?.length || 0;
          const isActive = displayLoc === loc;
          return (
            <Badge
              key={loc}
              variant={isActive ? "default" : "outline"}
              className="text-[10px] cursor-pointer font-normal transition-colors"
              style={isActive ? {
                background: `${cfg.color}20`,
                borderColor: `${cfg.color}50`,
                color: cfg.color,
              } : {}}
              onClick={() => setViewLoc(loc)}
            >
              {cfg.icon} {loc.slice(0, 4)} {count > 0 && <span className="text-red-400 ml-0.5">·{count}</span>}
            </Badge>
          );
        })}
      </div>

      <MarketPressureBar market={market} />

      {displayLoc && world.locations[displayLoc] ? (
        <LocationDetail
          name={displayLoc}
          data={world.locations[displayLoc]}
          bots={world.bots}
          onBotClick={onBotClick}
        />
      ) : (
        <EmptyState text="点击地点查看详情" />
      )}
    </div>
  );
}

function LocationDetail({
  name, data, bots, onBotClick
}: {
  name: string;
  data: WorldState["locations"][string];
  bots: WorldState["bots"];
  onBotClick: (id: string) => void;
}) {
  const cfg = LOCATION_MAP_CONFIG[name];

  return (
    <div className="space-y-3">
      {/* 地点头部 */}
      <div className="p-2.5 rounded-md glass-card" style={{ borderColor: `${cfg?.color || "#4d96ff"}25` }}>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-lg">{cfg?.icon || "📍"}</span>
          <div>
            <div className="text-xs font-medium" style={{ color: cfg?.color || "#4d96ff" }}>{name}</div>
            <div className="text-xs text-muted-foreground">{data.desc}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px] font-normal">
            {data.type}
          </Badge>
          <span className="text-xs text-muted-foreground">
            氛围: {data.vibe || "普通"}
          </span>
        </div>
      </div>

      {/* 在场 Bot */}
      {data.bots && data.bots.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1.5">在场人物 ({data.bots.length})</div>
          <div className="space-y-1">
            {data.bots.map(botId => {
              const bot = bots[botId];
              if (!bot) return null;
              const color = BOT_COLORS[botId] || "#4d96ff";
              return (
                <div
                  key={botId}
                  className="flex items-center gap-2 p-2 rounded-md glass-card cursor-pointer"
                  onClick={() => onBotClick(botId)}
                >
                  <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
                  <span className="text-xs" style={{ color }}>{bot.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {bot.current_activity?.slice(0, 20) || "..."}
                  </span>
                  {bot.is_sleeping && <span className="text-xs">💤</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* NPC */}
      {data.npcs && data.npcs.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1.5">NPC</div>
          <div className="flex flex-wrap gap-1">
            {data.npcs.map((npc, i) => (
              <Badge key={i} variant="outline" className="text-[10px] font-normal">
                {npc.name} · {npc.role}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* 公共记忆 */}
      {data.public_memory && data.public_memory.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1.5">地点记忆</div>
          <div className="space-y-1">
            {data.public_memory.slice(-3).map((mem, i) => (
              <div key={i} className="text-xs p-2 rounded-md glass-card text-foreground/55">
                {typeof mem === "string" ? mem : mem.event}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 工作岗位 */}
      {data.jobs && data.jobs.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-1.5">工作岗位</div>
          <div className="flex flex-wrap gap-1">
            {data.jobs.map((job, i) => (
              <Badge key={i} variant="outline" className="text-[10px] font-normal text-green-400 border-green-400/30">
                {job.title} ¥{job.pay}/轮
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center h-32">
      <span className="text-xs text-muted-foreground/40">{text}</span>
    </div>
  );
}
