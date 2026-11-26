---
title: "01 GPU与渲染"
category: "GPU"
tags: ["Unity", "Performance"]
discussion_status: "mixed"
learning_status: "pending"
priority: "P0"
created: "2026-11-26"
unity_scope: "通用原理；示例以 Unity 2022.3 URP 为背景；实际版本待确认"
related: ["[[02 CPU与调度]]", "[[04 纹理与资源]]", "[[07 场景流式与地形]]"]
---

# 01 GPU与渲染

本模块为归纳后的原理与实践建议。历史原问集中在 [[历史问题索引]]；无原文支持的扩展不视为用户问过。

## 帧流水线与瓶颈

CPU 提交命令后 GPU 执行顶点处理、光栅化、片元着色与输出。CPU 和 GPU 可以重叠工作；稳定帧耗时通常受关键路径限制，不能直接把两个计时相加。Draw Call、三角形数和 FPS 都不能单独说明瓶颈。

**验证与验收：** 在真机同一镜头分别降低分辨率、阴影和物体数，记录 GPU 与 Render Thread 时间，判断填充、几何还是提交受限。

## SRP Batcher与GPU Instancing

SRP Batcher 减少 CPU 侧绘制准备和状态设置，不等于多个对象只剩一个 Draw Call。传统自动 GPU Instancing 适合同 Mesh、同材质并满足 Shader 条件的重复物体；实例化并不自动减少每个实例的顶点工作量。两者作用阶段不同，应比较实际路径与耗时。

**验证与验收：** 固定同一批石头，分别测普通提交、SRP Batcher、实例化；同时记录 CPU 提交、GPU、批次、顶点数。

## CBUFFER与MPB

常量缓冲区组织 Shader 参数。SRP Batcher 要求材质参数符合 UnityPerMaterial 等布局规则。Unity 2022.3 常规 Renderer 路径使用 MaterialPropertyBlock 会破坏 SRP Batcher 兼容性；实例化属性还必须正确声明。不要把这一结论无限外推到新版本和其他绘制 API。

**验证与验收：** 比较共享材质、独立材质与 MPB 的内存和提交时间，检查 Frame Debugger 原因。

## 可见性与LOD

视锥剔除决定是否提交，遮挡剔除避免绘制被遮住的对象，LOD 减少可见对象复杂度。合并 Mesh 会扩大 Bounds，可能降低剔除精度；合批和剔除存在权衡。LOD 淡入淡出也可能增加瞬时绘制。

**验证与验收：** 验证跨块大型建筑不会过早消失；对比网格合并前后的可见三角形与批次。

## 透明与带宽

透明粒子、UI 和植被容易产生重复片元处理。Alpha Clip、混合、深度写入和绘制排序影响 Early-Z 效果；不能认为启用某个设置就消除 Overdraw。纹理采样、RenderTarget 读写和分辨率共同消耗带宽。

**验证与验收：** 在同一画面降低透明覆盖面积与渲染比例，观察 GPU 时间变化。

## Shader Pass与Variant

Pass 决定一次材质可能参与哪些绘制阶段；关键字组合产生变体。变体过多增加构建、包体和加载成本；剔除过度会导致运行时效果缺失。预热必须覆盖实际运行组合，并验证后端与设备。

**验证与验收：** 建立实际材质和关键字清单，在构建日志核对保留与剔除数量。

## 关联

- [[02 CPU与调度]]
- [[04 纹理与资源]]
- [[07 场景流式与地形]]

任务入口：[[学习任务脑图]]；参考依据：[[参考资料与版本边界]]。

专项：[[场景UI分辨率与RT带宽]]。

专项：[[GPU Driven与虚拟化技术]]。

历史来源：[[历史问题索引#Unity Shader Variants]]。
