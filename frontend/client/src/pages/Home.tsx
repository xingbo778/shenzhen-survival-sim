/**
 * Home - 深圳像素城市主页面
 * 布局：顶部 Header + 左侧地图(60%) + 右侧面板(40%)
 *       右侧面板：上半 Bot 卡片网格 + 下半 标签页信息面板
 *       点击 Bot 卡片时右侧切换为 Bot 详情
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useWorldData, sendMessage, setEngineUrl } from "@/hooks/useWorldData";
import { OVERVIEW_TO_SCENE_KEY } from "@/config/scenes";
import PixelCityMap3D from "@/components/PixelCityMap3D";
import CityOverviewMap from "@/components/CityOverviewMap";
import BotCard from "@/components/BotCard";
import BotDetailPanel from "@/components/BotDetailPanel";
import RightPanel from "@/components/RightPanel";
import TopHeader from "@/components/TopHeader";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import { AlertTriangle, ArrowLeft } from "lucide-react";

export default function Home() {
  const [engineUrl, setEngineUrlState] = useState(
    (import.meta.env.VITE_ENGINE_URL as string) || "http://localhost:8000"
  );
  const { world, moments, isConnected, isLoading, lastUpdated, error } = useWorldData(3000, engineUrl);

  const handleEngineUrlChange = useCallback((url: string) => {
    setEngineUrlState(url);
    setEngineUrl(url);
  }, []);
  const [selectedBotId, setSelectedBotId] = useState<string | null>(null);
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [currentMapLocation, setCurrentMapLocation] = useState<string>('宝安城中村');
  const [showBotDetail, setShowBotDetail] = useState(false);
  const [mapLayer, setMapLayer] = useState<'overview' | 'scene'>('overview');
  const [zoomAnimating, setZoomAnimating] = useState(false);

  const handleBotClick = useCallback((botId: string) => {
    setSelectedBotId(botId);
    setShowBotDetail(true);
  }, []);

  const handleLocationClick = useCallback((location: string) => {
    setSelectedLocation(location);
    setCurrentMapLocation(location);
    setShowBotDetail(false);
  }, []);

  const handleOverviewLocationSelect = useCallback((locationKey: string) => {
    const sceneName = OVERVIEW_TO_SCENE_KEY[locationKey] || '宝安城中村';
    setZoomAnimating(true);
    setTimeout(() => {
      setCurrentMapLocation(sceneName);
      setSelectedLocation(sceneName);
      setMapLayer('scene');
      setZoomAnimating(false);
    }, 350);
  }, []);

  const handleSendMessage = useCallback(async (botId: string, msg: string) => {
    const ok = await sendMessage(botId, msg);
    if (ok) {
      toast.success(`消息已发送给 ${world?.bots[botId]?.name || botId}`);
    } else {
      toast.error("发送失败，请检查 world_engine 是否运行");
    }
  }, [world]);

  const aliveBots = useMemo(() =>
    world
      ? Object.entries(world.bots).filter(([, b]) => b.status === "alive")
      : [],
    [world]
  );

  const selectedBot = selectedBotId && world ? world.bots[selectedBotId] : null;

  // Lazy-load Bot cards
  const [visibleBotIds, setVisibleBotIds] = useState<Set<string>>(new Set());
  const botCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        setVisibleBotIds(prev => {
          const next = new Set(prev);
          entries.forEach(e => {
            const id = (e.target as HTMLElement).dataset.botid;
            if (id) { if (e.isIntersecting) next.add(id); }
          });
          return next;
        });
      },
      { threshold: 0.01 }
    );
    Object.entries(botCardRefs.current).forEach(([, el]) => { if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, [aliveBots]);

  return (
    <div className="h-screen bg-background overflow-hidden flex flex-col">
      {/* 顶部 Header */}
      <TopHeader
        world={world}
        isConnected={isConnected}
        lastUpdated={lastUpdated}
        engineUrl={engineUrl}
        onEngineUrlChange={handleEngineUrlChange}
      />

      {/* 主体区域 */}
      <div className="flex flex-1 overflow-hidden">

        {/* 左侧：像素城市地图 */}
        <div className="relative w-[60%] border-r border-white/[0.06] overflow-hidden">
          {/* 地图标题 */}
          <div className="absolute top-2 left-3 z-10 pointer-events-none">
            <span className="text-xs text-muted-foreground">
              {mapLayer === 'overview' ? 'PIXEL MAP · SHENZHEN' : `SCENE · ${currentMapLocation.toUpperCase()}`}
            </span>
          </div>

          {/* 返回全景按钮 */}
          {mapLayer === 'scene' && (
            <Button
              onClick={() => setMapLayer('overview')}
              variant="outline"
              size="sm"
              className="absolute top-2 right-3 z-20 h-7 text-xs backdrop-blur-sm"
            >
              <ArrowLeft className="size-3.5" />
              全城视图
            </Button>
          )}

          {/* 全景提示 */}
          {mapLayer === 'overview' && (
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 text-xs text-muted-foreground pointer-events-none">
              点击地点进入场景
            </div>
          )}

          {/* 缩放动画遮罩 */}
          {zoomAnimating && (
            <div className="absolute inset-0 z-30 flex items-center justify-center bg-background/85 backdrop-blur-sm">
              <div className="text-sm text-primary">
                进入 {currentMapLocation}...
              </div>
            </div>
          )}

          {/* 加载状态 */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center z-20 bg-background/70 backdrop-blur-sm">
              <div className="text-center">
                <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent mx-auto mb-2 animate-spin" />
                <div className="text-xs text-primary">
                  连接 world_engine...
                </div>
              </div>
            </div>
          )}

          {/* 错误提示 */}
          {!isConnected && !isLoading && (
            <Alert variant="destructive" className="absolute bottom-8 left-3 right-3 z-10">
              <AlertTriangle className="size-4" />
              <AlertDescription className="text-xs">
                无法连接到 world_engine ({engineUrl})。请确保 world_engine_v8.py 正在运行，或修改上方地址。
              </AlertDescription>
            </Alert>
          )}

          {/* 全景层 */}
          {mapLayer === 'overview' && (
            <div className="absolute inset-0">
              <CityOverviewMap
                world={world}
                onLocationSelect={handleOverviewLocationSelect}
              />
            </div>
          )}

          {/* 场景层 */}
          {mapLayer === 'scene' && (
            <div className="absolute inset-0">
              <PixelCityMap3D
                world={world}
                selectedBotId={selectedBotId}
                onBotClick={handleBotClick}
                onLocationClick={handleLocationClick}
                currentLocation={currentMapLocation}
              />
            </div>
          )}
        </div>

        {/* 右侧面板 */}
        <div className="flex flex-col w-[40%] overflow-hidden">

          {/* Bot 状态网格（上半部分） */}
          <div
            className="shrink-0 overflow-y-auto border-b border-white/[0.06] transition-[height] duration-300"
            style={{ height: showBotDetail ? "0" : "45%" }}
          >
            <div className="px-2 pt-2 pb-1 flex items-center justify-between sticky top-0 z-10 glass-panel-solid border-0 border-b border-white/[0.06]">
              <span className="text-xs text-muted-foreground">
                BOT STATUS · {aliveBots.length} ACTIVE
              </span>
              {selectedBotId && (
                <button
                  onClick={() => { setSelectedBotId(null); setShowBotDetail(false); }}
                  className="text-[10px] text-muted-foreground/40 hover:text-muted-foreground transition-colors"
                >
                  清除选择
                </button>
              )}
            </div>
            <div className="p-2 grid grid-cols-2 gap-1.5">
              {aliveBots.map(([botId, bot]) => (
                <div
                  key={botId}
                  data-botid={botId}
                  ref={el => { botCardRefs.current[botId] = el; }}
                  style={{ minHeight: 80 }}
                >
                  {(visibleBotIds.has(botId) || selectedBotId === botId) ? (
                    <BotCard
                      botId={botId}
                      bot={bot}
                      isSelected={selectedBotId === botId}
                      onClick={() => handleBotClick(botId)}
                    />
                  ) : (
                    <div className="w-full h-full rounded-md bg-white/[0.02]" style={{ minHeight: 80 }} />
                  )}
                </div>
              ))}
              {aliveBots.length === 0 && (
                <div className="col-span-2 flex items-center justify-center h-20 text-xs text-muted-foreground/40">
                  {isLoading ? "加载中..." : "暂无存活 Bot"}
                </div>
              )}
            </div>
          </div>

          {/* Bot 详情面板 */}
          {showBotDetail && selectedBot && (
            <div
              className="shrink-0 overflow-hidden border-b border-white/[0.06]"
              style={{ height: "45%" }}
            >
              <BotDetailPanel
                botId={selectedBotId}
                bot={selectedBot}
                onClose={() => setShowBotDetail(false)}
                onSendMessage={handleSendMessage}
              />
            </div>
          )}

          {/* 下半部分：标签页信息面板 */}
          <div className="flex-1 overflow-hidden">
            <RightPanel
              world={world}
              moments={moments}
              selectedLocation={selectedLocation}
              onBotClick={handleBotClick}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
