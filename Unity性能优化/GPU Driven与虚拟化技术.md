---
title: "GPU Driven与虚拟化技术"
category: "专项"
tags: ["Unity", "Performance"]
discussion_status: "discussed"
learning_status: "pending"
priority: "P1"
created: "2026-11-26"
related: []
---

# GPU Driven与虚拟化技术

来源：[[历史问题索引#Unity图集对比]]、[[历史问题索引#解释ASTC压缩格式]]。这些主题在可取得的助手回答中已有解释，应标为已讨论；用户是否已经掌握另行验收。

## GPU Driven基础链

CPU 上传或维护实例数据 → GPU 视锥与可选 Hi-Z 剔除 → 选择 LOD → 写可见实例索引和间接绘制参数 → Indirect Draw。绘制阶段必须由可见列表正确映射回原实例，不能把压缩后的实例序号当原始 ID。还要考虑 Buffer 容量、溢出、同步、阴影视角和透明排序。

GPU Driven 减少 CPU 对象遍历与提交压力，但不自动解决大量像素、顶点、纹理驻留或复杂透明问题。GPU Resident Drawer、BatchRendererGroup 和自研 Indirect 是不同接入层，版本、后端与 Renderer 限制必须核对。

## LOD纠错

静态网格 LOD 切换不必然重新上传顶点或索引。已驻留资源可能只是更换绘制绑定。真正重传可能来自流送、动态修改或资源重建。共享 Buffer 与 offset 是某些底层方案的组织方式，不是所有 Unity LOD 的必需修复。

## 两种纹理流送

Mip Streaming 以资源的 mip 层级为主要控制粒度；Virtual Texturing 以虚拟页映射到物理缓存，细粒度访问需要页表、反馈和缺页管理。二者与 ASTC 压缩格式不是互斥方案。具体 Unity 管线的 VT 支持范围需要按版本确认。

## 引擎对比的边界

历史曾对团结引擎、Unity 6 与所谓 Unity 7 做技术比较。本库不将旧回答中的产品路线、发布日期或性能数字视为当前事实。评估需指定已发布版本、目标设备、管线、实际场景和授权条件；“百万棵树”只是压力场景，不能直接推断项目收益。

关联：[[01 GPU与渲染]]、[[04 纹理与资源]]、[[07 场景流式与地形]]。

历史来源：[[历史问题索引#Unity图集对比]]。

历史来源：[[历史问题索引#LOD切换优化方案]]。
