/**
 * Engine 模块组织说明
 *
 * navigation/  - A* 寻路 + 场景地图数据
 *   pathfinder.ts, sceneTiles.ts
 *
 * rendering/   - 2D Canvas 渲染 + 精灵 + Three.js 3D
 *   tileRenderer.ts, spriteSystem.ts, charSprites.ts,
 *   imageCache.ts, spritePngMap.ts, three/（6个文件）
 *
 * simulation/  - 实体移动 + 车辆 + 程序化城市
 *   gameEntity.ts, vehicleSystem.ts, proceduralCity.ts
 *
 * 共享配置（与 survival-sim 共用）:
 *   /shenzhen-shared/config/locations.json   - 7个地点
 *   /shenzhen-shared/config/activities.json  - 活动→地块映射
 *   /shenzhen-shared/config/emotions.json    - 5维情绪定义
 *   /shenzhen-shared/config/economy.json     - 经济参数
 *
 * 注意: 现有 @/engine/* import 路径不需要改动，原文件保持原位。
 * 子目录 index.ts 是模块边界文档，未来迁移时使用。
 */
export {}
