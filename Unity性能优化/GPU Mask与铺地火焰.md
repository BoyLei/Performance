---
title: "GPU Mask与铺地火焰"
category: "专项"
tags: ["Unity", "Performance"]
discussion_status: "discussed"
learning_status: "pending"
priority: "P1"
created: "2026-11-26"
related: []
---

# GPU Mask与铺地火焰

历史问题包括多条路径区域合并、斜线网格边缘、大圆形场地映射，以及类似兰博大招且长度可调的火焰。来源：[[历史问题索引#讲解 Unity 内存原理]]。

## 区域表达与映射

将世界 XZ 范围映射到 UV：`uv = (worldXZ - minXZ) / worldSize`。圆形场地可放在方形纹理内，圆外区域屏蔽；是否拆 Chunk 取决于世界尺寸与所需精度。宽 1024m、纹理 2048 像素时每像素约 0.5m，边缘更精细就需要局部高分辨率或分块。

轨迹段可表示为线段的圆头带。令 A、B 为端点、P 为采样位置：

```text
t = saturate(dot(P-A, B-A) / max(dot(B-A, B-A), epsilon))
d = length(P - (A + t*(B-A)))
coverage = 1 - smoothstep(radius-softness, radius, d)
```

多段区域用最大覆盖值合并。若要每处独立持续时间，应保存过期时间或最后写入时间；只用 bool 或反复 max 并不能表达独立衰减。CPU 网格可服务伤害查询，GPU Mask 服务视觉；两者精度和刷新率可以不同。

## GPU 读写边界

采样旧 Mask 同时写同一张纹理可能产生反馈问题；可用 ping-pong 两张 RT。若使用混合方式直接画轨迹，需验证目标格式、混合操作和平台支持，不能默认任意 R8 都支持所需 Max Blend。避免每帧 CPU ReadPixels 回读整图。

## 火焰如何覆盖

Mask 只给出覆盖权重，不会自动生成粒子。地面 Mesh Shader 采样 Mask 显示灼烧；火焰主体可沿路径按距离 Emit 粒子、生成 Ribbon Mesh，或在兼容的 GPU 粒子系统里按 Mask 采样生成。长度变化应同步影响路径、区域、生命周期和伤害范围。

优先做 Mesh + Shader 的连续地面层，再用少量粒子补火舌。斜线边缘用覆盖率、足够采样精度和抗锯齿处理，而不是把碰到的整格全部涂满。

关联：[[01 GPU与渲染]]、[[09 角色动画与特效]]。

历史来源：[[历史问题索引#讲解 Unity 内存原理]]。
