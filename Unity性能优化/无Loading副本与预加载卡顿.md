---
title: "无Loading副本与预加载卡顿"
category: "专项"
tags: ["Unity", "Performance"]
discussion_status: "discussed"
learning_status: "pending"
priority: "P1"
created: "2026-11-26"
related: []
---

# 无Loading副本与预加载卡顿

历史场景：主界面地图触发随机副本，只播放水波纹，怪物创建时明显卡顿。来源：[[历史问题索引#分支 · 讲解 Unity 内存原理]]。

## 分离四个阶段

资源到达、对象创建、逻辑初始化和显示启用是四个阶段。LoadAssetAsync 完成不代表 Instantiate、Awake、OnEnable、Shader 或上传成本已经消失。把 Prefab 预加载到内存只能解决其中一部分。

## 可落地方案

1. 按概率和成本预备少量可复用副本配置，限制常驻容量；不要在战斗高负载帧无限补池。
2. 资源加载限并发；对象分批创建。单次 Instantiate 本身无法被普通协程拆开，过大 Prefab 需要拆小或采用当前版本支持的实例化机制并实测。
3. 将昂贵初始化从 Awake/OnEnable 移到可显式调度的准备阶段；注意对象首次生命周期行为依赖激活状态和层级，不能认为 SetActive(false) 可以保证所有创建成本为零。
4. 状态采用 Preparing → Ready → Revealing → Active → Recycling；只在 Ready 后进入水波纹揭示。若资源未就绪，选择延迟触发或降级表现，不能承诺任意设备绝不掉帧。
5. 单独处理 Shader 与 GPU 首次使用，使用实际材质、Pass、关键字和目标后端验证。

## 对照实验

只做 LoadAsset、加载后实例化但不显示、最后启用显示，分别采样。检查依赖 Bundle 是否拖入过多纹理或 Shader。Application.backgroundLoadingPriority、asyncUploadTimeSlice 只应作为特定阶段的调节实验，不是所有卡顿的通用开关。

关联：[[06 异步与生命周期]]、[[03 内存与GC]]、[[09 角色动画与特效]]。

历史来源：[[历史问题索引#分支 · 讲解 Unity 内存原理]]。
