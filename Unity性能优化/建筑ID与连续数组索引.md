---
title: "建筑ID与连续数组索引"
category: "专项"
tags: ["Unity", "Performance"]
discussion_status: "discussed"
learning_status: "pending"
priority: "P1"
created: "2026-11-26"
related: ["[[07 场景流式与地形]]"]
---

# 建筑ID与连续数组索引

对应历史：[[历史问题索引#场景的流式加载]]。建筑跨 Chunk 时，索引应记录多对多关系，而不是复制建筑实例。

## 三张表

- Prefab 表：PrefabId → 资源地址；不同实例可以复用一个原型。
- Building 表：BuildingId → PrefabId、Transform、Bounds 和允许的实例参数。
- Chunk 表：ChunkId → Start、Count；它们指向扁平的“建筑 ID 引用数组”，不直接表示 BuildingId 的连续区间。

```text
Chunk A 的建筑: [2, 8, 15]
Chunk B 的建筑: [8, 21]
FlatBuildingIds = [2, 8, 15, 8, 21]
A: Start=0, Count=3
B: Start=3, Count=2
```

建筑 8 在两块中有引用，运行时只有一个实例。查询 A 与 B 后做并集，得到 2、8、15、21。时间主要与候选块的引用数量有关；不能声称与世界建筑总量完全无关，因为还要考虑空间查询与大物体覆盖。

```csharp
// 演示索引含义，省略边界检查与资源生命周期。
for (int i = chunk.Start; i < chunk.Start + chunk.Count; i++)
{
    int buildingId = flatBuildingIds[i];
    neededIds.Add(buildingId); // 复用 HashSet，避免每次分配
}
```

## 空间与加载意图

离线以 Renderer Bounds 或约定的包围盒求重叠 Chunk。Renderer.bounds 是世界 AABB，Shader 位移、风动、SkinnedMesh 的包围体可能需要保守扩张；自定义 world bounds 不随 Transform 自动更新，也不会自动序列化到 Scene/Prefab。碰撞盒与视觉范围可能不同，选择哪一个要明确。大建筑可单独进大物体索引，避免覆盖过多块。

60° 朝向扇区适合提高前方请求优先级，不应成为唯一保留条件。相机快速转向、倒退和网络校正时，周边保留圈与卸载滞回能避免突然缺物体。若用点积，60° 总夹角对应半角 30°；还要计入建筑 Bounds。

静态导出 ID 需要版本与稳定性规则，不要把运行时 GetInstanceID 当跨构建稳定 ID。服务器逻辑 ID 与表现 ID 也应显式映射。

关联：[[07 场景流式与地形]]、[[05 Addressables与AssetBundle]]。

本轮复核结论见 [[知识点逐项核验]]；文档/源码版本依据见 [[技术核验来源]]。
