# 前端性能优化方案 v2

## 已完成

- [x] 移除未使用 shadow map（ThreeScene.ts）— 节省 ~16MB VRAM
- [x] 建筑材质缓存池（Buildings3D.ts）— GPU batching
- [x] CharacterSprites3D 内存泄漏修复 — 释放克隆几何体/材质
- [x] TileGrid3D / Buildings3D 纹理释放
- [x] ThreeScene dispose 完整清理
- [x] A* 寻路节流 2 次/帧（PixelCityMap3D.tsx）
- [x] BotCard React.memo
- [x] CharacterSprites3D scale 缓存
- [x] Vite 代码分割（three / ui 独立 chunk）
- [x] 宝安城中村 / 南山科技园 程序化生成

---

## P0 — 高影响，实现简单 (ALL DONE)

### 1. A* 路径缓存

**文件**: `pathfinder.ts:63-139`

**问题**: 多个 Bot 前往同一地点时，A* 重复计算相同路径。10 个 Bot 去同一餐厅 = 10 次 A*。

**方案**:
```ts
const PATH_CACHE = new Map<string, { path: [number,number][], ts: number }>()
const CACHE_TTL = 5000

export function findPath(mesh, from, to) {
  const key = `${from[0]},${from[1]}-${to[0]},${to[1]}`
  const cached = PATH_CACHE.get(key)
  if (cached && Date.now() - cached.ts < CACHE_TTL) return [...cached.path]
  // ... existing A*
  PATH_CACHE.set(key, { path: result, ts: Date.now() })
  return result
}
```

**预估收益**: A* 调用减少 ~70%

---

### 2. A* 使用二叉堆替代线性扫描

**文件**: `pathfinder.ts:89-97`

**问题**: open 列表每次 pop 用线性扫描 O(n) 找最小 f 值。120x80 地图上路径搜索 open 列表可达数百节点。

**方案**: 用 MinHeap 替换数组，pop 从 O(n) 降为 O(log n)。

**预估收益**: 长距离路径搜索提速 3-5x

---

### 3. useWorldData 请求去重

**文件**: `hooks/useWorldData.ts:44-85`

**问题**: `fetchWorld()` 每次定时触发，不检查上一次请求是否完成。如果 fetch 耗时 2s、轮询间隔 3s，会出现并发请求。

**方案**:
```ts
const pendingRef = useRef(false)

const fetchWorld = useCallback(async () => {
  if (pendingRef.current) return
  pendingRef.current = true
  try { /* existing fetch */ }
  finally { pendingRef.current = false }
}, [])
```

---

### 4. RightPanel 计算结果 useMemo

**文件**: `RightPanel.tsx:54-78, 127, 200`

**问题**:
- EventsTab 每次渲染遍历所有 bots 构建 events 数组
- MomentsTab 每次 `[...moments].reverse().slice(0,20)` 创建新数组
- LocationTab 每次 `Object.keys(LOCATION_MAP_CONFIG)` 创建新数组

**方案**: 各处加 `useMemo`，依赖项为 `world` / `moments`。

---

### 5. Vehicles3D — 缓存 baseY 避免重复 Box3

**文件**: `Vehicles3D.ts:325-332`

**问题**: 每辆车 spawn 时从 clone 重新计算 Box3 取 baseY。120 辆车 = 120 次 Box3 遍历。

**方案**: 在 `loadGLB` 阶段计算 baseY 并存入 cache：
```ts
const glbCache = new Map<string, { model: THREE.Object3D, baseY: number }>()
```

---

## P1 — 高影响，需要较多改动 (DONE)

### 6. CharacterSprites3D 视锥剔除 [DONE]

**文件**: `CharacterSprites3D.ts:243-315`

**问题**: `sync()` 每帧遍历所有实体更新位置/动画。相机只看到 ~30% 的地图，但 100% 的实体都在计算。

**方案**:
```ts
const frustum = new THREE.Frustum()
const projScreenMatrix = new THREE.Matrix4()

function sync(...) {
  projScreenMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse)
  frustum.setFromProjectionMatrix(projScreenMatrix)

  for (const [botId, entity] of Object.entries(entities)) {
    const worldPos = new THREE.Vector3(worldX, 0, worldZ)
    if (!frustum.containsPoint(worldPos)) {
      entry.model?.visible = false
      continue
    }
    entry.model?.visible = true
    // ... existing sync logic
  }
}
```

**预估收益**: 60-70% 的实体跳过每帧更新

---

### 7. Sprite 材质池化 [SKIPPED — UV state is per-texture, sharing would conflict]

**文件**: `CharacterSprites3D.ts:197-210`

**问题**: 每个角色的 sprite 模式创建独立 `SpriteMaterial`。50 个 Bot = 50 个材质对象。

**方案**: 同 sheetKey 共享材质：
```ts
const spriteMaterialPool = new Map<string, THREE.SpriteMaterial>()
```

---

### 8. StreetFurniture3D — 合并 Box3 计算 [DONE]

**文件**: `StreetFurniture3D.ts:30-45`

**问题**: `normalizeModel()` 对 GLB 模型计算两次 Box3（scale + re-center），每次遍历整个几何体。

**方案**: 合并为一次 Box3：
```ts
function normalizeModel(model) {
  const box = new THREE.Box3().setFromObject(model)
  const size = new THREE.Vector3(); box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z)
  if (maxDim > 0) model.scale.multiplyScalar(1 / maxDim)
  // 直接用 scaled box 计算 center，不再重新调用 setFromObject
  const center = new THREE.Vector3(); box.getCenter(center)
  center.multiplyScalar(1 / maxDim)
  model.position.sub(center)
  model.position.y -= box.min.y / maxDim
}
```

---

### 9. randomWalkableTile 预计算候选列表 [DONE — included in P0 pathfinder rewrite]

**文件**: `pathfinder.ts:144-173`

**问题**: 每次调用遍历整个 rowRange 范围的所有格子建 candidates 数组。频繁调用（demo 实体每到达目的地就调用一次）。

**方案**: 场景加载时预计算每 N 行的可行走格子列表，存入索引：
```ts
const walkableIndex = new Map<number, [number,number][]>() // row -> walkable tiles
```

---

## P2 — 中等影响 (ALL DONE)

### 10. 建筑纹理 mipmap [DONE]

**文件**: `Buildings3D.ts:71-78`

**问题**: `loadTex()` 未生成 mipmap。远距离建筑立面纹理锯齿严重。

**方案**:
```ts
tex.generateMipmaps = true
tex.minFilter = THREE.LinearMipmapLinearFilter
```

---

### 11. 场景切换时清理全局缓存 [DONE]

**文件**: `Buildings3D.ts`, `Vehicles3D.ts`, `CharacterSprites3D.ts`

**问题**: `glbCache`、`texCache` 等全局 Map 跨场景累积。访问全部 7 个场景后，所有场景的纹理/模型留在内存。

**方案**: 添加 `clearGlobalCaches()` 函数，在 `PixelCityMap3D` 切换场景时调用，释放非当前场景的缓存。

---

### 12. RightPanel 列表虚拟化 [SKIPPED — lists already bounded: events by alive bots, moments sliced to 20]

**文件**: `RightPanel.tsx:100-114, 127-182`

**问题**: 事件流和朋友圈直接 `.map()` 渲染所有条目。100+ 条时 DOM 节点过多。

**方案**: 使用 `react-window` 或手动虚拟滚动，只渲染可视区域内的条目。

---

### 13. PixelCityMap3D — sceneConfig 引用稳定性 [SKIPPED — already stable refs from constant objects]

**文件**: `PixelCityMap3D.tsx:94-96`

**问题**: `meta` 和 `sceneConfig` 每次渲染可能产生新引用，触发下游 useEffect 重新执行。

**方案**: `useMemo(() => SCENE_META[activeLocation], [activeLocation])`

---

### 14. useWorldData — 首次连接后不再降级 Mock [DONE]

**文件**: `hooks/useWorldData.ts:73-84`

**问题**: 连接断开后降级到 MOCK_WORLD，用户误以为 Bot 仍在旧位置。

**方案**: 首次成功连接后设置 `hasConnected = true`，之后断连只显示错误状态，保留最后一次真实数据。

---

## P3 — 低影响 / 长期优化 (PARTIAL)

### 15. Web Worker 离线寻路 [SKIPPED — binary heap + cache + throttle already sufficient]

将 A* 搜索移入 Web Worker，主线程完全不阻塞。适合 Bot 数量 > 50 的场景。

### 16. 建筑 LOD [DONE]

远距离 landmark 自动切换为简化 Box 几何体。使用 `THREE.LOD`，阈值 60 单位。

### 17. 纹理压缩

将 PNG 纹理转为 KTX2 (Basis Universal) 格式，GPU 直接解码，减少 VRAM 占用 75%。需要 `KTX2Loader`。

### 18. 实体对象池 [DONE — activity candidate cache]

activityToDestTile 候选格子按关键词缓存，场景切换时自动失效。避免每次调用全量遍历 tilemap。

### 19. CSS containment [DONE]

对地图容器和右侧面板添加 `contain: content`，限制浏览器重排范围。

---

## 优先级总览

| 优先级 | 编号 | 优化项 | 预估工时 | 预估收益 |
|--------|------|--------|---------|---------|
| P0 | 1 | A* 路径缓存 | 30min | A* 调用 -70% |
| P0 | 2 | A* 二叉堆 | 1h | 长路径搜索 3-5x |
| P0 | 3 | useWorldData 请求去重 | 15min | 消除并发请求 |
| P0 | 4 | RightPanel useMemo | 20min | 减少数组分配 |
| P0 | 5 | Vehicles3D baseY 缓存 | 20min | 120 次 Box3 -> 0 |
| P1 | 6 | 角色视锥剔除 | 2h | 60-70% 实体跳过更新 |
| P1 | 7 | Sprite 材质池化 | 30min | 材质对象 50 -> 5 |
| P1 | 8 | StreetFurniture Box3 合并 | 20min | 遍历次数减半 |
| P1 | 9 | walkableTile 预计算 | 30min | 避免每次全量遍历 |
| P2 | 10 | 建筑纹理 mipmap | 10min | 远景抗锯齿 |
| P2 | 11 | 跨场景缓存清理 | 1h | 防止内存膨胀 |
| P2 | 12 | RightPanel 虚拟化 | 2h | DOM 节点大幅减少 |
| P2 | 13 | sceneConfig 引用稳定 | 10min | 避免无效 useEffect |
| P2 | 14 | useWorldData 连接状态 | 15min | UX 改善 |
| P3 | 15 | Web Worker 寻路 | 4h | 主线程零阻塞 |
| P3 | 16 | 建筑 LOD | 3h | 远景 draw call 减少 |
| P3 | 17 | 纹理压缩 KTX2 | 2h | VRAM -75% |
| P3 | 18 | 实体对象池 | 1h | GC 压力降低 |
| P3 | 19 | CSS containment | 10min | 减少重排范围 |
