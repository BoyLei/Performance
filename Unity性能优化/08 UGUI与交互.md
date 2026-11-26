---
title: "08 UGUI与交互"
category: "UI"
tags: ["Unity", "Performance"]
discussion_status: "mixed"
learning_status: "pending"
priority: "P1"
created: "2026-11-26"
unity_scope: "通用原理；示例以 Unity 2022.3 URP 为背景；实际版本待确认"
related: ["[[04 纹理与资源]]", "[[03 内存与GC]]", "[[02 CPU与调度]]"]
---

# 08 UGUI与交互

本模块为归纳后的原理与实践建议。历史原问集中在 [[历史问题索引]]；无原文支持的扩展不视为用户问过。

## 重建链路

Graphic 或布局变化会标脏，并在 Canvas 更新阶段触发布局、顶点或材质更新。频繁修改文本、RectTransform、LayoutGroup 和 ContentSizeFitter 可能放大重建。

**验证与验收：** 对同一 UI 分别修改颜色、文本与尺寸，观察 Canvas 和布局采样。

## Canvas拆分

把高频动态区域与静态区域分开可隔离部分重建，但增加 Canvas 也可能增加批次与管理开销。按变化频率和生命周期拆分，不能给每个控件都建 Canvas。

**验证与验收：** 比较整页重建与动态区域独立 Canvas 的 CPU 和 Draw Call。

## 点击与射线

EventSystem 与输入模块处理输入，GraphicRaycaster 找 UI 命中，再经层级分发接口事件。IPointerClickHandler 不是每个组件自行轮询鼠标。无交互装饰应评估关闭 Raycast Target。

**验证与验收：** 验证遮挡、父级处理、拖拽后点击以及多 Canvas 排序。

## CanvasGroup与隐藏

alpha、interactable、blocksRaycasts 分别影响可见度和交互；alpha=0 不等价于完整停止更新与释放资源。隐藏方式要结合生命周期、重建成本和恢复耗时选择。

**验证与验收：** 比较 SetActive、Canvas.enabled 与 CanvasGroup 的隐藏恢复成本。

## 架构与列表

MVC、MVP 和属性通知用于组织状态与表现；性能来自减少无效刷新和控制生命周期。大型滚动列表优先虚拟化、复用单元并解绑旧事件。

**验证与验收：** 对比 1000 行全创建与可见行复用的分配、重建和内存。

## 关联

- [[04 纹理与资源]]
- [[03 内存与GC]]
- [[02 CPU与调度]]

任务入口：[[学习任务脑图]]；参考依据：[[参考资料与版本边界]]。

专项：[[UGUI架构与事件顺序]]。

历史来源：[[历史问题索引#分支 · Unity UGUI 架构图]]。

历史来源：[[历史问题索引#Unity UGUI 架构图]]。

历史来源：[[历史问题索引#UGUI 架构图解析]]。

历史来源：[[历史问题索引#UGUI 概述解析]]。

历史来源：[[历史问题索引#UGUI架构图解析]]。

历史来源：[[历史问题索引#uGUI 网格重建过程]]。

历史来源：[[历史问题索引#Unity IPointerClickHandler 点击原理]]。

历史来源：[[历史问题索引#CanvasGroup in Unity]]。

## 移动、尺寸与 UI 技术选型纠错（Q054–Q067）

纯位置变化不必调用每个 Graphic 的 OnPopulateMesh；尺寸变化、Image 切片/填充、文字变化等才可能触发本地几何重建。Transform 变化仍可能引发 Canvas 原生重新合批，不代表零成本。不要把 Layout Rebuild、Graphic Rebuild、Canvas.BuildBatch 混成“整个 Canvas 所有 Mesh 重建”。

uGUI 同样保留对象树；UI Toolkit 的保留式 Visual Tree 也最终生成几何并提交 GPU。“GPU 不认识坐标”“UI Toolkit 必然整树重排”“UMG 不需要网格”“Overlay 总是最快”都不是可采信的选型结论。按实际版本、世界空间 UI、输入、样式、动画、绑定和 Profiler 对比；不要从架构标签推导必然快慢。

RectTransform 宽度可写为 `parentWidth*(anchorMax.x-anchorMin.x)+sizeDelta.x`。水平拉伸且左右边距分别 100 时，1920 宽父节点中的宽度为 1720；Pivot 影响参考点，CanvasScaler 不代替 Anchor 与安全区适配。

CanvasGroup.interactable 主要影响遵守组状态的 Selectable，不等同阻止所有自定义 IPointerClickHandler；blocksRaycasts 参与 UI 射线过滤，不是禁用 Physics.Raycast 的开关。alpha=0 也不会自动让射线穿透。

完整模块和源码定位见 [[UGUI架构与事件顺序]]，面试原问作为练习入口保留，不能将助手题库里每个反问当作用户已问或已掌握。
