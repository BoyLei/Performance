# Unity图集对比

会话 ID：`6aec554d-e2d0-83ee-ab93-d1bdcd05d976`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 93a5712b-8c4e-49be-bdf5-8ac4959b6dd4

### 用户

# Selected text:

## Selection 1
所以在 URP 中，MPB 并不一定比独立 Material 性能更好。

## My request:
为什么 mpb 会打断 srp batch？  直接使用 ma terial 不会打断嘛

### 助手

**直接使用独立 Material，通常不会打断 SRP Batcher；但使用 MaterialPropertyBlock（MPB），通常会让该 Renderer 失去 SRP Batcher 兼容性。**

这里有一个关键区别：

**SRP Batcher 不要求多个 Renderer 使用同一个 Material。它要求 Shader 满足特定的 Constant Buffer 布局规范，从而高效处理不同 Material 之间的切换。**

这是理解问题的核心。

## 一、先纠正一个常见误解

假设有三个角色：

```csharp
rendererA.material.color = Color.red;
rendererB.material.color = Color.blue;
rendererC.material.color = Color.green;
```

这三个 Renderer 可能分别使用：

```text
Renderer A → Material A → Red
Renderer B → Material B → Blue
Renderer C → Material C → Green
```

虽然 Material 不同，但只要它们使用兼容的 Shader Variant，并且满足 SRP Batcher 的其他要求，**依然可以走 SRP Batcher 路径**。

因为 SRP Batcher 优化的不是“所有物体共用一份材质”，而是 CPU 端准备、更新和绑定渲染状态的成本。

注意：这并不意味着三个 Renderer 会合并成一个 DrawCall。

## 二、SRP Batcher 为什么允许不同 Material？

先看 Shader 的两个关键 Constant Buffer：

```hlsl
CBUFFER_START(UnityPerMaterial)
    float4 _BaseColor;
    float _Metallic;
    float _Smoothness;
CBUFFER_END
```

```hlsl
CBUFFER_START(UnityPerDraw)
    // Unity 引擎管理的每对象数据
CBUFFER_END
```

这是简化示意，实际 `UnityPerDraw` 的内容由 Unity Shader 库和引擎约定。

SRP Batcher 的核心是把数据分为两类：

- `UnityPerMaterial`：每个 Material 的属性，尽可能持久保存在 GPU Constant Buffer 中。
- `UnityPerDraw`：每个 Renderer 的变换等引擎数据，通过专门的快速路径更新。

例如：

### SRP Batcher 的数据组织（示意）

**GPU：持久化 Material Constant Buffers**

Material A

各自的 CBUFFER

Material B

各自的 CBUFFER

Material C

各自的 CBUFFER

**SRP Batcher 快速渲染路径**

相同 Shader Variant，切换 Material 数据绑定并提交各个 Draw

GPU 绘制命令

Draw A → Draw B → Draw C

三个 Material 可以拥有不同的 `_BaseColor`。

只要数据布局符合规范，Unity 就可以复用快速路径，不必每个 DrawCall 都重新执行完整的材质属性收集与设置流程。

Unity 官方明确指出：SRP Batcher 允许多个不同 Material 使用相同 Shader，并强调减少 Shader Variant 切换。citeturn476734search0turn476734search2

## 三、那 MPB 为什么会破坏这个机制？

看两种代码：

**方案 A：独立 Material**

```csharp
Material mat = renderer.material;
mat.SetColor("_BaseColor", Color.red);
```

`_BaseColor` 属于 Material 自身的数据。

Unity 可以将它维护在该 Material 的 `UnityPerMaterial` Constant Buffer 中。材质发生修改时需要更新相关数据，但它仍然符合 SRP Batcher 的组织方式。

**方案 B：MPB**

```csharp
var block = new MaterialPropertyBlock();
block.SetColor("_BaseColor", Color.red);
renderer.SetPropertyBlock(block);
```

现在 `_BaseColor` 不再仅由 Material 决定，而是由具体 Renderer 的覆盖数据决定。

同一个 Material 可能出现：

```text
Material A
    _BaseColor = White

Renderer 1 + MPB → Red
Renderer 2 + MPB → Blue
Renderer 3 + MPB → Green
```

如果仍然直接绑定 Material A 的持久化 `UnityPerMaterial` 数据，三个 Renderer 都会得到 White，而不是各自的颜色。

渲染系统必须额外处理每个 Renderer 的覆盖值。

**这与 SRP Batcher 为 Material 预先组织、持久化属性数据的快速路径不匹配。**

这里要区分“技术上能否实现”和“Unity 当前是否支持”：

并不是 GPU 无法同时支持 MPB 和持久化 Constant Buffer，而是 Unity 的 SRP Batcher 实现明确规定，使用 MPB 的 Renderer 不走这条快速路径，转而使用普通 SRP 渲染路径。citeturn476734search1turn476734search8

## 四、独立 Material 就没有代价了吗？

当然不是。

假设 1000 个角色每个都有独立 Material。

| 指标 | 独立 Material | 共享 Material + MPB |
|--------|--------|--------|
| Material 实例数 | 1000 | 1 |
| 材质数据内存 | 较多 | 较少 |
| SRP Batcher | 通常兼容 | 不兼容 |
| 每 Renderer 的属性差异 | 支持 | 支持 |
| Material 生命周期管理 | 较复杂 | 较简单 |
| CPU 渲染成本 | 可能更低 | 可能更高 |

还有一个关键因素：**属性修改频率**。

如果你只在角色生成时执行一次：

```csharp
mat.color = Color.red;
```

随后一百帧都不修改，那么 Material 的属性数据可以长期复用。

但如果你每帧执行：

```csharp
mat.color = changingColor;
```

Unity 就需要持续更新对应 Material 的 GPU 数据。即使仍然兼容 SRP Batcher，也不能享受到材质数据长期不变的全部优势。

因此，不能简单认为“独立 Material 一定比 MPB 快”。

## 五、怎么验证？用 Frame Debugger

你可以在 URP 场景中放置三个 Cube，使用同一个 URP Lit Shader。

依次测试：

1. 三个 Cube 共享一个 Material。
2. 三个 Cube 分别使用不同 Material，但 Shader Variant 相同。
3. 三个 Cube 共享 Material，通过 MPB 设置不同颜色。

打开 `Window → Analysis → Frame Debugger`，观察 SRP Batch 以及 Draw 事件的相关信息。

预期结果：

| 测试 | SRP Batcher |
|--------|--------|
| 共享 Material | 兼容 |
| 三个独立 Material | 兼容（满足其他条件时） |
| 使用 MPB | 不兼容 |

需要注意 Shader Keyword、Pass、渲染队列等因素也会影响实际批次组织。不同 Material 兼容 SRP Batcher，不等于必然处于同一个 SRP Batch。

## 六、真正需要区分的是三种优化

| 技术 | 核心优化目标 |
|--------|--------|
| SRP Batcher | 减少 CPU 端 DrawCall 准备和状态设置开销 |
| GPU Instancing | 将多个实例合并到 Instanced Draw 中，减少提交次数 |
| MaterialPropertyBlock | 允许 Renderer 覆盖 Shader 属性，避免复制 Material |

**所以你的问题可以归结为一句话：**

`renderer.material` 虽然创建了独立 Material，但它仍然符合 SRP Batcher 的材质数据模型；MPB 则引入了 Renderer 级别的材质属性覆盖，而 Unity 当前的 SRP Batcher 快速路径不支持这种覆盖方式。

对于 URP 的大量角色渲染，下一层真正重要的问题是：**SRP Batcher 和 GPU Instancing 都在降低 CPU 渲染开销，但为什么 Unity 有时优先选择 SRP Batcher，导致明明启用了 GPU Instancing，Frame Debugger 中仍然看到大量独立 DrawCall？**

## 轮次 23d93d20-1bf4-4e58-9726-15dd0eb8b500

### 用户

可以

### 助手

接着讲 **SRP Batcher 和 GPU Instancing 的优先级问题**。

先给结论：

**在 Unity URP 中，如果一个 Renderer 同时满足 SRP Batcher 和传统 GPU Instancing 的条件，Unity 通常会优先使用 SRP Batcher。**

因此，你可能遇到：

- Shader 支持 GPU Instancing。
- Material 勾选了 `Enable GPU Instancing`。
- 场景里有 1000 个相同 Mesh 的对象。
- Frame Debugger 中仍然看到大量独立 Draw，而不是预期的 Instanced Draw。

这不一定是 GPU Instancing 失效，而可能是 Unity 选择了 SRP Batcher 路径。

## 一、它们到底优化了什么？

假设有 1000 个相同 Mesh 的角色。

### 传统绘制

```text
CPU
 ├─ 设置 Shader 状态
 ├─ 设置 Material 属性
 ├─ 设置 Renderer 数据
 └─ Draw 角色 1

 ├─ 设置 Shader 状态
 ├─ 设置 Material 属性
 ├─ 设置 Renderer 数据
 └─ Draw 角色 2

 ...重复 1000 次
```

### SRP Batcher

```text
CPU
 ├─ 使用兼容的 Shader Variant
 ├─ 高效切换 Material Constant Buffer
 ├─ 更新 Renderer 数据
 ├─ Draw 角色 1
 ├─ 更新 Renderer 数据
 ├─ Draw 角色 2
 └─ ...继续提交
```

它仍然可能产生 1000 次 Draw，但每次 Draw 的 CPU 准备成本降低了。

### GPU Instancing

```text
CPU
 ├─ 设置 Mesh
 ├─ 设置 Material
 ├─ 提交 1000 个实例的数据
 └─ Instanced Draw
           │
           ▼
GPU
 ├─ Instance 0
 ├─ Instance 1
 ├─ Instance 2
 └─ ...
```

它的目标是把多个对象合并到更少的 Draw 命令中。

所以两者优化的层次并不相同：

- SRP Batcher：让每次 Draw 更便宜。
- GPU Instancing：减少 Draw 的数量。

## 二、为什么 Unity 默认优先 SRP Batcher？

因为 SRP Batcher 的适用范围更广。

| 条件 | SRP Batcher | GPU Instancing |
|--------|--------|--------|
| Mesh 不同 | 可以 | 传统实例化不可以 |
| Material 不同 | 可以 | 通常要求相同 Material |
| Shader Variant 相同 | 重要条件 | 重要条件 |
| Renderer Transform 不同 | 可以 | 可以 |
| 减少实际 Draw 数量 | 通常不减少 | 可以显著减少 |
| 主要收益 | 降低每次绘制的 CPU 开销 | 降低绘制提交次数 |

例如，一个场景中有 1000 个物体，但分别使用 300 种 Mesh。

GPU Instancing 必须按相同 Mesh、Material 等条件分组。

SRP Batcher 则可以优化其中大量不同 Mesh 的绘制操作。

因此，Unity 将 SRP Batcher 设为传统 MeshRenderer 自动 GPU Instancing 之前的优先路径。这也是 Unity 2022 官方文档明确规定的行为。citeturn235005search3turn235005search0

## 三、如何让 Unity 真正使用 GPU Instancing？

有两条主要路线。

### 路线 A：让 Shader 不兼容 SRP Batcher

你可以针对专门用于大量重复 Mesh 的 Shader，调整其 Constant Buffer 布局，使它不符合 SRP Batcher 的兼容要求。

然后：

1. 确保 Shader 支持 GPU Instancing。
2. 勾选 Material 的 `Enable GPU Instancing`。
3. 所有对象使用相同 Mesh 和共享 Material。
4. 在 Frame Debugger 中确认出现 `Render Mesh (instanced)`。

不建议为了启用 Instancing 就直接关闭整个 URP 的 SRP Batcher，因为其他物体可能会因此增加 CPU 渲染成本。

### 路线 B：主动调用 Instancing 绘制 API

例如在 Unity 2022 中：

```csharp
using UnityEngine;

public class InstancingExample : MonoBehaviour
{
    public Mesh mesh;
    public Material material;

    private Matrix4x4[] matrices;

    void Start()
    {
        matrices = new Matrix4x4[500];

        for (int i = 0; i < matrices.Length; i++)
        {
            matrices[i] = Matrix4x4.TRS(
                new Vector3(i % 25, 0, i / 25),
                Quaternion.identity,
                Vector3.one
            );
        }
    }

    void Update()
    {
        Graphics.DrawMeshInstanced(
            mesh,
            0,
            material,
            matrices,
            matrices.Length
        );
    }
}
```

这会显式请求实例化绘制，不依赖普通 GameObject 的自动批处理选择。需要 Shader 和 Material 支持实例化。

注意，这段代码没有实现视锥剔除、LOD 和复杂的实例属性管理；它只是展示绘制路径。Unity 2022 也可以使用 `Graphics.RenderMeshInstanced`。

## 四、怎么判断哪种方式性能更好？

假设有 1000 个相同 Mesh 的物体。

示意：两种渲染路径的提交方式

**SRP Batcher**

# 1000

示意 Draw 数量

每次提交更轻量，但仍然有多个 Draw

**GPU Instancing**

# 1

理想情况下的 Instanced Draw

一次提交大量实例，但仍有实例数据准备成本

仅用于说明 Draw 数量差异，不代表真实耗时或 Unity 必然采用的批次大小。

虽然 Instancing 可能把 1000 次 Draw 减少到很少几次，但它还需要处理实例数据、剔除和其他渲染状态。

因此，性能比较不能只看 DrawCall 数量。

建议重点观察 Unity Profiler 的：

- `Render Thread` 耗时。
- `Main Thread` 中渲染准备的耗时。
- `Batches`、`SetPass Calls`。
- GPU Frame Time。
- Frame Debugger 中的具体绘制事件。

最好在实际 Android 和 iOS 设备上测试，而不是仅凭 Editor 数据决定。

## 五、针对大量角色和场景物体，应该怎么选？

| 场景 | 优先考虑 |
|--------|--------|
| 大量不同 Mesh、不同 Material 的场景物体 | SRP Batcher |
| 大量相同 Mesh、相同 Material 的树木、石头 | GPU Instancing |
| 大量不同动画的 SkinnedMeshRenderer | 传统 SRP Batcher 路径或自定义 GPU 动画方案 |
| 大量相同 Mesh、每实例不同颜色 | GPU Instancing + Instanced Properties |
| 少量物体需要不同颜色 | SRP Batcher 兼容的独立 Material 或按需使用 MPB |

最后还有一个很重要的版本区别：**以上优先级主要讨论 Unity 2022 中传统 GameObject/MeshRenderer 的自动实例化路径。** 新版本 Unity 的 GPU Resident Drawer、BatchRendererGroup 等系统，可以通过其他机制组织实例化绘制，不应该直接套用同样的优先级规则。

真正值得记住的是：**SRP Batcher 是降低 Draw 的 CPU 成本，GPU Instancing 是减少 Draw 的数量。Unity 默认选前者，不代表前者在所有场景下都更快。**

## 轮次 de92ee81-5e21-419c-a86d-79e2b342e1e4

### 用户

国内 团结引擎 有啥新的 渲染框架嘛？ 跟 unity6 和 unity7 对比有何差异

### 助手

团结引擎（Unity 中国的本土化引擎）与 Unity 6、Unity 7 的区别，需要分成两个层面来看：

1. **渲染管线架构**：有没有替代 URP/HDRP 的新框架？有没有新的 GPU Driven、Instancing、SRP Batcher 方案？
2. **引擎平台能力**：团结引擎针对国内平台做了哪些适配，与 Unity 官方版本的功能演进是否同步？

先明确一点：**团结引擎不是一套与 Unity 完全无关、从零开发的渲染引擎。** 它延续了 Unity 的技术体系，但具有独立的版本演进和本土化功能。

所以不能简单地用“团结引擎版本号更大或发布时间更新”来判断它的渲染架构是否比 Unity 6 更先进。

## 一、目前有哪些真正值得关注的新技术？

截至 2026 年 11 月，团结引擎公开展示的渲染技术中，最值得关注的是 **Virtual Geometry、Parallel Rendering、GPU Driven Pipeline 和 TuanjieGI**。

image_group{"query":["Tuanjie Engine Tower Valley virtual geometry 30 million vegetation rendering demo"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**1\. Virtual Geometry（虚拟几何体）**

思路接近 Unreal Engine Nanite：对高精度模型进行分块、层级组织和按需调度，减少传统人工制作大量 LOD 的负担。

团结引擎已将其用于《Tower Valley》技术演示。citeturn634938search3

---

image_group{"query":["Tuanjie Engine Tower Valley real time global illumination lighting demo"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**2\. TuanjieGI（实时动态全局光照）**

面向动态光照、间接光和大型场景，不必完全依赖预烘焙 Lightmap。

但实时 GI 的移动端成本、动态物体支持和画质限制，需要按具体版本验证。citeturn634938search4

---

image_group{"query":["Tuanjie Engine Tower Valley massive forest GPU driven rendering vegetation"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**3\. Parallel Rendering + GPU Driven**

Parallel Rendering 侧重 CPU 端渲染任务并行化；GPU Driven 则将更多实例管理、剔除和绘制数据生成工作转移到 GPU。

团结引擎 2025 年路线图提出三线程并行渲染架构和 2026 年全平台 GPU Driven Pipeline 目标，但路线图不能等同于所有功能已经正式交付。citeturn634938search4

还有两个值得关注的补充：

- **TJSR**：团结引擎的时域超分辨率技术，已扩展到 URP、HDRP。
- **Infinity Particle System**：新的粒子系统，包含面向批量渲染的数据组织、烘焙及共享配置能力。

这些功能在团结引擎 1.8.0 官方技术公告中都有说明。citeturn634938search3

## 二、团结引擎、Unity 6、Unity 7 对比

| 技术方向 | 团结引擎 | Unity 6 | Unity 7 |
|--------|--------|--------|--------|
| 核心渲染管线 | 延续 URP/HDRP，并独立扩展 | URP/HDRP | 延续并强化 URP |
| GPU Driven | 自研路线，部分能力已演示 | GPU Resident Drawer、BatchRendererGroup 等 | 继续演进，最终细节待发布 |
| 虚拟几何体 | Virtual Geometry 已公开演示 | 无完全对应的通用内置 Nanite 方案 | 尚待明确 |
| 实时 GI | TuanjieGI | HDRP 有成熟方案，URP 逐步增强 | 重点方向 |
| 超分辨率 | TJSR、DLSS 等 | FSR、DLSS 等，取决于管线及平台 | 官方提出神经超分辨率方向 |
| 并行渲染 | 自研 Parallel Rendering 路线 | Render Thread、Jobs、BatchRendererGroup 等 | 持续优化 |
| 国内小游戏、鸿蒙 | 重点支持方向 | 平台支持策略不同 | 尚需确认 |

这里尤其要注意 **Unity 7 还没有正式发布**。官方计划在 2027 年初推出，并强调它是 Unity 6 系列的延续，而不是完全推倒重来的渲染架构。citeturn634938search6

另外，Unity 官方 2026 年渲染战略已经明确：未来重点推进 URP，HDRP 侧重维护和稳定性，并从 Unity 6.5 开始逐步弃用 Built-in Render Pipeline。citeturn634938search5

## 三、团结引擎 2.0 是不是重写了一套渲染框架？

2026 年 7 月，团结引擎公布了 2.0 技术方向，提到对底层架构进行重构，升级虚拟几何体、实时 GI、阴影、动画、特效和并行计算能力。citeturn634938search2

但这里需要区分：

- **产品技术路线中的“2.0”**：代表下一阶段架构升级。
- **公开下载的编辑器版本**：官方发布页面列出的版本为 1.11.0（2026 年 10 月 26 日）。citeturn634938search1

因此，不能把 2.0 发布会上展示的全部能力都当作 1.11.0 中已经稳定可用的功能。

从现有公开资料看，我也没有找到足够依据，证明团结引擎已经用一套完全独立的新渲染管线替代了 URP/HDRP。

更准确的描述是：**在现有 SRP 技术体系上，团结引擎正在加入自研的几何调度、光照、并行渲染和 GPU Driven 能力。**

## 四、从渲染架构角度，哪一个更值得研究？

如果你关心的是大量角色、植被、建筑、GPU Instancing 和移动端性能，我会按技术问题来选：

image_group{"query":["Unity 6 GPU Resident Drawer render graph GPU instancing rendering technical demo"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**Unity 6：研究成熟的 GPU Resident Drawer 和 Render Graph**

重点看 GPU Resident Drawer 如何通过 BatchRendererGroup 等机制组织实例数据，以及 Render Graph 如何管理渲染资源和 Pass 依赖。

这两项都适合深入理解现代 Unity 渲染架构。

---

image_group{"query":["Tuanjie Tower Valley virtual geometry millions vegetation demonstration"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**团结引擎：重点研究 Virtual Geometry 和 Parallel Rendering**

尤其值得看《Tower Valley》开源 Demo，研究高密度植被、虚拟几何体、GPU 剔除和间接绘制如何组合。

官方提供的工程地址：urlTower Valley 开源项目https://cnb.cool/tuanjie/Tower_Valley/。

---

image_group{"query":["Unity 7 engine high end graphics neural upscaling official showcase"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**Unity 7：关注后续 URP 统一化与神经超分辨率**

目前更适合跟踪路线图，而不是据此直接制定生产项目迁移计划。

## 五、我认为最值得深挖的技术差异

如果只选一个方向，我建议比较：

**团结引擎 Virtual Geometry + GPU Driven 与 Unity 6 GPU Resident Drawer 的底层区别。**

因为它们看起来都在优化海量物体渲染，但其实并不完全是同一层面的技术：

| 技术 | 主要解决什么 |
|--------|--------|
| Virtual Geometry | 海量三角形的层级管理、LOD、几何数据调度 |
| GPU Driven | 将实例剔除、绘制列表生成等工作移到 GPU |
| GPU Resident Drawer | 让更多实例数据驻留 GPU，减少 CPU 绘制提交成本 |
| SRP Batcher | 优化 CPU 端每个 Draw 的状态准备成本 |

尤其需要研究一个问题：

**如果一个场景有 100 万棵树，传统 GPU Instancing、Unity 6 GPU Resident Drawer、团结引擎 Virtual Geometry 分别怎样处理剔除、LOD、DrawCall 和显存？**

这个问题能真正看出它们在架构上的差别，而不仅仅是功能列表上的区别。

## 轮次 fe666bee-15e4-470f-b552-0d62436e6c42

### 用户

继续

### 助手

我们继续深入比较：**假设一个开放世界场景里有 100 万棵树，传统 GPU Instancing、Unity 6 GPU Resident Drawer，以及团结引擎的 Virtual Geometry + GPU Driven，分别会如何处理？**

先明确一个重要区别：

**这三者不是同一层级的技术，也不完全互斥。**

- **GPU Instancing**：解决如何用更少的 DrawCall 绘制大量相同 Mesh。
- **GPU Resident Drawer（GRD）**：解决如何把大量 Renderer 的实例数据更高效地组织到 GPU 上，并自动执行实例化绘制。
- **Virtual Geometry（虚拟几何体）**：解决如何管理、选择和绘制海量几何细节，通常需要结合 GPU Driven 剔除和间接绘制。

我们从 CPU、GPU、显存和 LOD 四个角度拆解。

## 一、先假设一个实际场景
image_group{"query":["dense open world forest game environment millions of trees aerial view realtime rendering","large scale forest vegetation game engine rendering technical demo"],"aspect_ratio":"5:3","layout":"carousel"}

假设有以下数据：

| 指标 | 假设值 |
|--------|--------|
| 场景树木总数 | 100 万 |
| 树木种类 | 20 种 |
| 每棵树高模三角形数 | 20,000 |
| 相机可见树木 | 约 30,000 |
| 目标平台 | PC / 高端移动端 |
| 目标帧率 | 60 FPS |

如果所有树木都以最高精度绘制：

\[
1,000,000 \times 20,000 = 200亿
\]

即整个场景包含约 200 亿个树木三角形实例。

但这不代表 GPU 每帧必须绘制 200 亿个三角形。真正的目标是：

**在 CPU 不遍历过多对象的前提下，快速筛选出可见实例，并为每个实例选择合适的几何精度。**

## 二、传统 GPU Instancing：解决 DrawCall，但不自动解决百万对象管理

最简单的方案是使用 `Graphics.DrawMeshInstanced` 或 `Graphics.RenderMeshInstanced`。

例如 20 种树，每种树使用相同的 Mesh 和 Material。

**传统 Instancing 渲染流程**

CPU：管理树木实例与位置

CPU：视锥剔除、距离 LOD、实例分组

CPU：构建 Matrix 数组并提交 Instanced Draw

GPU：执行顶点和像素着色

假设可见 30,000 棵树，并且都属于一个 Mesh/Material 组合。

传统 `DrawMeshInstanced` 每次最多提交 1023 个实例，因此至少需要：

\[
\lceil 30000/1023\rceil=30
\]

次 Instanced Draw。

但这只是理想条件下的绘制命令数量，不包含不同 Mesh、LOD、材质、阴影 Pass 等造成的额外拆分。

真正的难点是：**CPU 如何高效地从 100 万棵树中找到需要绘制的 30,000 棵？**

如果每帧遍历全部实例、逐个计算距离、判断视锥、生成矩阵数组，CPU 仍然可能成为瓶颈。

当然，你可以通过空间分区、Job System、Burst、四叉树等方式优化，也可以自己编写 Compute Shader 实现 GPU 剔除。传统 Instancing API 本身并不强制所有剔除都在 CPU 上完成。

## 三、Unity 6 GPU Resident Drawer：优化 Renderer 数据管理和自动实例化

GPU Resident Drawer 最大的价值，是让开发者仍然可以使用普通 GameObject 和 MeshRenderer，而引擎在底层自动使用 `BatchRendererGroup` 组织实例化绘制。

**Unity 6 GPU Resident Drawer**

GameObject + MeshRenderer + LODGroup

Unity 自动组织兼容 Renderer 的实例数据

GPU Resident Data + BatchRendererGroup

GPU Instanced Draw

官方文档确认，GRD 使用 `BatchRendererGroup` 来减少 DrawCall 和 CPU 工作；它还能配合 GPU Occlusion Culling 排除被遮挡的对象。citeturn489477search3turn489477search0

但是要注意三个限制：

**第一，GRD 不是完整的 GPU 场景管理系统。**

它没有自动把所有 GameObject 的生命周期、业务逻辑和 Transform 更新全部搬到 GPU。100 万个 GameObject 本身仍可能造成很大的 CPU 和内存开销。

**第二，GRD 不等于 Virtual Geometry。**

它能高效绘制大量实例，但不会自动把一棵拥有 20,000 个三角形的树转化成可按几何 Cluster 选择细节的虚拟几何体。

**第三，它有兼容条件。**

例如 Unity 6 的 URP 实现要求支持 Compute Shader 的图形 API，以及特定渲染路径。使用 MPB 的 Renderer 也可能不符合 GRD 条件。citeturn489477search1

这也说明我们前面讨论的一个重要问题：**MPB 不仅可能影响 SRP Batcher，也可能影响 Unity 6 的 GPU Resident Drawer。**

## 四、团结引擎 Virtual Geometry：把优化深入到三角形层级

这才是架构上的主要差异。

传统 LOD 通常是：

```text
树木 Mesh
    ├── LOD0：20,000 triangles
    ├── LOD1：5,000 triangles
    ├── LOD2：500 triangles
    └── Billboard
```

每个实例选择一个 LOD Mesh。

Virtual Geometry 则把高精度几何体组织为多个 Cluster，并构建层级结构。

**Virtual Geometry 的概念结构**

原始高精度 Mesh

Cluster A

Cluster B

Cluster C

Cluster 层级与几何误差数据

GPU：按可见性、距离和屏幕误差选择 Cluster

绘制被选中的几何细节

这里的关键变化是：

传统 LOD 以**整个 Mesh** 为主要细节切换单位；Virtual Geometry 可以在更细的几何 Cluster 层级选择细节。

团结引擎官方将其描述为基于 GPU Driven Pipeline 和自适应 Cluster LOD 的方案，并宣称支持 URP、HDRP 以及 Android、iOS。citeturn489477search13

### 为什么它对复杂场景有优势？

假设一棵树靠近摄像机，但树冠只有一部分占据屏幕较大区域。

传统 Mesh LOD 可能需要选择整棵树的高精度模型。

Virtual Geometry 则可以根据 Cluster 层级及屏幕误差选择不同几何细节，从而更细粒度地控制几何复杂度。

不过，这不意味着 Virtual Geometry 对树木必然更快。

树叶通常涉及 Alpha Test、双面绘制、风动画和大量细碎几何。这些都可能让虚拟几何体的实现更复杂，且像素填充、Overdraw 和显存带宽依然可能成为瓶颈。

## 五、三种方案如何管理剔除、LOD 和显存？

| 对比维度 | 传统 GPU Instancing | Unity 6 GRD | 团结 Virtual Geometry + GPU Driven |
|--------|--------|--------|--------|
| 主要处理单位 | Mesh 实例 | Renderer / Mesh 实例 | 实例 + 几何 Cluster |
| 实例剔除 | 需自行组织或依赖其他系统 | 引擎自动管理，支持 GPU 遮挡剔除 | 依赖 GPU Driven 实现 |
| LOD | Mesh 级 LOD | 传统 Mesh LOD | Cluster 层级 LOD |
| Draw 提交 | 显式实例化 API | 自动 BRG Instancing | GPU Driven 绘制组织 |
| 几何数据 | 传统 Mesh | 传统 Mesh | 分块、层级几何数据 |
| 显存重点 | Mesh + 实例数据 | Mesh + GPU 常驻实例数据 | Cluster 数据、层级信息及缓存 |
| 接入复杂度 | 中等 | 相对较低 | 取决于资产转换和平台支持 |

这里要特别强调：团结引擎的具体 Cluster 调度、显存缓存、剔除算法和绘制命令生成方式，不能仅凭宣传资料认定与 Nanite 完全一致。上述是技术架构层面的比较，不代表已经验证其全部内部实现。

## 六、100 万棵树，真正的性能瓶颈可能在哪里？

假设经过剔除和 LOD 后，每帧剩下 30,000 棵可见树。

如果平均每棵树最终绘制 2,000 个三角形：

\[
30000 \times 2000 = 6000万
\]

每帧仍有 6000 万个三角形。

在 60 FPS 下：

\[
6000万 \times 60 = 36亿
\]

也就是每秒约 36 亿个三角形。

这还没有计算阴影 Pass、Overdraw、材质采样和后处理。

因此，对于移动端而言，单纯降低 DrawCall 不足以保证性能。

百万植被场景需要同时优化的四个层面

**CPU 提交**

Renderer 管理、剔除、Draw 命令准备

**几何处理**

三角形数量、顶点变换、LOD

**像素处理**

Alpha Test、Overdraw、阴影和光照

**内存带宽**

纹理采样、顶点读取、GPU Buffer 访问

## 七、团结引擎的实际成果有多大？

团结引擎在 2026 年 1 月公开了《Tower Valley》Demo。

官方披露的技术展示包括：

- 场景中超过 3000 万棵植被。
- 同屏处理三角形数量峰值超过 5 亿。
- 结合虚拟几何体、虚拟阴影贴图、实时 GI 和 DOTS。
- 推荐 Windows 平台使用 RTX 4070 或更高等级 GPU、至少 10GB 显存。citeturn489477search12

image_group{"query":["团结引擎 Tower Valley Demo 虚拟几何体 植被 2026","Tuanjie Engine Tower Valley rendering demo landscape"],"aspect_ratio":"5:3"}

这些数据说明它有值得研究的高复杂度场景演示，但**不能直接推导出同样的性能能在移动端复现**。需要知道实际分辨率、帧率、GPU、材质复杂度、阴影配置，以及统计的三角形是场景总量还是每帧实际处理量。

## 八、如果是移动端 MMO，我会怎样设计？

对于大量植被、建筑和场景装饰物，我会优先采用分层方案，而不是把所有物体统一交给一种渲染技术。

**世界数据层**

Chunk / 空间分区 / 实例数据 / 资源引用

**可见性与 LOD 层**

Chunk 剔除 → 实例剔除 → LOD 选择 → 可见列表

**普通几何**

树木、草、简单建筑

GPU Instancing / Indirect

**复杂几何**

高精度建筑、岩石

Virtual Geometry（设备允许时）

**渲染管线**

URP / HDRP → Render Graph → GPU

其中最关键的设计原则是：**场景数据不应该完全依赖 GameObject 层级来表示。**

100 万棵树不一定需要 100 万个 GameObject。可以将树木的位置、旋转、缩放、LOD 等信息存入结构化 Buffer，再由剔除和绘制系统使用。

这也解释了为什么 GPU Driven 不只是一个 Shader 技巧，而是涉及场景数据结构、资源调度、剔除系统和绘制提交的整体架构。

## 九、最终应该如何看待 Unity 6 与团结引擎？

Unity 6 的 GPU Resident Drawer，主要是在**保持现有 GameObject 工作流的前提下，提高实例绘制效率**。

团结引擎的 Virtual Geometry 则试图进一步解决**高复杂度几何体的表示、细节选择和绘制调度**。

二者解决的问题不同，实际项目中甚至可以组合类似的技术。

如果继续向底层研究，下一步最关键的是理解：

**GPU Driven 中，Compute Shader 如何完成 100 万个实例的视锥剔除、Hi-Z 遮挡剔除、LOD 选择，并生成 Indirect Draw 参数，让 CPU 不必逐个提交 Renderer？**

这才是从传统 Unity 渲染真正进入 GPU Driven 架构的分界点。

## 轮次 d6892f19-f4d9-4e04-83ae-8c169717b090

### 用户

继续

### 助手

这一步我们深入 **GPU Driven Rendering（GPU 驱动渲染）** 的核心实现。

重点回答一个问题：

**如果场景有 100 万棵树，如何让 GPU 自己完成视锥剔除、遮挡剔除、LOD 选择和绘制列表生成，而 CPU 不必逐个处理 Renderer？**

先明确：GPU Driven 并不是 GPU 完全取代 CPU。CPU 仍然负责发起 Compute Dispatch 和 Draw 命令，只是把大量逐实例计算工作转移给 GPU。

## 一、传统渲染和 GPU Driven 的本质区别

**传统 CPU Driven**

CPU

遍历场景对象

视锥剔除

LOD 选择

组织绘制命令

GPU

执行绘制

**GPU Driven**

CPU

更新相机数据

提交 Compute / Draw

GPU

实例剔除

LOD 选择

生成可见实例列表

间接绘制

对于 100 万个实例，CPU 不再需要每帧逐个计算可见性并上传所有可见矩阵，而是可以让实例数据长期保存在 GPU Buffer 中。

但 GPU Driven 的收益取决于数据更新频率、剔除效率、GPU 带宽以及目标平台。

## 二、GPU Driven 的完整渲染流水线

**GPU Instance Buffer**

100 万个实例的 Transform、Bounds、MeshID、LOD 信息

**Compute Shader：Frustum Culling**

视锥剔除

**Compute Shader：Hi-Z Occlusion Culling**

层级深度遮挡剔除

**Compute Shader：LOD Selection**

根据屏幕尺寸和误差选择几何精度

**Visible Instance Buffer**

只保留可见实例索引，按 Mesh / Material / LOD 分组

**Indirect Args Buffer**

GPU 写入实例数量等绘制参数

**DrawMeshInstancedIndirect / RenderMeshIndirect**

GPU 读取可见列表，绘制实例

这套流程的关键是：**GPU 生成的结果直接供 GPU 绘制使用，不需要把可见列表读回 CPU。**

接下来我们拆解每个阶段。

## 三、第一步：如何在 GPU 存储 100 万棵树？

首先，不要为每棵树创建一个 GameObject，而是使用 GPU Buffer 保存实例数据。

例如：

```hlsl
struct InstanceData
{
    float3 position;
    float scale;

    float4 rotation;

    float3 boundsExtents;
    uint meshId;
};

StructuredBuffer<InstanceData> _Instances;
```

每个实例占用：

\[
12+4+16+12+4=48\text{ Bytes}
\]

100 万个实例约占：

\[
1,000,000\times48=48\text{ MB}
\]

这还不包括 Mesh、纹理、可见列表和其他 GPU Buffer。

这里有一个优化点：如果树木是静态的，位置、旋转、缩放不需要每帧从 CPU 上传，可以初始化一次后长期驻留 GPU。

## 四、第二步：GPU 视锥剔除

视锥剔除的目的，是判断物体是否处于相机的可见范围。

二维示意：实际视锥是由六个平面构成的三维空间。

最常见的方法是使用包围球或 AABB 与视锥六个平面测试。

例如包围球：

\[
d=\operatorname{dot}(N,C)+D
\]

其中：

- \(N\)：平面法线。
- \(C\)：包围球中心。
- \(D\)：平面常数。
- \(r\)：包围球半径。

如果对任意一个视锥平面：

\[
d<-r
\]

就说明包围球完全位于该平面外侧，可以剔除。

Compute Shader 伪代码：

```hlsl
#pragma kernel FrustumCull

StructuredBuffer<InstanceData> _Instances;
AppendStructuredBuffer<uint> _VisibleIndices;

uint _InstanceCount;

[numthreads(256, 1, 1)]
void FrustumCull(uint3 id : SV_DispatchThreadID)
{
    uint index = id.x;

    if (index >= _InstanceCount)
        return;

    InstanceData instance = _Instances[index];

    if (!IsInsideFrustum(instance))
        return;

    _VisibleIndices.Append(index);
}
```

CPU 发起：

```csharp
int groups = Mathf.CeilToInt(instanceCount / 256.0f);

compute.Dispatch(kernel, groups, 1, 1);
```

100 万个实例约需要 3907 个线程组。

这不是说 GPU 只运行 3907 个线程，而是每组 256 个线程，合计覆盖约 100 万个实例。

## 五、第三步：Hi-Z 遮挡剔除

视锥剔除只能判断物体是否在摄像机范围内。

但它无法判断物体是否被山体、建筑等遮挡。

例如：

```svg
<svg viewBox="0 0 340 180" width="100%" xmlns="http://www.w3.org/2000/svg"><path d="M22 90 L316 24 L316 154 Z" fill="#64748b" fill-opacity=".07" stroke="#94a3b8" stroke-dasharray="4 4" /><path d="M92 132 L138 51 L187 132 Z" fill="#64748b" fill-opacity=".6" stroke="#64748b" /><path d="M143 132 L184 65 L225 132 Z" fill="#64748b" fill-opacity=".8" /><path d="M250 120 L250 72 M236 89 L250 62 L264 89 Z" stroke="#16a34a" stroke-width="2" fill="#16a34a" fill-opacity=".2" /><path d="M302 125 L302 79 M289 96 L302 70 L315 96 Z" stroke="#16a34a" stroke-width="2" fill="#16a34a" fill-opacity=".2" /><path d="M25 82 L41 90 L25 98 Z" fill="currentColor" /><path d="M40 90 L275 94" stroke="#ef4444" stroke-dasharray="5 4" stroke-width="1.5" /><text x="10" y="115" font-size="11" fill="currentColor">相机</text><text x="106" y="145" font-size="11" fill="currentColor">遮挡物</text><text x="240" y="145" font-size="11" fill="#16a34a">被遮挡实例</text></svg>
```

Hi-Z（Hierarchical Z）通常通过深度纹理的 Mipmap 层级进行保守遮挡测试。

基本步骤：

1. 先获得场景遮挡物的深度。
2. 构建深度金字塔（Hi-Z Pyramid）。
3. 将候选实例的包围体投影到屏幕空间。
4. 根据投影范围选择合适的 Mip Level。
5. 比较实例的保守最近深度与该区域的遮挡深度。
6. 确定完全被遮挡的实例后剔除。

**Hi-Z 深度金字塔**

Mip 0

Mip 1

Mip 2

高层 Mip 使用更少的深度样本，快速测试大范围遮挡。

这里有一个非常重要的技术细节：

**Hi-Z 不能简单地对深度做平均。**

对于普通 Z（深度越大表示越远），保守遮挡测试通常需要保存区域的最远深度，即 Max Depth。对于 Reversed-Z（深度越小表示越远），通常使用 Min Depth。

具体比较还必须保证深度空间一致，并正确处理包围体的最近深度，否则可能错误剔除可见物体。

另外，Hi-Z 数据来源有两种常见方案：

- **上一帧深度**：容易实现，但相机移动或遮挡关系变化时可能出现错误剔除，需要保守处理。
- **当前帧深度预处理**：先绘制主要遮挡物，再构建 Hi-Z，随后剔除其他物体，结果更及时但增加了 Pass 和同步成本。

所以 GPU 遮挡剔除并不是“加一个 Compute Shader 就完成了”。

## 六、第四步：GPU LOD 选择

经过剔除后，还需要选择合适的 LOD。

传统 CPU LOD 通常根据距离或屏幕占比决定。

GPU 上同样可以计算。

例如：

```hlsl
uint SelectLOD(float distance)
{
    if (distance < 30.0)
        return 0;

    if (distance < 80.0)
        return 1;

    return 2;
}
```

这是最简单的距离 LOD。

更合理的方案是基于屏幕投影大小或几何误差。

假设一个物体的包围球半径为 \(r\)，距离为 \(d\)，垂直视场角为 \(\theta\)，屏幕高度为 \(H\)。

在物体距离足够远时，其投影直径近似为：

\[
P \approx \frac{rH}{d\tan(\theta/2)}
\]

\(P\) 越小，说明物体在屏幕上占据的像素越少，可以选择更低的 LOD。

为了避免 LOD 频繁抖动，还需要设置迟滞阈值（Hysteresis）或交叉淡化。

## 七、第五步：如何生成 Indirect Draw 参数？

这一步是 GPU Driven 的关键。

传统绘制由 CPU 指定实例数量：

```csharp
Graphics.DrawMeshInstanced(
    mesh,
    0,
    material,
    matrices,
    count
);
```

而 Indirect Draw 的实例数量可以由 GPU 写入参数缓冲区。

传统索引间接绘制参数通常包括：

| 参数 | 含义 |
|--------|--------|
| Index Count Per Instance | 每个实例绘制多少索引 |
| Instance Count | 绘制多少个实例 |
| Start Index | 索引缓冲起点 |
| Base Vertex | 顶点偏移 |
| Start Instance | 起始实例编号 |

假设 GPU 剔除后剩下 25,000 棵树。

GPU 通过 Append Buffer 或计数器得到：

```text
VisibleCount = 25000
```

然后将该数量写入 Indirect Args Buffer。

CPU 不需要将这个数量读回托管内存。

在 Unity 2022 中，传统 API 可以使用：

```csharp
Graphics.DrawMeshInstancedIndirect(...)
```

新一些的渲染 API 则提供 `Graphics.RenderMeshIndirect` 等接口。

对于传统 `DrawMeshInstancedIndirect`，可以用 `ComputeBuffer.CopyCount` 将 Append Buffer 的计数器复制到参数缓冲区中对应的 `instanceCount` 字段。

但需要注意：**一个 Draw 通常仍然对应固定的 Mesh/SubMesh/Material 配置。**

如果 20 种树还有 3 个 LOD，就需要按不同绘制组合组织可见实例列表和参数。

一个常见的实现是：

```text
Compute Shader
    │
    ├── TreeType 0 / LOD 0 → Visible Buffer 0
    ├── TreeType 0 / LOD 1 → Visible Buffer 1
    ├── TreeType 0 / LOD 2 → Visible Buffer 2
    │
    ├── TreeType 1 / LOD 0 → Visible Buffer 3
    └── ...
```

这可以用多个 Append Buffer，也可以用计数、前缀和（Prefix Sum）和 Scatter 的方式，把实例整理到一个连续的大 Buffer 中。

后者通常更适合大规模 GPU Driven 系统。

## 八、最容易忽略的一点：Indirect Draw 怎么找到正确的实例？

假设剔除前：

```text
InstanceBuffer:
0  Tree A
1  Tree B
2  Tree C
3  Tree D
4  Tree E
```

剔除后：

```text
VisibleIndices:
0 → 1
1 → 3
2 → 4
```

现在 Indirect Draw 的 `instanceCount = 3`。

GPU 执行顶点 Shader 时，必须通过 `SV_InstanceID` 访问可见索引表，再找到原始实例数据。

概念性 HLSL：

```hlsl
StructuredBuffer<uint> _VisibleIndices;
StructuredBuffer<InstanceData> _Instances;

void LoadInstance(uint drawInstanceID)
{
    uint originalIndex =
        _VisibleIndices[drawInstanceID];

    InstanceData instance =
        _Instances[originalIndex];

    // 使用 instance 的 Transform
}
```

这里假设当前 Draw 的实例编号从 0 开始；实际还需要正确处理 API 的 Start Instance、Buffer 分组偏移和平台差异。

这才是 **GPU 剔除结果与最终绘制真正连接起来的地方**。

如果只生成了可见实例列表，但顶点 Shader 仍然使用原始连续 InstanceID，那么绘制的对象就会错乱。

## 九、完整方案的性能成本

GPU Driven 不是免费优化。

每帧可能新增的 GPU 工作

1. 读取实例 Bounds 和 Transform。
2. 执行视锥和遮挡剔除。
3. 计算 LOD、分组、计数和压缩可见列表。
4. 更新 Indirect Args Buffer。
5. 执行 Indirect Draw。

对于高端 PC，这种方案通常具有较大的优化空间。

但在移动端，尤其是 Tile-Based GPU 上，还要考虑：

- Compute Pass 与 Graphics Pass 之间的资源同步。
- 深度金字塔构建的额外带宽。
- GPU Buffer 随机访问。
- 原子计数器争用。
- GPU 是否原本已经受限于像素着色或内存带宽。

如果一个场景只有几百个简单物体，GPU Driven 可能反而更慢。

---

## 十、与 Unity 6 和团结引擎的关系

现在就可以更准确地理解这些技术：

| 技术 | 在上述流程中承担的角色 |
|--------|--------|
| Unity 6 GPU Resident Drawer | 自动管理兼容 Renderer 的 GPU 实例数据及实例化绘制 |
| BatchRendererGroup | 提供底层批量渲染组织接口 |
| GPU Driven Pipeline | 将剔除、LOD、绘制列表生成等更多工作放到 GPU |
| Virtual Geometry | 进一步将 LOD 和剔除深入到几何 Cluster 层级 |
| Indirect Draw | 让 GPU 生成的绘制参数直接驱动绘制 |

**最后的核心结论：**

GPU Driven 真正改变的不是某一个 DrawCall API，而是渲染数据的控制权。

传统 Unity 主要由 CPU 决定绘制什么，再告诉 GPU。

GPU Driven 则让 CPU 提供场景数据和任务，GPU 自己筛选可见对象、选择 LOD、组织实例数据，并执行间接绘制。

如果继续深入，最有技术价值的是研究 **GPU Driven 中的 Prefix Sum、Stream Compaction 和 Draw Command Generation**。它们决定了如何在 GPU 上高效地把 100 万个无序实例，整理成几十个能够直接执行的绘制批次。

