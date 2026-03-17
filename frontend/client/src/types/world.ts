// 深圳生存模拟 - 世界数据类型定义
// 对应 world_engine_v8.py 的 /world API 返回结构

export interface Emotions {
  happiness: number;
  sadness: number;
  anger: number;
  anxiety: number;
  loneliness: number;
}

export interface Skills {
  tech: number;
  social: number;
  creative: number;
  physical: number;
}

export interface Desires {
  lust: number;
  power: number;
  greed: number;
  vanity: number;
  security: number;
}

export interface Reputation {
  score: number;
  tags: string[];
  deeds: string[];
}

export interface KnownOpportunity {
  location: string;
  title: string;
  wage_estimate: number;
  skill: string;
  confidence: number;
  source: string;
}

export type LifeStance = 'active' | 'cautious' | 'low_motivation';

export function getLifeStance(riskTolerance: number, lowMotivationTicks: number): LifeStance {
  if (lowMotivationTicks > 5) return 'low_motivation';
  if (riskTolerance >= 0.6) return 'active';
  return 'cautious';
}

export function getLifeStanceLabel(stance: LifeStance): { label: string; emoji: string; color: string } {
  switch (stance) {
    case 'active':        return { label: '内卷', emoji: '💪', color: '#4d96ff' };
    case 'cautious':      return { label: '佛系', emoji: '🧘', color: '#ffd93d' };
    case 'low_motivation': return { label: '躺平', emoji: '😴', color: '#9b59b6' };
  }
}

export interface ActionLog {
  tick: number;
  time: string;
  plan: string;
  action?: { category?: string; type?: string; desc?: string };
  result?: { narrative?: string };
}

export interface BotState {
  id: string;
  name: string;
  age: number;
  gender: string;
  origin: string;
  edu: string;
  home: string;
  location: string;
  hp: number;
  money: number;
  energy: number;
  satiety: number;
  status: 'alive' | 'dead';
  job: string | null;
  skills: Skills;
  is_sleeping: boolean;
  current_task: string | null;
  emotions: Emotions;
  desires: Desires;
  phone_battery: number;
  aging_rate: number;
  current_activity: string;
  reputation: Reputation;
  long_term_goal: string | null;
  narrative_summary: string | null;
  action_log: ActionLog[];
  generation: number;
  inherited_from: string | null;
  occupation?: string;  // derived from job/role for sprite selection
  // v11: 劳动力市场
  aspiration_level?: number;
  risk_tolerance?: number;
  _low_motivation_ticks?: number;
  known_opportunities?: KnownOpportunity[];
}

export interface LocationNpc {
  name: string;
  role: string;
}

export interface LocationJob {
  title: string;
  pay: number;
}

export interface PublicMemory {
  event: string;
  actor: string;
  tick: number;
  impact: string;
}

export interface LocationState {
  desc: string;
  type: 'residential' | 'business' | 'commercial' | 'leisure';
  bots: string[];
  npcs: LocationNpc[];
  jobs: LocationJob[];
  public_memory: PublicMemory[];
  vibe: string;
  modification_count?: number;
}

export interface NewsItem {
  headline: string;
  source: string;
  tick: number;
  time: string;
}

export interface WorldTime {
  tick: number;
  virtual_hour: number;
  virtual_day: number;
  virtual_datetime: string;
}

export interface Weather {
  current: string;
  desc: string;
  changed_at_tick: number;
}

export interface WorldEvent {
  tick: number;
  time: string;
  event: string;
  desc: string;
}

export interface Moment {
  id: string;
  bot_id: string;
  bot_name: string;
  content: string;
  image_url?: string;
  tick: number;
  time: string;
  likes: string[];
  comments: { bot_id: string; bot_name: string; content: string; tick: number }[];
}

export interface WorldModification {
  name: string;
  description: string;
  type: string;
  creator: string;
  creator_name: string;
  location: string;
  tick: number;
  time: string;
}

export interface WorldState {
  time: WorldTime;
  weather: Weather;
  news_feed: NewsItem[];
  hot_topics: string[];
  bots: Record<string, BotState>;
  locations: Record<string, LocationState>;
  events: WorldEvent[];
  world_narrative: string;
  world_modifications: WorldModification[];
  generation_count: number;
  graveyard: BotState[];
  job_market?: Record<string, Record<string, { pressure: number; workers: string[] }>>;
}

// 地图配置：各地点的坐标（百分比）和图标
export const LOCATION_MAP_CONFIG: Record<string, {
  x: number; y: number; icon: string; color: string; label: string;
}> = {
  "宝安城中村":  { x: 15, y: 52, icon: "🏚️", color: "#ff9f43", label: "宝安城中村" },
  "南山科技园":  { x: 32, y: 28, icon: "🏢", color: "#4d96ff", label: "南山科技园" },
  "福田CBD":     { x: 62, y: 22, icon: "🏦", color: "#c77dff", label: "福田CBD" },
  "华强北":      { x: 52, y: 48, icon: "📱", color: "#00f5ff", label: "华强北" },
  "东门老街":    { x: 72, y: 58, icon: "🏮", color: "#ff6b6b", label: "东门老街" },
  "南山公寓":    { x: 22, y: 68, icon: "🏠", color: "#6bcb77", label: "南山公寓" },
  "深圳湾公园":  { x: 38, y: 82, icon: "🌊", color: "#00f5ff", label: "深圳湾公园" },
};

// Bot 颜色配置
export const BOT_COLORS: Record<string, string> = {
  "bot_1":  "#4d96ff",
  "bot_2":  "#ff6b9d",
  "bot_3":  "#ffd93d",
  "bot_4":  "#6bcb77",
  "bot_5":  "#9b59b6",
  "bot_6":  "#ff9ff3",
  "bot_7":  "#ff6348",
  "bot_8":  "#ffa502",
  "bot_9":  "#1abc9c",
  "bot_10": "#e040fb",
};

// Bot 角色标签
export const BOT_ROLES: Record<string, string> = {
  "bot_1":  "程序员",
  "bot_2":  "金融人",
  "bot_3":  "工人",
  "bot_4":  "设计师",
  "bot_5":  "富二代",
  "bot_6":  "创业者",
  "bot_7":  "商人",
  "bot_8":  "餐馆老板",
  "bot_9":  "音乐人",
  "bot_10": "网红",
};

// 情绪到颜色的映射
export function getEmotionColor(emotions: Emotions): string {
  if (!emotions) return "#4d96ff";
  const max = Math.max(
    emotions.happiness,
    emotions.sadness,
    emotions.anger,
    emotions.anxiety,
    emotions.loneliness
  );
  if (max === emotions.happiness && emotions.happiness > 40) return "#6bcb77";
  if (max === emotions.anger) return "#ff6b6b";
  if (max === emotions.anxiety) return "#ffd93d";
  if (max === emotions.sadness) return "#4d96ff";
  if (max === emotions.loneliness) return "#c77dff";
  return "#4d96ff";
}

// 情绪主情绪标签
export function getDominantEmotion(emotions: Emotions): { label: string; emoji: string } {
  if (!emotions) return { label: "平静", emoji: "😐" };
  const map = [
    { key: "happiness", label: "开心", emoji: "😊" },
    { key: "sadness",   label: "难过", emoji: "😢" },
    { key: "anger",     label: "愤怒", emoji: "😠" },
    { key: "anxiety",   label: "焦虑", emoji: "😰" },
    { key: "loneliness",label: "孤独", emoji: "😔" },
  ] as const;
  const dominant = map.reduce((a, b) =>
    (emotions[a.key] ?? 0) > (emotions[b.key] ?? 0) ? a : b
  );
  return { label: dominant.label, emoji: dominant.emoji };
}

// 天气图标
export const WEATHER_ICONS: Record<string, string> = {
  "晴天": "☀️", "多云": "⛅", "小雨": "🌧️",
  "暴雨": "⛈️", "台风": "🌀", "闷热": "🌡️", "凉爽": "🍃",
};
