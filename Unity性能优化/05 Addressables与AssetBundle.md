---
title: "05 Addressables与AssetBundle"
category: "资源管理"
tags: ["Unity", "Performance"]
discussion_status: "mixed"
learning_status: "pending"
priority: "P0"
created: "2026-11-26"
unity_scope: "通用原理；示例以 Unity 2022.3 URP 为背景；实际版本待确认"
related: ["[[03 内存与GC]]", "[[06 异步与生命周期]]", "[[07 场景流式与地形]]"]
---

# 05 Addressables与AssetBundle

本模块为归纳后的原理与实践建议。历史原问集中在 [[历史问题索引]]；无原文支持的扩展不视为用户问过。

## 地址与依赖图

Addressables 将地址映射到资源位置，底层可能使用 AssetBundle。分组不自动等于最优打包；共享依赖若重复进入不同 Bundle 会扩大体积和驻留。

**验证与验收：** 查看 Build Layout，记录共享纹理、材质与 Shader 的实际归属。

## 引用计数与释放

每次加载获得的句柄需要明确所有者与释放路径。LoadAssetAsync 后自行 Instantiate 的对象不应误用 ReleaseInstance；InstantiateAsync 的实例使用匹配的 ReleaseInstance 方式。释放句柄不等于该帧立刻归还全部内存。

**验证与验收：** 建立加载、失败、取消、销毁四条路径的资源配对表。

## 循环引用与卸载

资源间循环依赖应分析最终 Bundle 图与持有关系，而不是认为 C# GC 可以回收 Bundle。运行时共享依赖被其他有效句柄持有时不能被提前释放。

**验证与验收：** 用构建报告查强连通依赖组，比较拆分前后加载峰值。

## Resources与启动

Resources 中的资源会进入相关构建数据，但不意味着进入游戏就全部实例化。启动耗时应区分索引初始化、实际加载、解压、反序列化和业务初始化。

**验证与验收：** 记录启动各阶段时间，移除无用资源后对比包体和启动采样。

## 粒度与抖动

Bundle 太大增加加载粒度与峰值；太小增加文件、元数据和请求成本。频繁卸载重载共享依赖会造成资源抖动。缓存与滞回应结合场景轨迹验证。

**验证与验收：** 沿同一路线往返，记录 Bundle 重载次数和峰值。

## 关联

- [[03 内存与GC]]
- [[06 异步与生命周期]]
- [[07 场景流式与地形]]

任务入口：[[学习任务脑图]]；参考依据：[[参考资料与版本边界]]。

历史来源：[[历史问题索引#处理AssetBundle循环引用]]。

历史来源：[[历史问题索引#Resources目录与启动时间]]。

历史来源：[[历史问题索引#Unity Addressables 架构]]。
