# Unity Camera Setup

会话 ID：`6a337174-8c00-83ea-a932-7411e6d7a42d`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 8290dc6c-1bcd-4390-bf7f-c26b8005cde1

### 用户

什么是

### 助手

**RenderGraph** 可以理解成 **"现代渲染管线的任务调度器 + 资源管理器"**。

它不是一种渲染算法，而是一种**组织 Render Pass 的框架**。它的目标是：

> **告诉系统"我要做哪些渲染步骤"，而不是"我要如何管理每一张 RenderTexture"。**

---

## 为什么需要 RenderGraph？

先看没有 RenderGraph 的情况。

假设你要实现下面的渲染流程：

```text
Scene

↓

Depth

↓

SSAO

↓

Bloom

↓

ToneMapping

↓

Screen
```

传统写法大概是：

```csharp
// 创建 RT
RenderTexture depthRT = GetTemporaryRT();
RenderTexture ssaoRT = GetTemporaryRT();
RenderTexture bloomRT = GetTemporaryRT();

// Pass1
RenderDepth(depthRT);

// Pass2
RenderSSAO(depthRT, ssaoRT);

// Pass3
RenderBloom(ssaoRT, bloomRT);

// Pass4
ToneMapping(bloomRT);

// 释放 RT
ReleaseTemporary(depthRT);
ReleaseTemporary(ssaoRT);
ReleaseTemporary(bloomRT);
```

开发者需要自己管理：

- 什么时候申请 RenderTexture
- 什么时候释放
- 哪些 RT 可以复用
- 哪些 Pass 有依赖关系

项目越大，越容易出问题。

---

## RenderGraph 的思想

RenderGraph 改变了思路。

你只需要描述：

> **我有哪些 Pass，每个 Pass 读什么资源、写什么资源。**

例如：

```text
Depth Pass

写入

↓

DepthTexture
```

↓

```text
SSAO Pass

读取 DepthTexture

写入 SSAOTexture
```

↓

```text
Bloom Pass

读取 SSAOTexture

写入 BloomTexture
```

↓

```text
Final Pass

读取 BloomTexture
```

这样就形成了一张"图"（Graph）。

```
Depth
   │
   ▼
SSAO
   │
   ▼
Bloom
   │
   ▼
Final
```

这就是 **Render Graph** 名字的来源。

---

# RenderGraph 会自动做什么？

假设：

```text
Depth RT

↓

SSAO 用

↓

后面没人用了
```

传统：

```text
你自己 Release()
```

RenderGraph：

自动知道：

```
Depth RT 生命周期结束
```

立即：

```
回收
```

开发者不用管。

---

## RenderGraph 可以复用显存

例如：

```
Pass1

↓

RT_A
```

Pass2：

```
RT_A

↓

RT_B
```

Pass3：

已经不用 RT_A 了。

那么：

```
RT_A 的显存

↓

直接给 RT_C
```

即：

```
RT_A

×

释放

×

重新申请
```

而是：

```
RT_A

↓

Reuse

↓

RT_C
```

这样：

GPU 显存几乎没有额外开销。

---

## RenderGraph 可以优化执行顺序

例如：

你写了：

```
PassA

↓

PassB

↓

PassC
```

但实际上：

```
PassC

根本不用

PassB
```

RenderGraph 会分析依赖：

```
PassA

↓

PassB

PassC
```

甚至可以：

```
PassB

↓

PassC

并行
```

（如果 GPU 支持 Async Compute。）

---

## RenderGraph 可以删除无用 Pass

例如：

你写了：

```
Depth

↓

MotionVector

↓

Bloom

↓

Final
```

结果：

```
MotionVector

没人读取
```

RenderGraph：

直接：

```
删掉整个 MotionVector Pass
```

这叫：

**Pass Culling**

也是它名字中的 Culling。

---

# RenderGraph 的底层原理

实际上，它会把每个 Pass 看成一个节点（Node）。

例如：

```
Depth Pass

输入：

无

输出：

DepthTexture
```

↓

```
Bloom Pass

输入：

DepthTexture

输出：

BloomTexture
```

RenderGraph 内部大概维护这样的数据结构：

```text
PassNode
{
    Read[]

    Write[]

    Execute()
}
```

所有 Pass 连起来就是一张 **有向无环图（DAG，Directed Acyclic Graph）**：

```
A

↓

B

↘

C

↓

D
```

然后：

```
拓扑排序

↓

资源分析

↓

生命周期分析

↓

执行
```

---

# RenderGraph 与 CommandBuffer 的关系

很多人容易混淆。

实际上：

```
RenderGraph
```

负责：

> **决定什么时候执行哪个 Pass。**

而：

```
CommandBuffer
```

负责：

> **真正向 GPU 提交命令。**

例如：

```
RenderGraph

↓

Bloom Pass

↓

Execute()

↓

CommandBuffer.Draw()

↓

GPU
```

所以：

```
RenderGraph
```

是：

**调度器**

而：

```
CommandBuffer
```

是：

**命令记录器**

---

# Unity 中 RenderGraph 的位置

在 URP/HDRP 中，一帧的流程可以简化为：

```
Camera

↓

RenderPipeline

↓

RenderGraph

↓

RenderPass

↓

CommandBuffer

↓

GPU Driver

↓

GPU
```

因此：

- **Camera**：描述"从哪里看"。
- **Render Pipeline**：组织整个渲染流程。
- **RenderGraph**：分析 Pass 依赖、管理资源生命周期、优化执行顺序。
- **RenderPass**：完成一个具体渲染任务（如阴影、Bloom、SSAO）。
- **CommandBuffer**：记录实际的 GPU 绘制命令。

---

## 一个形象的比喻

可以把 RenderGraph 想象成一个**工厂生产线调度系统**。

假设要生产一辆汽车：

```
钢板

↓

冲压

↓

焊接

↓

喷漆

↓

装配
```

传统方式就像：

> 工人自己安排每道工序、搬运材料、管理仓库。

而 RenderGraph 就像：

> 一个智能调度系统，你只需要告诉它有哪些工序以及工序之间的依赖关系，它会自动安排顺序、分配设备、回收资源，并避免不必要的中间步骤。

---

## 为什么 Unity 在新版本全面推广 RenderGraph？

主要原因有三个：

1. **减少显存占用**：自动复用临时 RenderTexture。
2. **提高性能**：自动裁剪无用 Pass、优化资源屏障和执行顺序。
3. **降低开发复杂度**：开发者关注"渲染逻辑"，而不是资源管理。

对于 **Unity 6** 来说，RenderGraph 已经成为 URP 和 HDRP 的重要基础设施，也是未来 SRP 持续发展的方向。

## 轮次 5c95641a-2d72-4a50-89ed-160a8ad69ab1

### 用户

是什么

### 助手

你问的是 **RenderTexture（渲染纹理）是什么**。

一句话概括：

> **RenderTexture 就是一块 GPU 显存中的"画布"，Camera 或 Shader 可以把渲染结果画到这块画布上，而不是直接画到屏幕。**

---

## 先理解普通渲染

正常情况下：

```text
Camera

↓

GPU

↓

FrameBuffer（屏幕）

↓

显示器
```

Camera 最终把画面直接画到屏幕。

例如：

```text
Main Camera

↓

画游戏场景

↓

玩家看到
```

---

## 有了 RenderTexture

如果 Camera 的 **Target Texture** 设置为一个 RenderTexture：

```text
Main Camera

↓

RenderTexture

↓

（没有直接显示）
```

此时，Camera 不再画到屏幕，而是画到一张"纹理"里。

之后你可以：

```text
RenderTexture

↓

RawImage

↓

UI 显示
```

或者：

```text
RenderTexture

↓

Shader

↓

继续处理
```

所以它本质上也是一种 **Texture（纹理）**，只是它的内容是 GPU 实时渲染出来的，而不是从 PNG、JPG 等图片文件加载的。

---

## RenderTexture 在内存中的位置

普通 Texture：

```text
PNG

↓

读取磁盘

↓

GPU Texture
```

RenderTexture：

```text
GPU

↓

实时渲染

↓

GPU Texture
```

两者最终都在 GPU 显存中。

---

## RenderTexture 的典型用途

### 1. 小地图（最常见）

```text
Top Camera

↓

RenderTexture

↓

UI RawImage
```

游戏里的小地图基本都是这样实现的。

---

### 2. 后处理（Bloom、HDR、景深）

现代渲染一般不会直接画到屏幕，而是：

```text
Scene

↓

RenderTexture A

↓

Bloom

↓

RenderTexture B

↓

ToneMapping

↓

Screen
```

每一步都以 RenderTexture 作为输入和输出。

---

### 3. 镜子

镜子前放一个 Camera：

```text
Mirror Camera

↓

RenderTexture

↓

镜子材质
```

于是镜子就能实时反射场景。

---

### 4. 安防监控、电视屏幕

```text
Camera A

↓

RenderTexture

↓

电视模型材质
```

游戏里常见的监控画面就是这么实现的。

---

### 5. 截图

```text
Camera

↓

RenderTexture

↓

Texture2D

↓

PNG
```

很多游戏的拍照功能就是利用 RenderTexture。

---

## RenderTexture 的数据结构

它和普通 Texture 类似，只不过可以写入：

```text
RenderTexture

宽度：1920

高度：1080

格式：RGBA8

深度缓冲：24bit

MSAA：4x
```

GPU 在绘制时，会把：

```text
颜色(Color)

深度(Depth)

模板(Stencil)
```

写入这块显存。

---

## 为什么 RenderTexture 很重要？

现代 GPU 渲染很少一步完成。

例如 Bloom：

```text
Scene

↓

RT1

↓

高亮提取

↓

RT2

↓

模糊

↓

RT3

↓

合成

↓

屏幕
```

如果没有 RenderTexture，就无法把每一步的结果保存下来供下一步继续处理。

---

## 和 Texture2D 的区别

| RenderTexture | Texture2D |
|--------------|-----------|
| GPU 可以直接写入 | GPU 通常只读取 |
| 内容实时生成 | 内容来自图片文件或 CPU |
| 用于渲染流程 | 用于贴图、图片资源 |
| 通常驻留在 GPU | CPU 和 GPU 都可能持有数据 |

简单理解：

- **Texture2D**：一张"静态照片"。
- **RenderTexture**：一块可以反复擦写的"电子白板"，GPU 可以不断在上面作画。

---

### 一个最经典的例子

假设你要实现一个游戏内的小地图：

```text
          Top Camera
               │
               ▼
        RenderTexture
               │
               ▼
        UI RawImage
               │
               ▼
          玩家看到小地图
```

这里的 **RenderTexture** 就充当了"中间画布"：顶部摄像机把场景画到它上面，而 UI 再把这张实时更新的纹理显示出来。

这也是理解 RenderTexture 最直观的例子。

## 轮次 4cc89b18-fcb4-47fd-b878-32910d2f57ff

### 用户

如果没有释放，是每帧都绘制吗

### 助手

是的，但需要区分**"没有释放（Release）"**和**"每帧都会渲染"**，这是两个不同的概念。

---

## 情况一：Camera 持续绑定 RenderTexture（最常见）

例如：

```text
Main Camera
    ↓
TargetTexture = RT
```

只要这个 Camera 是启用状态（`enabled = true`），**每一帧都会把新的画面渲染到这个 RenderTexture**。

流程就是：

```text
第1帧
Camera → RT

第2帧
Camera → RT（覆盖上一帧内容）

第3帧
Camera → RT（再次覆盖）
```

这里的 RT 不需要每帧重新创建，它只是被反复写入。

---

## 情况二：RenderTexture 没有释放，但 Camera 不再渲染

例如：

```csharp
camera.targetTexture = rt;
camera.Render();     // 手动渲染一次
camera.targetTexture = null;
```

之后：

- RT 没有 `Release()`
- Camera 也没有继续往里面画

那么：

**RenderTexture 会一直占用 GPU 显存，但内容保持最后一次渲染的结果，不会自动更新。**

也就是说：

```text
RenderTexture

↓

一直保存最后一帧画面
```

不会每帧变化。

---

## 情况三：每帧都创建 RenderTexture（错误做法）

例如：

```csharp
void Update()
{
    var rt = new RenderTexture(1920, 1080, 24);
    camera.targetTexture = rt;
}
```

这样就变成：

```text
Frame1
创建 RT1

Frame2
创建 RT2

Frame3
创建 RT3
```

如果没有释放：

```csharp
rt.Release();
Destroy(rt);
```

GPU 显存会越来越高，最终可能导致：

- 显存泄漏
- 性能下降
- 甚至崩溃（Out of Memory）

---

## Release() 到底是干什么？

很多人误以为：

> Release() = 停止渲染

其实不是。

`Release()` 的作用是：

> **释放 RenderTexture 内部申请的 GPU 显存资源。**

例如：

```csharp
RenderTexture rt = new RenderTexture(1024, 1024, 24);
rt.Create();   // 分配 GPU 显存

...

rt.Release();  // 释放 GPU 显存
```

如果 Camera 还绑定着这个已经 `Release()` 的 RT，下次渲染时可能会重新创建底层资源（具体行为取决于使用方式和 Unity 内部实现），或者导致渲染异常，因此通常不会在仍需使用时调用 `Release()`。

---

## RenderTexture 会一直占用显存吗？

会。

例如：

```text
RenderTexture

2048 × 2048

RGBA32
```

大约占用：

```text
2048 × 2048 × 4 ≈ 16 MB
```

如果还有：

- Depth Buffer
- MSAA（例如 4×）

实际占用可能达到几十 MB。

只要没有释放或销毁，它就会一直占着这些 GPU 资源。

---

## 项目中的正确做法

### 长期使用（推荐）

例如：

- 小地图
- 镜子
- 监控画面

```csharp
Start()
{
    rt = new RenderTexture(...);
    camera.targetTexture = rt;
}

OnDestroy()
{
    camera.targetTexture = null;
    rt.Release();
    Destroy(rt);
}
```

创建一次，重复使用，最后统一释放。

---

### 临时使用

例如：

- 截图
- 一次性的离屏渲染

```text
创建 RT
    ↓
渲染
    ↓
读取结果
    ↓
Release
    ↓
Destroy
```

---

## RenderGraph 为什么能优化这个问题？

以前需要开发者自己管理：

```text
Create RT

↓

Render

↓

Release RT
```

很容易忘记释放。

RenderGraph 会自动分析：

```text
这个 RT 已经没有任何 Pass 使用了
```

于是自动回收或复用它的显存，开发者无需手动管理临时 RenderTexture 的生命周期。

---

**一句话总结：**

- **RenderTexture 不释放** → 会一直占用 GPU 显存。
- **是否每帧都绘制** → 取决于是否还有 Camera（或其他渲染命令）持续向它写入，而不是取决于它有没有 `Release()`。

## 轮次 7d24c606-b0fa-4c0e-9cc8-7e0eaadcc0e8

### 用户

我们是Srp mmo项目，需要实现 场景和 UI的渲染分离，从而达到不同机型 场景按不同分辨率渲染，同时UI保持设计分辨率不变

### 助手

这是目前很多 **MMO、开放世界、二游** 都采用的方案，本质上就是：

> **3D 场景动态分辨率（Dynamic Resolution）+ UI 固定分辨率。**

你的需求可以总结成：

```text
屏幕：2560×1440

↓

Scene
    ↓
    可以渲染成
    2560×1440
    1920×1080
    1280×720

↓

UI
    始终按
    2560×1440
    绘制

↓

最终合成
```

这样低端机 GPU 压力大幅下降，而 UI 始终清晰。

---

# 为什么不能直接改 Screen.SetResolution？

如果：

```csharp
Screen.SetResolution(1280,720,false);
```

那么：

```text
Scene
↓

720P
```

同时

```text
UI
↓

720P
```

UI 会变糊。

所以不能这么做。

---

# SRP 的标准做法

实际上就是：

```text
Scene Camera

↓

RenderTexture(720P)
```

↓

```text
Final Blit

↓

BackBuffer(1440P)
```

↓

```text
UICamera

↓

直接画UI
```

即：

```text
┌──────────────┐
│ Scene Camera │
└──────┬───────┘
       │
       ▼
720P RenderTexture
       │
       ▼
Upscale
       │
       ▼
BackBuffer(1440P)
       │
       ▼
UICamera Overlay
       │
       ▼
屏幕
```

---

# 为什么 UI 不会糊？

因为：

UI 根本没有经过：

```text
720P RT
```

UI：

直接：

```text
BackBuffer
```

例如：

BackBuffer：

```text
2560×1440
```

Canvas：

```text
Scale With Screen Size
```

设计分辨率：

```text
1920×1080
```

所以：

UI：

一直：

```text
1440P
```

---

# Camera 如何配置？

通常：

```text
Scene Camera
```

负责：

```text
Default

Terrain

Player

Monster
```

UICamera：

```text
UI
```

Layer。

Scene Camera：

```text
TargetTexture

↓

SceneRT
```

UICamera：

```text
TargetTexture

↓

None
```

直接画：

```text
BackBuffer
```

---

# Render Pipeline

Pipeline：

实际上：

```text
Scene Camera

↓

SceneRT
```

↓

```text
Blit(SceneRT)

↓

Screen
```

↓

```text
UICamera

↓

Screen
```

UI：

没有：

```text
Blit
```

所以：

不会缩放。

---

# 动态分辨率

例如：

高端：

```text
1.0x

↓

2560×1440
```

中端：

```text
0.8

↓

2048×1152
```

低端：

```text
0.6

↓

1536×864
```

甚至：

```text
0.5

↓

1280×720
```

UI：

一直：

```text
2560×1440
```

不变。

---

# Unity 官方 Dynamic Resolution

URP：

其实支持：

```text
Dynamic Resolution
```

但是：

Unity 官方：

主要：

针对：

```text
RenderTexture
```

缩放。

很多 MMO：

不会直接用官方。

原因：

需要：

更加灵活。

例如：

```text
Scene

0.65x
```

UI：

```text
1.0x
```

Video：

```text
0.8x
```

Map：

```text
0.5x
```

官方：

做不到这么细。

---

# MMO 常见架构

很多项目：

实际上：

```text
Scene Camera

↓

SceneRT
```

↓

```text
PostProcess
```

↓

```text
FSR
```

↓

```text
BackBuffer
```

↓

```text
UICamera
```

↓

```text
Present
```

例如：

```text
Scene

↓

70%

↓

AMD FSR

↓

100%

↓

UI

↓

Screen
```

玩家：

几乎：

感觉不到。

---

# 如果是 URP

推荐：

```text
Base Camera

↓

TargetTexture
```

↓

```text
RendererFeature

↓

Blit
```

↓

```text
Overlay Camera(UI)
```

而不是：

自己：

```text
Graphics.Blit()
```

因为：

RendererFeature：

可以：

插入：

```text
Before Rendering

After Opaque

After PostProcess
```

性能更好。

---

# RenderGraph 中怎么做？

Unity6：

就是：

```text
ScenePass

↓

SceneRT
```

↓

```text
UpscalePass

↓

BackBuffer
```

↓

```text
UIPass

↓

BackBuffer
```

RenderGraph：

自动：

管理：

```text
SceneRT
```

生命周期。

---

# 大厂通常还会加入 Upscaler

例如：

```text
Scene

↓

70%
```

↓

```text
FSR2
```

↓

```text
DLSS
```

↓

```text
XeSS
```

↓

```text
100%
```

↓

UI

↓

Screen
```

这样：

GPU：

压力下降：

30~60%。

UI：

仍然：

100% 清晰。

---

## 从你的描述来看，我更推荐的架构

既然你们是 **SRP MMO**，而且需要兼顾不同机型，我建议采用下面这种结构（也是很多商业项目的做法）：

```text
Scene Camera（Base）
    ↓
Scene RenderTexture（可动态调整分辨率）
    ↓
PostProcess（Bloom、ToneMapping 等）
    ↓
Upscale（FSR/双线性/双三次等）
    ↓
BackBuffer（屏幕原生分辨率）
    ↓
UI Camera（Overlay）
    ↓
UGUI（固定设计分辨率）
    ↓
Present
```

这种设计有几个优点：

- **场景分辨率可以动态调整**，根据 GPU 性能实时切换。
- **UI 始终保持原生分辨率**，文字和图标不会因为场景降分辨率而变糊。
- **后处理只作用于场景**，不会影响 UI 的清晰度。
- 后续如果接入 **FSR、DLSS、XeSS** 等超分技术，也几乎不需要改 UI 渲染流程。

如果你们已经在使用 **Unity 6 + RenderGraph URP**，我还可以结合 RenderGraph 详细讲解这一整套流程，包括 **RendererFeature、RenderPass、RenderGraph Pass 的实现细节**，以及如何在 SRP 中实现这种**场景与 UI 完全分离渲染**的商业级方案。

## 轮次 961f5351-a0cf-4d34-b530-b0270a736348

### 用户

Blit是什么

### 助手

**Blit（Bit Block Transfer）** 可以理解成：

> **把一张纹理（Texture）画到另一张纹理（RenderTarget）上，同时可以选择经过一个 Shader 处理。**

它是图形渲染中最常见的操作之一，几乎所有后处理（Bloom、HDR、FXAA、Color Grading）都会用到。

---

# 最简单理解

假设有一张图片：

```text
SceneRT
```

现在要显示到屏幕：

```text
SceneRT

↓

Screen
```

这个"复制到屏幕"的过程，就是一次 **Blit**。

---

## 它不是 CPU memcpy

很多程序员第一次看到 Blit，以为就是：

```cpp
memcpy(A,B)
```

其实不是。

Blit 是：

```text
GPU

↓

画一个全屏 Quad（三角形）

↓

Shader 采样 Source Texture

↓

输出到 Destination
```

也就是说：

GPU 又进行了一次绘制（Draw Call）。

---

# Blit 的内部流程

例如：

```text
Source RT

↓

Blit

↓

Destination RT
```

GPU 实际做的是：

```text
绑定 Destination RT

↓

绑定 Source Texture

↓

画一个覆盖整个屏幕的矩形

↓

Fragment Shader

↓

output
```

整个屏幕每个像素都会执行一次 Fragment Shader。

---

# 为什么需要 Blit？

因为 GPU **不能直接修改一张纹理自身的内容**。

例如：

错误：

```text
SceneRT

↓

修改自己
```

GPU 不允许：

```text
Read

↓

Write

↓

同一张 RT
```

因此必须：

```text
SceneRT

↓

Blit

↓

TempRT
```

然后：

```text
TempRT

↓

Blit

↓

SceneRT
```

所以：

后处理通常都有很多：

```text
RT1

↓

RT2

↓

RT3

↓

RT4
```

---

# 举个 Bloom 的例子

Bloom：

第一步：

提取高亮：

```text
SceneRT

↓

Blit

↓

BrightRT
```

Shader：

```hlsl
if(color > threshold)

output=color;
```

---

第二步：

模糊：

```text
BrightRT

↓

BlurRT
```

Shader：

```text
Gaussian Blur
```

---

第三步：

再模糊：

```text
BlurRT

↓

BlurRT2
```

---

第四步：

合成：

```text
SceneRT

+

BlurRT2

↓

Screen
```

整个过程：

几乎全是：

```text
Blit()
```

---

# Unity 中的 Blit

以前：

```csharp
Graphics.Blit(src, dst);
```

内部就是：

```text
Draw FullScreen Quad
```

---

URP：

已经不推荐：

```csharp
Graphics.Blit()
```

而是：

```csharp
Blitter.BlitCameraTexture()
```

或者：

```csharp
CoreUtils.DrawFullScreen()
```

或者：

```text
RenderGraph

↓

AddBlitPass()
```

因为：

它们效率更高。

---

# Blit 可以做什么？

最简单：

复制：

```text
Source

↓

Destination
```

Shader：

```hlsl
return tex;
```

---

颜色：

```text
Source

↓

Shader

↓

Gray

↓

Destination
```

Shader：

```hlsl
gray=(r+g+b)/3;
```

---

模糊：

```text
Source

↓

Blur Shader

↓

Destination
```

---

反色：

```text
Source

↓

Shader

↓

1-color
```

---

边缘检测：

```text
Source

↓

Sobel

↓

Destination
```

都是：

```text
Blit
```

---

# Blit 为什么只需要画一个矩形？

因为：

Source：

已经是一张纹理。

GPU：

只需要：

```text
□□□□□□□□

覆盖整个屏幕
```

每个 Pixel：

```text
uv

↓

Texture.Sample()

↓

Output
```

所以：

Blit：

DrawCall：

只有：

```text
1
```

但是：

Fragment：

会执行：

```text
1920×1080

≈200万次
```

所以：

Blit：

CPU 很轻。

GPU：

压力主要来自：

Fragment Shader。

---

# 在你们 MMO 项目里的 Blit

你前面提到：

```text
Scene

↓

720P
```

↓

```text
UI

↓

1440P
```

实际上：

中间：

就是：

```text
SceneRT(720P)

↓

Blit

↓

BackBuffer(1440P)
```

Blit：

负责：

把：

```text
720P
```

放大：

```text
1440P
```

Shader：

可以：

```text
Nearest

Linear

FSR

DLSS

XeSS
```

都是：

一种：

```text
Blit Shader
```

---

# 面试中更深入的问题：为什么 Blit 比重新渲染场景便宜？

这是一个很经典的问题。

假设你的场景有：

```text
10000 个 Mesh
500 种材质
100 万个三角形
```

重新渲染一遍意味着：

- 再次进行 Culling。
- 再次提交大量 Draw Call。
- Vertex Shader 再执行一遍。
- Fragment Shader 再执行一遍。

而 **Blit** 呢？

它只做：

```text
1 个全屏三角形（或 Quad）

↓

采样一张已有的纹理

↓

输出到目标
```

也就是说：

- **没有场景遍历。**
- **没有 Mesh 绘制。**
- **没有顶点变换。**
- **只有一次全屏绘制和纹理采样。**

因此，Blit 是现代渲染中处理后处理、动态分辨率、HDR 合成等操作的基础工具，也是为什么你们这种 **SRP MMO** 能够做到"场景低分辨率 + UI 高分辨率"的关键步骤。

