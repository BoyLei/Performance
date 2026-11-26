# Unity纹理回退机制

会话 ID：`6aeb1a4a-95c8-83e8-9791-9e512c5053e1`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 b7f20f8f-3d76-4d37-8f04-05638d9bd3f1

### 用户

所谓的 1080p / 720p / 2k / 4k 分辨率 到底是什么意思， 什么是 设计分辨率， 实际分辨率，  什么是 后处理 ，有哪些后处理， 什么是 bloom ， 升降采样 是啥，为啥要这么做

### 助手

这些概念其实属于同一套图形渲染知识体系。尤其是在 Unity 手游开发中，**分辨率、RenderTexture、升降采样、后处理、Bloom、UI 清晰度、GPU 性能**之间都有直接关系。

我按照一个游戏画面从渲染到最终显示的过程来讲，重点解释三个问题：

1. 这些概念在 GPU 层面究竟是什么？
2. Unity 是怎么实现的？
3. 为什么手游需要这些技术，它们解决了什么问题，又付出了什么代价？

# 一、1080P、720P、2K、4K 到底是什么意思？

分辨率最本质的含义就是：

**一张二维图像由多少个像素组成。**

例如 1920×1080，代表横向有 1920 个像素，纵向有 1080 个像素。

| 常见名称 | 分辨率（宽×高） | 总像素数 |
|--------|--------|--------|
| 720P | 1280×720 | 约 92 万 |
| 1080P / FHD | 1920×1080 | 约 207 万 |
| 2K（DCI） | 2048×1080 | 约 221 万 |
| QHD / 1440P | 2560×1440 | 约 369 万 |
| 4K UHD | 3840×2160 | 约 829 万 |

注意两个容易混淆的地方。

**第一，2K 并不严格等于 2560×1440。**

严格来说，2K 通常指横向约 2000 像素的分辨率。但在消费级显示器市场中，2560×1440 也经常被称为 2K。

**第二，4K 的像素数量是 1080P 的四倍，而不是两倍。**

因为宽度和高度都翻倍了：

\[
(1920\times2)\times(1080\times2)=4\times1920\times1080
\]

这对游戏性能影响非常大。

假设同一个场景分别以 720P、1080P、4K 渲染，仅从需要处理的像素数量来看：

genui{"charts_widget_v2":{"content":{"chartType":"bar","meta":{"title":"\u4e0d\u540c\u5206\u8fa8\u7387\u7684\u50cf\u7d20\u6570\u91cf","description":"\u5355\u4f4d\uff1a\u767e\u4e07\u50cf\u7d20"},"xKey":"resolution","series":[{"dataKey":"pixels","label":"\u767e\u4e07\u50cf\u7d20","valueSuffix":" M"}],"yAxisMin":0,"data":[{"resolution":"720P","pixels":0.922},{"resolution":"1080P","pixels":2.074},{"resolution":"1440P","pixels":3.686},{"resolution":"4K UHD","pixels":8.294}]}}}

像素数量增加会提高片元着色、纹理采样、RenderTexture 带宽、部分后处理等工作的成本。

但这不代表 GPU 总耗时一定严格增加四倍，因为顶点处理、DrawCall 等开销并不会按像素数量同比增长。

# 二、什么是实际分辨率、设计分辨率、渲染分辨率？

这三个概念非常容易混淆。

在 Unity 项目里，我建议你明确区分以下四种分辨率。

## 1\. 屏幕物理分辨率

指设备屏幕实际拥有的物理像素数量。

例如手机屏幕是：

```text
2400 × 1080
```

那么这台设备拥有 259.2 万个物理像素。

Unity 中可以通过以下方式查询当前游戏显示分辨率：

```csharp
Debug.Log($"{Screen.width} x {Screen.height}");
```

注意：`Screen.width` 和 `Screen.height` 表示 Unity 当前渲染窗口或显示区域的尺寸，不一定等于屏幕面板的原生物理像素数。

## 2\. 设计分辨率

设计分辨率本质上是**UI 布局使用的一套参考坐标系**。

例如美术按照 1920×1080 设计游戏界面。

这并不意味着游戏必须在 1920×1080 的屏幕上运行。

假设 UI 中一个按钮设计为：

```text
宽度：200
高度：80
位置：(300, 200)
```

这些尺寸和位置通常都是相对于设计参考分辨率的 UI 单位，而不必直接等于最终物理像素。

Unity UGUI 中通常这样设置：

```text
Canvas
 └── Canvas Scaler
       UI Scale Mode: Scale With Screen Size
       Reference Resolution: 1920 × 1080
       Screen Match Mode: Match Width Or Height
```

`CanvasScaler` 负责根据屏幕尺寸计算缩放系数。

需要注意：**CanvasScaler 解决的是 UI 缩放问题，不是自动解决所有屏幕比例下的布局问题。** 刘海屏、安全区域、超宽屏仍然需要 Anchor 和适配逻辑。

## 3\. 场景渲染分辨率

这个概念对于手游性能优化尤其重要。

假设手机实际显示区域为：

```text
2400 × 1080
```

但你希望 3D 场景以较低分辨率渲染：

```text
1600 × 720
```

这时可以让场景 Camera 渲染到一张 1600×720 的 RenderTexture，然后放大到最终显示区域。

而 UI 仍然按最终屏幕尺寸进行渲染。

```svg
<svg viewBox="0 0 340 260" width="100%" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="8" width="320" height="44" rx="7" fill="#64748b" fill-opacity=".12" stroke="#64748b" /><text x="170" y="26" font-size="12" text-anchor="middle" fill="currentColor" font-weight="600">屏幕显示区域 2400 × 1080</text><text x="170" y="41" font-size="10" text-anchor="middle" fill="currentColor">最终输出目标</text><path d="M170 52 V69 M82 69 H258 M82 69 V83 M258 69 V83" fill="none" stroke="#64748b" stroke-width="1.5" /><rect x="8" y="83" width="148" height="64" rx="7" fill="#3b82f6" fill-opacity=".12" stroke="#3b82f6" /><text x="82" y="102" font-size="12" text-anchor="middle" fill="currentColor" font-weight="600">3D 场景 Camera</text><text x="82" y="119" font-size="11" text-anchor="middle" fill="currentColor">1600 × 720</text><text x="82" y="135" font-size="10" text-anchor="middle" fill="currentColor">低分辨率 RenderTexture</text><rect x="184" y="83" width="148" height="64" rx="7" fill="#16a34a" fill-opacity=".12" stroke="#16a34a" /><text x="258" y="102" font-size="12" text-anchor="middle" fill="currentColor" font-weight="600">UI Canvas</text><text x="258" y="119" font-size="11" text-anchor="middle" fill="currentColor">1920 × 1080 设计参考</text><text x="258" y="135" font-size="10" text-anchor="middle" fill="currentColor">按屏幕尺寸输出</text><path d="M82 147 V163 M258 147 V163" stroke="#64748b" stroke-width="1.5" /><rect x="12" y="163" width="140" height="30" rx="5" fill="#3b82f6" fill-opacity=".12" /><text x="82" y="182" text-anchor="middle" font-size="11" fill="currentColor">放大 / Upscale</text><rect x="188" y="163" width="140" height="30" rx="5" fill="#16a34a" fill-opacity=".12" /><text x="258" y="182" text-anchor="middle" font-size="11" fill="currentColor">高分辨率 UI</text><path d="M82 193 V210 H170 V223 M258 193 V210 H170" stroke="#64748b" stroke-width="1.5" fill="none" /><rect x="53" y="223" width="234" height="31" rx="6" fill="#64748b" fill-opacity=".12" stroke="#64748b" /><text x="170" y="243" text-anchor="middle" font-size="12" fill="currentColor" font-weight="600">最终合成并显示</text></svg>
```

这样做的好处是：

- 3D 场景需要处理的像素变少。
- UI 仍然保持较高的显示清晰度。
- 可以根据手机 GPU 性能动态调整场景渲染比例。

这也是很多移动游戏采用的思路。

不过，图中的 UI 设计参考分辨率 1920×1080 不代表 UI 实际只渲染 1920×1080 个像素。

## 4\. RenderTexture 分辨率

RenderTexture 可以理解为 GPU 上的一张可写入纹理。

例如：

```csharp
var rt = new RenderTexture(1600, 720, 24);
camera.targetTexture = rt;
```

此时 Camera 不再直接把画面绘制到默认屏幕目标，而是绘制到这张 RenderTexture。

然后可以把这张纹理放大、后处理、合成或者显示到 UI 上。

**RenderTexture 的尺寸可以完全独立于屏幕分辨率。**

这正是动态分辨率、离屏渲染、后处理等技术的重要基础。

# 三、什么是后处理（Post-processing）？

后处理可以理解为：

**3D 场景已经被 Camera 渲染成一张二维图像，然后 GPU 再对这张图像进行加工。**

例如游戏中的角色、建筑、地面都已经绘制完成，但你希望整个画面有电影感、发光效果或者景深效果。

这时候不一定需要重新渲染场景，而是对渲染结果进行处理。

典型流程：

```text
3D 模型 / 材质 / 光照
          ↓
    Camera 渲染场景
          ↓
    Scene Color Texture
          ↓
    后处理 Pass
       ├─ Bloom
       ├─ Color Grading
       ├─ Tonemapping
       └─ Vignette
          ↓
    最终输出到屏幕
```

注意，后处理并不一定只有一个 Pass。

例如 Bloom 可能包含多个降采样、模糊、升采样和合成 Pass。

## 常见的后处理有哪些？

image_group{"query":["3d game scene bloom effect glowing neon lights before after comparison"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**1\. Bloom（泛光）**

让明亮区域向周围产生光晕。常用于魔法特效、霓虹灯、太阳、武器发光。

---

image_group{"query":["video game color grading cinematic warm cool before after comparison"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**2\. Color Grading（色彩分级）**

调整整体颜色、对比度、饱和度，让场景呈现冷色、暖色或电影风格。

---

image_group{"query":["depth of field game rendering foreground sharp background bokeh example"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**3\. Depth of Field（景深）**

模拟相机对焦，焦点附近清晰，远处或近处模糊。

---

image_group{"query":["video game motion blur racing car fast movement screenshot"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**4\. Motion Blur（运动模糊）**

模拟高速运动时的拖影，需要考虑运动信息、相机运动等。

---

image_group{"query":["ambient occlusion SSAO 3d architectural scene comparison"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**5\. SSAO（屏幕空间环境光遮蔽）**

根据深度、法线等信息估计物体接触区域的遮蔽，让墙角、缝隙和物体接触处更有层次感。

还有 Tonemapping（色调映射）、Vignette（暗角）、Chromatic Aberration（色差）、Film Grain（胶片颗粒）等。

SSAO 通常也被归入屏幕空间效果，但在 URP 中它通常由 Renderer Feature 实现，而不是普通的 Volume 后处理项。

# 四、Bloom 到底是怎么实现的？

Bloom 是非常典型的多 Pass 后处理，理解它之后，你对升降采样也会有比较清晰的认识。

image_group{"query":["Unity URP bloom glowing fantasy game environment bright magical light","game environment without bloom clean sharp emissive lighting"],"aspect_ratio":"5:3","layout":"carousel"}

Bloom 的核心目的不是简单提高亮度，而是**让高亮区域的能量在视觉上扩散到周围像素**。

例如一把发光的剑，原本只有剑本身的像素很亮。Bloom 会让剑周围也出现一圈柔和光晕。

一个典型 Bloom 算法可以分成四步。

## 第一步：提取高亮区域

假设场景图像中有很多像素：

```text
普通地面：亮度 0.3
人物衣服：亮度 0.6
发光武器：亮度 4.0
```

我们设置一个阈值：

```text
Threshold = 1.0
```

那么低于阈值的像素被过滤，高亮区域被保留下来。

实际算法通常会有软阈值过渡，避免突然截断。

## 第二步：降采样（Downsampling）

把高亮图像缩小。

例如：

```text
1920 × 1080
      ↓
 960 × 540
      ↓
 480 × 270
      ↓
 240 × 135
      ↓
 120 × 68
```

为什么要缩小？

因为我们要对图像进行模糊处理。

如果直接对 1920×1080 的每一个像素执行多次模糊采样，开销会比较大。

缩小之后，需要处理的像素数量显著减少。

## 第三步：模糊与升采样（Upsampling）

把低分辨率的模糊图像逐级放大，与上一层图像合成。

不同层级产生不同尺度的模糊。

- 较高分辨率层保留较小范围的光晕。
- 较低分辨率层产生较大范围的柔和扩散。
- 多层合成后形成自然的 Bloom。

## 第四步：与原图合成

最后把 Bloom 结果与场景原图进行合成。

简化公式：

\[
C_{\text{result}}=C_{\text{scene}}+kC_{\text{bloom}}
\]

其中 \(k\) 控制 Bloom 强度。

实际 HDR 渲染中还涉及曝光、Tonemapping 和色彩空间等问题，因此最终显示不一定是简单的像素加法。

Unity URP 的 Bloom 提供 Threshold、Intensity、Scatter、Downscale、Max Iterations 等参数。citeturn345763search2turn345763search4

# 五、升采样、降采样究竟是什么？

这是你需要重点掌握的概念，因为它不只用于 Bloom，还用于动态分辨率、SSAO、模糊、景深等大量图形技术。

## 1\. 降采样：大图变小图

例如把 4×4 的图像变成 2×2。

降采样不是简单删除像素。

为了减少锯齿、闪烁和混叠，通常需要先进行适当的过滤，再生成低分辨率图像。

最简单的理解是：把邻近像素的信息进行加权汇总。

## 2\. 升采样：小图变大图

升采样是反过来的操作，例如 2×2 放大成 4×4。

但有一个关键问题：

**原图只有四个像素，放大之后需要十六个像素，多出来的十二个像素从哪里来？**

答案是通过算法估算。

常见方法包括：

| 算法 | 特点 |
|--------|--------|
| Nearest Neighbor | 最近邻复制，速度快但容易出现像素块 |
| Bilinear | 双线性插值，平滑但容易模糊 |
| Bicubic | 利用更多邻域信息，通常更锐利 |
| FSR 1 | 空间重建和锐化 |
| TAAU / 时域重建 | 结合历史帧、运动信息等提高重建质量 |

例如双线性插值会参考目标位置周围的四个输入像素，根据距离计算加权结果。

所以升采样不会凭空恢复原始图像的全部细节，只能尽可能重建视觉上合理的结果。

## 3\. 为什么先降采样再升采样？

主要有两个目的。

**第一，降低 GPU 成本。**

一张 1920×1080 的图像有约 207 万像素。

降到 960×540 后只有约 52 万像素。

也就是说：

\[
\text{像素处理量}=\frac14
\]

对于很多以像素处理和纹理采样为主要开销的后处理，降采样能明显降低成本。

当然，这不代表整个后处理耗时一定降为四分之一，因为还存在 RT 切换、读写、合成等开销。

**第二，构造不同尺度的图像信息。**

Bloom 的大范围光晕、景深的模糊、环境光遮蔽的低频信息，都可以通过低分辨率图像高效实现。

# 六、Unity URP 中怎么使用这些技术？

对于 URP 项目，可以从两个地方入手。

## 1\. 场景分辨率：Render Scale

在 URP Asset 中找到：

```text
Quality
    Render Scale = 0.75
```

假设输出目标为 1920×1080：

\[
1920\times0.75=1440
\]

\[
1080\times0.75=810
\]

场景会以约 1440×810 的尺寸渲染，再放大到目标输出尺寸。

**Render Scale 模拟计算** (×)

> **滑块**
>
> 当前值不可用。
>
> **范围：** 0.5 至 1.25
>
> **步长：** 0.05

实际场景渲染尺寸

## ×

相对原生像素量

## %

像素处理量比例 %

以 1920×1080 为输出目标计算。这里展示的是场景像素数量，不代表最终帧率或 GPU 耗时。

在 Unity 2022 的 URP 中，Render Scale 就是比较直接的场景降分辨率手段。Unity 官方文档也说明了它与最终 UI 分辨率的区别。citeturn345763search1turn345763search5

不过要注意 UI 的渲染模式、Camera Stack、后处理顺序，以及是否存在自定义 Renderer Feature，不能认为所有 UI 都必然不受 Render Scale 影响。

## 2\. 后处理：Global Volume

URP 中可以通过以下步骤开启 Bloom：

1. Camera 中开启 Post Processing。
2. 场景中创建 Global Volume。
3. 创建 Volume Profile。
4. Add Override → Post-processing → Bloom。
5. 设置 Threshold、Intensity 等参数。

具体菜单和属性会随 URP 版本有所不同。citeturn345763search9

# 七、站在手游性能优化角度，应该如何理解？

假设你开发一款 MMO 手游，设备输出尺寸为 2400×1080。

一种可行的设计是：

| 渲染阶段 | 分辨率策略 |
|--------|--------|
| 3D 场景 | 1600×720 |
| Bloom | 进一步降采样 |
| SSAO | 半分辨率或其他低分辨率策略 |
| 场景 Upscale | 放大至最终输出 |
| UI | 尽量保持输出分辨率 |
| 最终合成 | 2400×1080 |

这样做的核心不是单纯追求低分辨率，而是**把有限的 GPU 性能分配到玩家更敏感的画面部分**。

玩家通常更容易注意到 UI 文字模糊、按钮边缘不清晰，而场景中某些纹理和远景细节经过适当升采样后，视觉损失可能相对可接受。

但还需要注意三个问题：

- 场景降分辨率主要减少像素相关成本，对 CPU 脚本、DrawCall、顶点处理等瓶颈帮助有限。
- Bloom 的低分辨率 RT 可以降低模糊成本，但也可能产生光晕闪烁、边缘伪影。
- 多张 RenderTexture 会增加显存占用和带宽开销，应尽量使用临时 RT 复用、合理的格式以及 RenderGraph 等资源管理机制。

---

## 八、把这些概念串成一句话

**屏幕分辨率**决定最终显示目标的像素尺寸；**设计分辨率**决定 UI 参考布局；**渲染分辨率**决定场景实际绘制多少像素；**后处理**负责加工已经渲染出来的图像；**降采样**减少处理的数据量或构造低频信息；**升采样**把低分辨率结果重建到更高分辨率；而 **Bloom** 就是综合使用亮度提取、降采样、模糊、升采样和合成的一种后处理效果。

我建议下一步深入一个更底层的问题：

**Unity 的 Camera 到底把画面画在哪里？RenderTexture、FrameBuffer、Color Buffer、Depth Buffer、Blit、GPU 显存之间是什么关系？**

把这一部分弄明白，再看 URP 的 Renderer、Render Pass、Bloom 源码和场景/UI 分辨率分离方案，就会容易很多。

## 轮次 85f46334-72e7-42f0-843b-ed9878fefb41

### 用户

继续

### 助手

接下来我们深入 Unity 渲染的底层机制。

前面讲了分辨率、RenderTexture、后处理、Bloom、升降采样。现在有一个核心问题：

**Camera 渲染出来的画面到底存放在哪里？GPU 又是如何把这张画面显示到手机屏幕上的？**

理解这个问题，需要搞清楚六个概念：

1. FrameBuffer（帧缓冲）
2. Color Buffer（颜色缓冲）
3. Depth Buffer（深度缓冲）
4. RenderTexture（渲染纹理）
5. Render Pass（渲染通道）
6. Blit（图像复制或处理）

# 一、Camera 并不是直接往屏幕上画东西

先看一张完整的渲染流程图。

简化流程：实际 URP 会根据 Renderer、平台和渲染特性选择不同的中间目标与 Pass。

这里最关键的一点：

**Camera 是渲染视角和渲染任务的配置对象，而不是一块存储像素的内存。**

真正保存渲染结果的是 GPU 使用的图像资源。

---

# 二、什么是 FrameBuffer？

Framebuffer（帧缓冲）这个词容易产生误解。

很多人以为 FrameBuffer 就是一块存放完整画面的内存。

但在 OpenGL 语义中，**Framebuffer Object（FBO）本质上是一个渲染目标的组织对象**，它关联颜色、深度、模板等附件。

在 Vulkan、Metal 等现代图形 API 中，对应的资源组织方式有所不同，但概念类似。

可以理解为：

```text
Framebuffer
    │
    ├── Color Attachment
    │       └── 保存颜色结果
    │
    ├── Depth Attachment
    │       └── 保存深度
    │
    └── Stencil Attachment
            └── 保存模板值
```

GPU 执行绘制命令时，会向当前绑定的渲染目标写入结果。

## 1\. Color Buffer：颜色缓冲

假设渲染分辨率是 1920×1080，格式为 RGBA8。

每个像素占 4 字节：

\[
1920\times1080\times4=8,294,400\text{ Bytes}
\]

也就是约 7.91 MiB。

Color Buffer 存储的通常是每个像素的颜色值。

例如：

```text
Pixel (100, 200)
R = 255
G = 128
B = 0
A = 255
```

这就是一个橙色像素。

但是注意，Color Buffer 不一定是 RGBA8。

如果使用 HDR，可能是：

```text
R16G16B16A16_SFloat
```

每个像素需要 8 字节。

因此，同样是 1080P，HDR Color Buffer 的存储需求可能是 RGBA8 的两倍。

## 2\. Depth Buffer：深度缓冲

深度缓冲解决的是一个非常基础的问题：

**多个三维物体投影到同一个屏幕像素时，哪个物体应该显示在前面？**

例如：

```svg
<svg viewBox="0 0 340 190" width="100%" xmlns="http://www.w3.org/2000/svg"><rect x="18" y="18" width="304" height="154" rx="8" fill="#64748b" fill-opacity=".07" stroke="#64748b" stroke-opacity=".4" /><path d="M42 137 H297" stroke="#64748b" stroke-dasharray="4 4" /><rect x="91" y="54" width="95" height="70" rx="3" fill="#3b82f6" fill-opacity=".78" /><rect x="151" y="81" width="103" height="70" rx="3" fill="#d97706" fill-opacity=".75" /><circle cx="169" cy="105" r="5" fill="#fff" stroke="#1e293b" /><path d="M169 105 L271 42" stroke="currentColor" stroke-dasharray="3 3" opacity=".7" /><text x="275" y="35" font-size="11" fill="currentColor" text-anchor="middle">重叠像素</text><text x="112" y="43" font-size="11" fill="#3b82f6" font-weight="600">物体 A</text><text x="219" y="162" font-size="11" fill="#d97706" font-weight="600">物体 B</text></svg>
```

假设两个物体的片元都对应同一个屏幕像素：

```text
物体 A：深度值 0.3
物体 B：深度值 0.7
```

在常规的 Less 深度测试中，0.3 更近，因此 A 可以遮挡 B。

不过 Unity/URP 在部分平台上会使用 Reversed-Z（反向深度），此时通常是更大的深度值代表更近，深度比较规则也会相应变化。

Depth Buffer 的核心作用不变：通过深度测试决定片元是否被遮挡。

## 3\. Stencil Buffer：模板缓冲

Stencil Buffer 通常存储每个像素的模板标记，用于限制某些区域是否允许绘制。

例如：

- UI Mask
- 特定区域的描边
- 门户效果
- 局部特殊渲染

UGUI 的部分 Mask 实现就依赖 Stencil。

---

# 三、RenderTexture 和 FrameBuffer 有什么区别？

这是 Unity 开发中非常重要的区别。

**RenderTexture 是 Unity 暴露给开发者的渲染目标资源；Framebuffer 则是底层图形 API 用于组织渲染附件的概念。**

你可以这样创建 RenderTexture：

```csharp
RenderTexture rt = new RenderTexture(
    1920,
    1080,
    24,
    RenderTextureFormat.ARGB32
);

rt.Create();

camera.targetTexture = rt;
```

这段代码的意思是：

让 Camera 将渲染结果写入这张 RenderTexture，而不是直接输出到默认屏幕目标。

在底层，Unity 会为它创建或关联相应的 GPU 资源与渲染目标配置。

但要注意：

**RenderTexture 并不等于 CPU 内存中的 Texture2D。**

通常它主要位于 GPU 可访问的内存中。

如果你想从 CPU 读取 RenderTexture 的像素，往往需要 GPU → CPU 数据传输。

例如 `Texture2D.ReadPixels` 或 `AsyncGPUReadback`。

这类操作涉及同步或数据传输成本，尤其是同步 ReadPixels，可能造成明显卡顿。

---

# 四、什么是 Render Pass？

可以把 Render Pass 理解为一次具有明确渲染目标和处理职责的渲染阶段。

例如一帧画面可能包含：

```text
Shadow Pass
    ↓
Opaque Pass
    ↓
Skybox Pass
    ↓
Transparent Pass
    ↓
Post-processing Pass
    ↓
Final Output
```

这里有一个容易误解的地方：

**一个 Render Pass 并不等于一个 DrawCall，也不一定等于一次 GPU 渲染目标切换。**

例如 Opaque Pass 可能绘制几百个 Mesh，对应几百个 DrawCall。

而在现代图形 API 和 Unity RenderGraph 中，多个逻辑 Pass 也可能被合并或优化，减少不必要的内存读写。

这对于手机 GPU 尤其重要。

## 为什么手机 GPU 很关注 Render Pass？

很多移动 GPU 采用 Tile-Based Rendering（基于图块的渲染）架构。

例如将屏幕划分为很多小块：

```text
┌────┬────┬────┬────┐
│ T0 │ T1 │ T2 │ T3 │
├────┼────┼────┼────┤
│ T4 │ T5 │ T6 │ T7 │
├────┼────┼────┼────┤
│ T8 │ T9 │T10 │T11 │
└────┴────┴────┴────┘
```

GPU 可以利用片上高速存储处理一个 Tile 的颜色、深度等数据，减少对外部显存的访问。

如果渲染流程频繁要求：

```text
写入 RenderTexture A
    ↓
从显存读取 A
    ↓
写入 RenderTexture B
    ↓
再读取 B
```

就可能增加显存带宽消耗。

所以，手游后处理优化不仅要考虑像素数量，还要考虑 **RT 的读写次数、带宽、Load/Store 操作以及 Pass 的组织方式**。

---

# 五、Blit 究竟是什么？

Blit 是图形开发里非常常见的操作。

最简单的理解：

**Blit 是把一张图像复制、缩放或者通过 Shader 处理后写入另一张图像。**

例如：

```csharp
Graphics.Blit(source, destination);
```

这个操作可以用于：

- 复制图像。
- 把低分辨率图像放大。
- 把高分辨率图像缩小。
- 执行自定义全屏 Shader。
- 合成后处理结果。

例如：

```csharp
Graphics.Blit(
    source,
    destination,
    material
);
```

其中 `material` 可以包含一个 Shader。

Shader 读取 source 的像素，计算后输出到 destination。

要注意，Blit 不一定是底层 API 的简单内存复制。它可能通过全屏三角形或其他方式执行图像处理，具体取决于 API 和实现。

在现代 URP 的自定义渲染流程中，通常更推荐使用对应版本提供的 Blitter、RTHandle 或 RenderGraph API，而不是无条件使用旧式 `Graphics.Blit`。

---

# 六、Bloom 为什么需要多个 RenderTexture？

现在可以把前面的知识串起来了。

假设 Camera 渲染出一张 1920×1080 的 HDR 场景图像。

Bloom 可能执行如下操作：

每一个中间阶段都可能需要一张临时 RenderTexture。

例如：

```text
RT0: SceneColor
RT1: BloomMip0
RT2: BloomMip1
RT3: BloomMip2
RT4: BloomUpsample
```

实际 URP 实现可能复用 RT 或使用不同的中间资源布局。

为什么不能只用一张 RT？

因为很多图像算法需要同时读取旧图像和写入新图像。

如果直接在同一张纹理上边读边写，可能产生读写冲突或未定义行为，除非使用专门支持这种访问的机制。

因此经常需要 Ping-Pong Buffer（乒乓缓冲）：

```text
Pass 1: 读取 A → 写入 B
Pass 2: 读取 B → 写入 A
Pass 3: 读取 A → 写入 B
```

不过这不意味着每个 Pass 都要新建永久纹理。临时 RT 可以复用，从而降低峰值内存。

---

# 七、为什么场景降低分辨率，而 UI 仍然可以保持清晰？

现在回到手游架构设计。

假设设备输出分辨率为：

```text
2400 × 1080
```

你希望：

```text
场景：1600 × 720
UI：2400 × 1080
```

一种典型的实现方式是：

```svg
<svg viewBox="0 0 340 270" width="100%" xmlns="http://www.w3.org/2000/svg"><rect x="10" y="10" width="151" height="64" rx="7" fill="#3b82f6" fill-opacity=".10" stroke="#3b82f6" /><text x="85" y="32" text-anchor="middle" font-size="12" fill="currentColor" font-weight="600">Scene Camera</text><text x="85" y="51" text-anchor="middle" font-size="11" fill="currentColor">1600 × 720</text><rect x="179" y="10" width="151" height="64" rx="7" fill="#16a34a" fill-opacity=".10" stroke="#16a34a" /><text x="255" y="32" text-anchor="middle" font-size="12" fill="currentColor" font-weight="600">UI Camera / Canvas</text><text x="255" y="51" text-anchor="middle" font-size="11" fill="currentColor">2400 × 1080</text><path d="M85 74 V96 M255 74 V140" stroke="#64748b" stroke-width="1.5" /><rect x="20" y="96" width="131" height="43" rx="6" fill="#3b82f6" fill-opacity=".10" stroke="#3b82f6" /><text x="85" y="113" font-size="11" text-anchor="middle" fill="currentColor">Scene RT</text><text x="85" y="128" font-size="10" text-anchor="middle" fill="currentColor">低分辨率颜色缓冲</text><path d="M85 139 V158" stroke="#64748b" stroke-width="1.5" /><rect x="20" y="158" width="131" height="42" rx="6" fill="#3b82f6" fill-opacity=".10" stroke="#3b82f6" /><text x="85" y="175" font-size="11" text-anchor="middle" fill="currentColor">Upscale</text><text x="85" y="189" font-size="10" text-anchor="middle" fill="currentColor">放大场景</text><path d="M85 200 V219 H170 V230 M255 140 V219 H170" stroke="#64748b" fill="none" stroke-width="1.5" /><rect x="59" y="230" width="222" height="34" rx="6" fill="#64748b" fill-opacity=".12" stroke="#64748b" /><text x="170" y="251" text-anchor="middle" font-size="12" font-weight="600" fill="currentColor">最终合成 2400 × 1080</text></svg>
```

在这种设计中：

Scene Camera 的输出先放大到最终目标，然后再叠加高分辨率 UI。

这有一个非常重要的好处：

**UI 不会跟着场景一起经历低分辨率渲染和放大过程。**

例如 UI 文字原本是 24 像素高，如果先渲染到低分辨率 RT 再放大，字体边缘可能变得模糊。

但如果 UI 直接以输出分辨率渲染，就能避免这类额外模糊。

不过实现时还需要考虑：

- UI 是否需要被场景后处理影响。
- UI 和场景之间是否存在遮挡关系。
- UI 是否使用 Screen Space - Overlay。
- Camera Stack 的渲染顺序。
- 最终合成是否增加一次全屏 Blit。
- 不同设备上场景 Render Scale 的动态调整。

---

# 八、再深入一点：RenderTexture 的内存究竟怎么算？

假设你有以下渲染目标：

| 资源 | 分辨率 | 格式 | 约占内存 |
|--------|--------|--------|--------|
| Scene Color | 1920×1080 | RGBA16F | 15.82 MiB |
| Depth | 1920×1080 | D24 | 约 5.93 MiB\* |
| Bloom RT 1 | 960×540 | RGBA16F | 3.96 MiB |
| Bloom RT 2 | 480×270 | RGBA16F | 0.99 MiB |
| Bloom RT 3 | 240×135 | RGBA16F | 0.25 MiB |

\*D24 按每像素 3 字节估算逻辑数据量；实际 GPU 内存分配可能因 D24S8、对齐和平台实现而更高。

仅这些资源，理论数据量就约为 27 MiB。

但实际 GPU 内存还可能包括：

- MSAA 采样存储。
- 额外的 Color/Depth 副本。
- 双缓冲或三缓冲交换链。
- RT 对齐和驱动内部资源。
- 临时资源生命周期重叠。

所以 GPU Profiler 中的实际内存占用不一定等于简单计算结果。

---

# 九、作为 Unity 开发者，你应该重点掌握什么？

如果你准备阅读 URP 源码，我建议按照下面这个顺序：

**第一阶段：Camera 与 Render Target**

理解 Camera、RenderTexture、Color/Depth Buffer，以及 GPU 在哪里保存画面。

**第二阶段：Render Pass 与 Renderer**

理解 URP 如何安排 Opaque、Transparent、Post-processing 等渲染阶段。

**第三阶段：Blit 与图像处理**

理解全屏 Shader、RT 读写、升降采样、Bloom 和图像合成。

**第四阶段：移动 GPU 性能**

理解 Tile-Based Rendering、显存带宽、Overdraw、MSAA 和 Render Pass 合并。

这里还有一个更底层、也更容易产生误解的问题：

**假设 Camera 已经把场景渲染到 RenderTexture A，随后我们调用 Blit(A, B)，GPU 到底做了什么？它是把 A 的所有像素先读取到 CPU，再复制到 B 吗？还是直接在 GPU 内部完成？**

答案是：通常完全在 GPU 侧完成，不需要 CPU 读取像素。CPU 主要负责提交渲染命令，GPU 读取 A、执行采样或 Shader 运算，再写入 B。

理解这个过程，就可以进一步研究 Unity 的 CommandBuffer、GPU 命令队列、RenderGraph，以及为什么频繁 Blit 可能导致移动设备性能下降。

## 轮次 01ff69b9-c9c1-4037-addf-2b13a3843a92

### 用户

bloom 的时候， 会先将采样，将分辨率降低， 然后再升采样。那么升采样是在哪一步完成？ CPU 处理还是 gpu 处理？ 场景 如果低分辨率 UI高分辨率， 那么最终合并的时候， 是在 cpu 端 还是 在gpu 处理

### 助手

这两个问题的答案都是：**GPU 处理。CPU 主要负责组织渲染流程、提交命令，而不是亲自处理图像像素。**

你问的其实涉及 GPU 渲染架构中一个非常重要的分工：

- CPU：决定什么时候渲染、使用什么 RenderTexture、执行什么 Pass、绑定什么材质和 Shader。
- GPU：真正读取纹理像素、执行采样、计算颜色、升降采样、混合和写入目标纹理。

我们分别看。

# 一、Bloom 的升采样到底在哪里完成？

先回顾 Bloom 的处理流程。

假设场景分辨率是 1920×1080。

## Bloom 多级分辨率处理

**提取高亮区域**

1920 × 1080

**Downsample 1**

960 × 540

**Downsample 2**

480 × 270

**Downsample 3**

240 × 135

**低分辨率模糊结果**

**Upsample 1**

240 × 135 → 480 × 270

**Upsample 2**

480 × 270 → 960 × 540

**Upsample 3**

960 × 540 → 1920 × 1080

**与原始场景图像合成**

这里需要注意：上面是为了理解而简化的三级示意，并不是所有 Bloom 实现都严格采用这个分辨率和顺序。

## 1\. GPU 是如何完成升采样的？

假设现在有一张：

```text
RT_A：240 × 135
```

需要放大成：

```text
RT_B：480 × 270
```

GPU 并不是让 CPU 把 240×135 的像素读取出来，再计算 480×270 的像素。

而是执行一个全屏绘制任务。

大致流程：

```text
CPU
 │
 ├── 创建/获取 RT_B
 ├── 设置 Shader 和纹理参数
 ├── 提交 Draw Command
 │
 ▼
GPU
 │
 ├── 读取 RT_A
 ├── 执行 Texture Sampling
 ├── 执行插值计算
 ├── 执行 Bloom 合成计算
 └── 将结果写入 RT_B
```

这里的 Texture Sampling 就是纹理采样。

例如，GPU 要生成 RT\_B 中的一个像素：

```text
目标像素：RT_B[100, 100]
```

Shader 会根据 UV 坐标去 RT\_A 中采样。

如果采用 Bilinear Filtering（双线性过滤），GPU 会参考源纹理中相邻的四个像素：

\[
C = w_1C_1+w_2C_2+w_3C_3+w_4C_4
\]

通过权重计算得到目标像素的颜色。

这整个过程都在 GPU 上执行。

## 2\. Unity 中如何实现？

简化后的代码可能是：

```csharp
Graphics.Blit(source, destination, material);
```

这里：

- source：低分辨率输入纹理。
- destination：高分辨率输出纹理。
- material：负责采样、插值和图像处理的 Shader。

CPU 调用这行代码，主要是提交渲染操作。

真正的像素处理发生在 GPU。

而且这个过程通常不需要 GPU 把图像传回 CPU。

# 二、场景低分辨率，UI 高分辨率，最终怎么合并？

这个问题更有意思。

假设：

```text
手机最终输出：2400 × 1080

3D 场景：1600 × 720
UI：2400 × 1080
```

我们希望场景降低分辨率以节省 GPU 开销，但 UI 依然清晰。

那么整个过程可以这样设计。

## 1\. 两个独立的渲染流程

**场景 Camera** (GPU)

3D 模型、光照、材质

1600 × 720

Scene RenderTexture

1600 × 720

Upscale / 场景后处理

放大到 2400 × 1080

---

**UI Camera** (GPU)

Canvas、Image、Text、Button

2400 × 1080 最终输出目标

---

**GPU 最终合成**

场景图像 + UI 图像

**Backbuffer：2400 × 1080**

提交给显示系统

## 2\. 最终合成是谁做的？

还是 GPU。

假设场景已经放大到 2400×1080，UI 也已经在 2400×1080 的目标上准备好。

那么 GPU 可以通过一次或多次绘制，把 UI 叠加到场景上。

最简单的 Alpha Blend 公式：

\[
C_{out}=C_{UI}\times A_{UI}
+C_{Scene}\times(1-A_{UI})
\]

例如：

```text
场景颜色：蓝色
UI 颜色：白色
UI Alpha：0.5
```

最终得到的就是两者混合的颜色。

这就是 GPU 的 Alpha Blending（透明混合）。

实际上，UI 不一定需要先单独渲染到一张 RT，再与场景合并。

如果使用 UGUI 的 Screen Space - Overlay，UI 可以在场景之后直接绘制到最终输出目标。

例如：

```text
Scene Camera
    ↓
Scene RT (1600×720)
    ↓
GPU Upscale
    ↓
Backbuffer (2400×1080)
    ↓
UGUI Screen Space - Overlay
    ↓
最终显示
```

这里的 UI 就是在 GPU 上直接绘制到最终目标。

这通常比额外创建一张 UI RenderTexture 再合成更简单。

## 3\. 那 CPU 到底做了什么？

可以把一帧渲染理解为下面的分工：

| 工作 | 执行者 |
|--------|--------|
| 决定 Camera 渲染顺序 | CPU |
| 设置 RenderTexture | CPU |
| 创建渲染命令 | CPU |
| 提交 DrawCall | CPU |
| 读取纹理像素 | GPU |
| 降采样 | GPU |
| 升采样 | GPU |
| Bloom 计算 | GPU |
| Alpha Blend | GPU |
| 写入最终颜色 | GPU |

这里有一个容易忽略的细节：

CPU 提交命令不等于 GPU 立即执行命令。

CPU 和 GPU 通常是异步工作的，GPU 有自己的命令队列。CPU 提交完渲染命令后，可以继续执行其他工作，而 GPU 在后台执行绘制。

---

# 三、再补充一个非常重要的架构问题：UI 要不要参与后处理？

假设你的游戏有一个全屏 Bloom。

如果 UI 和场景一起经过 Bloom，会出现什么情况？

例如 UI 上有一个白色按钮。

如果按钮亮度超过 Bloom 阈值，它也可能产生光晕。

有时候这是想要的效果，有时候却不是。

因此，实际项目中经常需要把 UI 和场景的后处理分开。

例如：

```text
3D Scene
   ↓
Scene Post Processing
   ↓
Scene Upscale
   ↓
UI Rendering
   ↓
Final Output
```

这样 UI 不会被场景的 Bloom、景深、运动模糊等效果影响。

但如果希望某些 UI 特效也参与 Bloom，可以将它们放到单独的渲染阶段，或者使用专门的合成方案。

# 四、我想让你建立一个非常重要的认识

你可以把 GPU 理解为一个图像加工流水线。

image_group{"query":["GPU graphics rendering pipeline framebuffer texture sampling shader post processing diagram"],"aspect_ratio":"16:9","layout":"carousel","num_per_query":1}

RenderTexture 就像流水线上的中间产品。

Blit 就像把一个加工阶段的结果交给下一个加工阶段。

Shader 就是具体的加工规则。

Render Pass 则是组织这些加工工作的阶段。

CPU 是负责安排生产顺序和提交任务的调度者，GPU 才是真正执行图像加工的设备。

**下一步最值得深入的是：为什么移动 GPU 使用 TBDR（Tile-Based Deferred Rendering）架构，以及为什么频繁使用 RenderTexture、Blit 会影响手机 GPU 性能。**

这会把你之前关注的手机 TBDR、场景/UI 分辨率分离、Bloom 优化真正串联起来。

## 轮次 9f2aaf2e-7f72-4b81-b69e-c9168dae4fd2

### 用户

继续

### 助手

接下来深入移动 GPU 的 **TBDR（Tile-Based Deferred Rendering，基于图块的延迟渲染）** 架构。

这部分对 Unity 手游性能优化非常重要，因为它能够解释几个看似矛盾的问题：

1. 为什么手机 GPU 的显存带宽很宝贵？
2. 为什么多个 Render Pass 不一定比一个 Pass 慢？
3. 为什么 Bloom 的多次 Blit 可能产生较大的带宽开销？
4. 为什么 `RenderTexture.GetTemporary()` 不代表每次都重新申请显存？
5. 为什么 Unity URP 要引入 Native Render Pass 和 RenderGraph？

# 一、先理解手机 GPU 和桌面 GPU 的区别

传统的 Immediate Mode Rendering（IMR，即时模式渲染）可以简化理解为：

GPU 处理三角形，然后将对应的像素结果写入渲染目标。

而很多移动 GPU 使用 Tile-Based Rendering（基于图块的渲染）。

例如：

- ARM Mali：主要采用 Tile-Based Rendering。
- Qualcomm Adreno：具有基于 Tile 的渲染机制。
- Apple GPU：采用 Tile-Based Deferred Rendering。
- PowerVR：以 TBDR 架构著称。

需要注意，**Tile-Based Rendering 和 TBDR 不是完全相同的概念**。不同厂商的几何处理、隐藏面消除、片元调度机制存在差异，不能认为所有移动 GPU 的内部实现完全一致。

## 1\. 为什么要使用 Tile？

假设手机渲染分辨率是 1920×1080。

GPU 需要处理约 207 万个像素。

如果使用 RGBA8：

\[
1920\times1080\times4\approx7.91\text{ MiB}
\]

如果同时存在深度缓冲、HDR Color Buffer、MSAA，实际需要处理的数据更多。

移动 GPU 受功耗、散热、内存带宽限制，因此会尽可能减少对外部内存的访问。

Tile-Based Rendering 的核心思路是：

**把屏幕分成很多小块，让 GPU 尽可能在片上高速存储中完成一个 Tile 的渲染。**

## 屏幕被划分为多个 Tile

图块大小由 GPU 架构、渲染附件和实现决定，不固定为某一种像素尺寸。

# 二、TBDR 的实际工作流程

假设场景里有 1000 个三角形。

在基于 Tile 的渲染中，可以把工作简化为两个主要阶段。

## 阶段一：几何处理与分箱（Binning）

GPU 首先处理顶点，确定三角形在屏幕上的位置，然后记录哪些三角形可能覆盖哪些 Tile。

例如：

```text
Triangle A → Tile 1、Tile 2
Triangle B → Tile 2
Triangle C → Tile 3、Tile 4
```

这一步通常称为 Binning 或 Tiling。

注意，具体架构可能会在不同阶段执行裁剪、深度相关优化或可见性处理。

## 阶段二：逐 Tile 光栅化

GPU 开始处理每一个 Tile。

GPU 可以在片上高速存储中完成颜色混合、深度测试等工作。

等到 Tile 处理完成后，再根据需要把结果写入外部内存。

这就是为什么移动 GPU 非常关注 Render Target 的 Load/Store 操作。

---

# 三、什么是 Load / Store？为什么影响性能？

在渲染目标的生命周期中，经常会遇到三个操作：

| 操作 | 含义 |
|--------|--------|
| Load | 读取之前已经存在的附件内容 |
| Clear | 将附件初始化为指定值 |
| Store | 保留本次渲染结果，供后续使用 |

假设一张 Color RenderTexture 被用来渲染场景。

如果后续 Pass 还需要采样它，那么当前渲染结果通常必须以某种方式保存为后续可访问的纹理数据。

但如果这张 RT 只用于当前 Pass，后续不再需要，就可能使用 `DontCare` Store Action，让 GPU 不必把无用结果写回外部内存。

例如，深度缓冲仅用于当前阶段的遮挡判断，后面不再读取它，那么有机会省去深度数据的 Store。

这里有个很重要的结论：

**RenderTexture 的内存分配成本和 RenderTexture 的读写带宽成本，是两个不同的问题。**

即使 RT 已经分配好，频繁写入和读取仍然可能消耗大量显存带宽。

# 四、为什么 Bloom 的 Blit 可能比较昂贵？

假设你有一个 1920×1080 的 HDR Color Buffer。

格式为 RGBA16F，每像素 8 字节。

单张图像的数据量约为：

\[
1920\times1080\times8\approx15.82\text{ MiB}
\]

现在执行：

```csharp
Graphics.Blit(source, destination);
```

如果是一次完整的全屏读取和写入，且不考虑缓存、压缩和硬件优化，那么理论数据传输量约为：

\[
15.82+15.82=31.64\text{ MiB}
\]

在 60 FPS 下：

\[
31.64\times60\approx1.85\text{ GiB/s}
\]

这只是一次全分辨率 Blit 的粗略理论数据量，并不是 GPU 性能分析器测得的实际 DRAM 带宽。

实际带宽还取决于缓存命中、纹理压缩、采样次数、片上存储、RT 格式以及硬件实现。

## 为什么 Bloom 要降低分辨率？

因为 Bloom 需要反复采样和处理图像。

例如：

```text
1920×1080 → 960×540
960×540  → 480×270
480×270  → 240×135
```

如果第一层是 960×540，那么其像素数量只有原图的四分之一。

在后续模糊阶段，处理更少的像素就能显著降低成本。

而且 Bloom 的光晕本身是低频、模糊的图像信息，因此不一定需要原始分辨率才能获得良好的视觉效果。

但是，降采样和升采样本身也需要 Pass 和纹理访问，所以并不是层级越多越好。

---

# 五、为什么多个 Render Pass 不一定更慢？

这里需要纠正一个常见的性能优化误区：

**不是 Render Pass 越少，性能就一定越好。**

假设两个渲染阶段：

```text
Pass A：绘制不透明物体
Pass B：绘制透明物体
```

如果它们使用相同的渲染目标，并且满足相关条件，底层图形 API 或 Unity 渲染系统可能在同一个 Native Render Pass 中组织执行。

这样 GPU 有机会在 Tile 内保留颜色和深度数据，而不必在两个逻辑阶段之间完整地写回再读取。

但如果 Pass B 必须把 Pass A 的 Color Buffer 当作普通纹理进行采样，那么就可能需要结束当前渲染阶段，并让图像数据可供后续读取。

可合并的情况

Opaque Pass

Transparent Pass

可能保留 Tile 数据

需要纹理采样

Render to A

Sample A → B

可能产生额外读写

具体是否合并取决于附件、依赖关系、平台 API 和 Unity 渲染实现。

因此，在 URP 优化时，真正应该关注的是：

- Render Target 是否发生不必要的切换。
- 是否存在多余的 Color/Depth Store。
- 是否产生额外的中间 RT。
- Pass 是否能够合并。
- 是否有不必要的全屏采样。

# 六、Unity RenderGraph 为什么重要？

RenderGraph 的核心思想是：

**让开发者描述每个渲染 Pass 需要读取什么、写入什么，再由渲染系统分析资源依赖关系和生命周期。**

例如：

```text
Pass A：写 SceneColor
Pass B：读 SceneColor，写 Bloom
Pass C：读 SceneColor + Bloom，写 FinalColor
```

RenderGraph 可以分析：

- 哪些 Pass 存在依赖。
- 哪些临时纹理可以复用内存。
- 哪些 Pass 或资源没有被最终结果使用。
- 哪些渲染阶段可能被合并。
- 资源什么时候需要创建、使用和释放。

但 RenderGraph 并不保证所有 Pass 都能合并，也不能消除算法本身必须进行的纹理采样。

对于 Unity 2022 URP 14，常见的是传统 `ScriptableRenderPass` 工作流；较新版本的 URP 则提供了 RenderGraph 工作流。

---

# 七、RenderTexture.GetTemporary() 会频繁申请 GPU 内存吗？

看一段代码：

```csharp
RenderTexture rt = RenderTexture.GetTemporary(
    960,
    540,
    0,
    RenderTextureFormat.ARGBHalf
);

// 执行渲染操作

RenderTexture.ReleaseTemporary(rt);
```

`GetTemporary()` 会从 Unity 管理的临时 RenderTexture 池中获取资源。

如果存在符合要求的可复用资源，就有机会复用，而不是每次都重新分配一块 GPU 内存。

但需要注意：

- 复用不代表没有任何管理开销。
- 不同尺寸、格式、MSAA 配置可能影响复用。
- 资源的创建和释放可能触发底层驱动工作。
- `ReleaseTemporary()` 表示归还给临时资源池，不代表立即释放底层显存。
- RT 内容不能假设在重新获取后仍然有效。

所以 Bloom 的多级 RT 通常会使用临时资源管理机制，而不是每帧创建大量永久 RenderTexture。

---

# 八、实际 Unity 项目应该如何排查？

假设你的游戏开启 Bloom 后 GPU 耗时从 8ms 增加到 12ms。

不要立即得出“Bloom 多了几个 Blit，所以慢了 4ms”的结论。

应该先检查具体 GPU 耗时和带宽瓶颈。

image_group{"query":["Unity Frame Debugger render events editor screenshot"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**Frame Debugger**

检查渲染事件顺序、RT 切换、Bloom 的降采样和升采样 Pass，以及每个阶段的渲染目标。

---

image_group{"query":["Unity profiler GPU module timeline screenshot"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**Unity Profiler / GPU Profiler**

查看 GPU 耗时变化，判断 Bloom 是否是主要开销。移动平台的计时能力取决于图形 API 和设备支持。

---

image_group{"query":["Arm Mobile Studio Streamline GPU performance counters screenshot"],"aspect_ratio":"5:4","layout":"carousel","num_per_query":1}

**厂商 GPU 分析工具**

例如 Arm Streamline、Snapdragon Profiler、Xcode GPU 工具。根据设备支持情况，分析纹理采样、带宽、片元处理和 GPU 利用率。

## 九、一个实际的优化例子

假设你的项目配置为：

```text
设备输出：2400 × 1080
场景分辨率：1600 × 720
HDR：开启
Bloom：开启
UI：独立高分辨率渲染
```

我会优先考虑以下渲染流程：

```text
Scene Camera
    ↓
1600 × 720 HDR Scene Color
    ↓
Bloom Downsample Pyramid
    ↓
Bloom Upsample Pyramid
    ↓
Bloom + Scene 合成
    ↓
Tonemapping / Color Grading
    ↓
Upscale 到 2400 × 1080
    ↓
绘制高分辨率 UI
    ↓
Backbuffer
    ↓
Display
```

这个顺序的优点是大部分场景后处理可以在低分辨率执行。

但实际项目也可能采用不同顺序，例如先升采样再进行某些后处理，以保证质量；或者使用时域升采样算法，将升采样与抗锯齿结合。

**尤其要注意：如果你先把场景放大到 2400×1080，再执行 Bloom，那么 Bloom 的输入分辨率就变高了，可能失去一部分降低场景分辨率带来的性能收益。**

---

# 十、最后一个关键问题：为什么移动 GPU 不喜欢频繁读写显存？

因为移动设备通常使用 CPU、GPU 共享的系统内存架构。

GPU 访问外部 DRAM 会消耗带宽和功耗。

而 Tile-Based Rendering 希望尽可能把中间计算留在片上存储中完成。

因此，一次看似简单的全屏 Blit，可能涉及：

1. 从外部内存读取源纹理。
2. 执行纹理过滤和 Shader。
3. 将结果写入目标渲染附件。
4. 在必要时将结果 Store 到外部内存。
5. 处理后续 Pass 对结果的依赖。

不过不能简单理解成“每次 Blit 必然完整读取和写入 DRAM”。缓存、压缩、片上存储和 Pass 合并都可能改变实际的数据流量。

**对于 Unity 手游，优化重点不是机械地减少 DrawCall 或 Blit 数量，而是减少不必要的像素处理、纹理采样、显存传输和同步。**

如果继续往底层深入，下一步就是研究 **TBDR 的 Hidden Surface Removal（隐藏面消除）与 Early-Z、Overdraw 的关系**：为什么两个模型重叠时，有些 GPU 可以避免执行被遮挡像素的 Fragment Shader，而透明物体却往往无法获得同样的优化。这也是 Unity 场景渲染性能优化的核心知识之一。

## 轮次 59f00637-e9d5-4a94-9d67-02160d50d448

### 用户

# Selected text:

## Selection 1
RenderTexture 的内存分配成本和 RenderTexture 的读写带宽成本，是两个不同的问题。

即使 RT 已经分配好，频繁写入和读取仍然可能消耗大量显存带宽。

## My request:
先解释为啥？  然后 在继续

### 助手

这个问题需要从 **GPU 显存、内存分配、数据传输、GPU 缓存以及移动端 TBDR 架构** 五个角度理解。

先说结论：

**RenderTexture 已经分配了 GPU 内存，只代表 GPU 有地方存储像素，并不代表这些像素以后读取和写入就没有成本。**

就像 C\# 中预先分配一个 `byte[]`，可以避免反复 `new`，但你每帧遍历这个数组、读取数据、修改数据，CPU 依然需要执行指令并访问内存。

GPU 的情况类似，但 GPU 还面临一个重要瓶颈：**内存带宽（Memory Bandwidth）**。

# 一、为什么内存分配和读写带宽是两回事？

假设 Unity 创建一张 RenderTexture：

```csharp
RenderTexture rt = new RenderTexture(
    1920,
    1080,
    0,
    RenderTextureFormat.ARGBHalf
);

rt.Create();
```

这里的 `ARGBHalf` 通常对应每像素 64 bit，即 8 字节。

所以这张 RT 的逻辑数据大小为：

\[
1920\times1080\times8=16,588,800\text{ Bytes}
\]

约为 15.82 MiB。

这里存在两种完全不同的成本。

## 1\. 内存分配成本

创建 RenderTexture 时，Unity 需要通过底层图形 API 创建纹理资源，驱动则负责管理对应的 GPU 内存资源。

这个过程可能涉及：

- 申请或预留 GPU 可访问的内存。
- 创建图像资源和相关描述信息。
- 设置尺寸、格式、采样数、用途等。
- 建立渲染目标需要的资源关联。

但要注意，实际物理内存可能由驱动延迟分配，并不一定在调用 `rt.Create()` 时就全部提交。

创建完成后，这张 RT 就可以反复使用。

例如：

```csharp
void Update()
{
    Graphics.Blit(source, rt);
}
```

这段代码并不会因为每帧调用 `Blit`，就必然重新分配 `rt` 的 GPU 内存。

因此，复用 RenderTexture 可以避免重复创建资源的开销。

## 2\. 内存读写成本

但是每次执行：

```csharp
Graphics.Blit(source, rt);
```

GPU 仍然需要处理图像数据。

简化为：

```text
GPU 读取 source 的像素
          ↓
    执行 Shader
          ↓
GPU 写入 rt 的像素
```

即使 `rt` 已经存在一年，这些像素也不会自动更新。

GPU 仍然需要重新计算并写入本帧的结果。

这就涉及内存带宽。

---

# 二、什么是 GPU 内存带宽？

内存带宽指的是单位时间内，内存系统能够传输多少数据。

例如，假设某个 GPU 可以使用的有效内存带宽为：

\[
20\text{ GB/s}
\]

这表示在理想化条件下，每秒最多可以传输约 20 GB 的数据。

注意，这只是一个假设值。真实移动设备的内存带宽还需要与 CPU、ISP、NPU 等组件共享，而且理论峰值不等于应用可持续获得的带宽。

## 举个具体例子

假设有两张 RT：

```text
RT_A：1920 × 1080，RGBA16F
RT_B：1920 × 1080，RGBA16F
```

执行一次全屏 Blit：

```csharp
Graphics.Blit(rtA, rtB);
```

如果每个输出像素读取一个输入像素，再写入一个输出像素，那么逻辑数据访问量约为：

读取 RT\_A

# 15.82 MiB

写入 RT\_B

# 15.82 MiB

---

**单次逻辑读写量**

# 31.64 MiB

按每像素读取一次、写入一次计算，不代表实际 DRAM 总线流量。

假设游戏运行在 60 FPS，每帧执行 5 次类似的全屏处理：

\[
31.64\times5\times60
\approx 9.27\text{ GiB/s}
\]

这还只是这些 Blit 的理想化逻辑读写量。

游戏还有纹理采样、深度缓冲、阴影、其他后处理等大量工作。

因此，即使没有重新申请任何 RT，也可能因为持续的数据读写而出现 GPU 性能瓶颈。

# 三、GPU 不是有缓存吗？为什么还要访问显存？

确实有缓存。

现代 GPU 通常存在多级缓存和专用的片上存储。

我们可以简化为：

概念示意：GPU Cache 与 Tile Storage 并不是所有硬件上都严格串联的层级，实际数据路径取决于 GPU 架构。

这里要区分两个概念：

**GPU Cache**：缓存已经访问过的数据，让后续采样有机会避免重复访问 DRAM。

**Tile Storage**：移动 GPU 用于当前图块渲染的高速片上存储，尤其适合颜色、深度和模板附件的局部处理。

例如，GPU 正在处理一个 Tile。

如果颜色和深度数据都能留在片上存储中，那么多个片元可以在这里完成深度测试、颜色混合，而不必每次都访问外部 DRAM。

但如果后续 Pass 要把上一阶段的完整渲染结果作为普通纹理采样，数据就可能需要从 Tile Storage 转换为后续可访问的纹理资源。

这通常涉及 Store、资源状态转换以及后续的纹理读取。

因此：

**RT 已经分配好，只解决了存储空间的问题；并没有消除数据在 GPU 各级存储之间移动的成本。**

---

# 四、为什么 TBDR 特别在意 RenderTexture 的读写？

假设我们要绘制 100 个不透明物体。

## 情况 A：连续绘制到同一个渲染目标

```text
Begin Render Pass
    ↓
Draw Object 1
    ↓
Draw Object 2
    ↓
...
    ↓
Draw Object 100
    ↓
End Render Pass
```

在支持的移动 GPU 上，颜色和深度数据可以尽可能保留在 Tile Storage 中。

每个 Tile 处理完成后，再根据需要将结果写回外部内存。

这意味着：

即使 100 个物体都产生了绘制操作，也不代表每个物体都会让完整 Color Buffer 在 DRAM 中读写一遍。

## 情况 B：中间频繁执行全屏后处理

```text
Render Scene → RT_A
       ↓
Blit RT_A → RT_B
       ↓
Blit RT_B → RT_C
       ↓
Blit RT_C → RT_D
       ↓
Final Output
```

每个后处理阶段都可能需要读取上一阶段的完整纹理结果。

这可能让原本能保留在片上存储中的数据更频繁地进入外部内存。

当然，并非所有 Blit 都一定导致完整的 DRAM 读写。GPU 缓存、压缩、硬件专用路径以及 Render Pass 优化可能减少实际流量。

但从架构上看，**多次全屏纹理读取和写入，通常比连续在同一个渲染目标上绘制更容易形成带宽压力。**

---

# 五、继续：TBDR、Early-Z、Overdraw 为什么相关？

前面我们理解了 GPU 为什么希望减少显存读写。

接下来要研究另一个非常重要的性能问题：

**GPU 能不能避免计算那些最终根本看不到的像素？**

这就涉及 Overdraw、Early-Z 和 Hidden Surface Removal。

## 1\. 什么是 Overdraw？

Overdraw（重复绘制）指的是同一个屏幕位置，被多个图元反复覆盖和处理的现象。

例如一个屏幕像素位置上，依次存在：

```text
背景地面
    ↓
建筑物
    ↓
角色
    ↓
角色身上的特效
```

假设这些对象都覆盖了同一个像素。

如果 GPU 对每一层都执行了 Fragment Shader，那么就可能产生多次片元计算。

```svg
<svg viewBox="0 0 340 180" width="100%" xmlns="http://www.w3.org/2000/svg"><rect x="15" y="18" width="310" height="145" rx="8" fill="#64748b" fill-opacity=".06" stroke="#64748b" stroke-opacity=".4" /><rect x="45" y="38" width="170" height="93" rx="5" fill="#64748b" fill-opacity=".35" stroke="#64748b" /><rect x="90" y="55" width="170" height="93" rx="5" fill="#3b82f6" fill-opacity=".35" stroke="#3b82f6" /><rect x="135" y="72" width="155" height="77" rx="5" fill="#16a34a" fill-opacity=".35" stroke="#16a34a" /><circle cx="173" cy="97" r="6" fill="#ef4444" stroke="white" stroke-width="2" /><path d="M179 97 L269 35" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4 3" /><text x="271" y="29" font-size="11" text-anchor="middle" fill="currentColor">重复覆盖区域</text><text x="58" y="54" font-size="11" fill="currentColor">A</text><text x="104" y="71" font-size="11" fill="currentColor">B</text><text x="147" y="88" font-size="11" fill="currentColor">C</text></svg>
```

同一像素被多个图元覆盖，并不意味着每一层都一定执行完整的 Fragment Shader。

这里需要特别注意：

**几何覆盖次数不等于 Fragment Shader 实际执行次数。**

因为 GPU 可能通过深度测试提前剔除不可见片元。

## 2\. Early-Z 是什么？

正常情况下，一个片元要经过若干测试和 Shader 计算。

可以简化为：

```text
Rasterization
      ↓
Fragment Shader
      ↓
Depth Test
      ↓
Color Write
```

但如果 GPU 能提前判断某个片元会被已有深度挡住，就可以尝试把深度测试提前：

```text
Rasterization
      ↓
Early Depth Test
      ↓
通过？
   ├── 否 → 丢弃
   └── 是 → Fragment Shader
                    ↓
                Color Write
```

这样，被遮挡的片元就可能不需要执行昂贵的 Fragment Shader。

例如：

```text
建筑物已经写入深度
       ↓
后面的地面片元到来
       ↓
Early-Z 判断被遮挡
       ↓
直接剔除
```

如果地面的 Shader 包含大量纹理采样、复杂光照计算，那么这种提前剔除就能节省不少 GPU 工作。

不过 Early-Z 的实际执行条件受到 Shader、深度写入、Discard、Alpha Test、平台等因素影响，并不是所有材质都能获得相同效果。

## 3\. TBDR 的 Hidden Surface Removal 又是什么？

部分 TBDR 架构能够在真正执行片元着色之前，利用几何和可见性信息减少隐藏表面的着色工作。

这和普通 Early-Z 的目标相似，但实现机制不完全相同。

例如某些 PowerVR 架构，会先处理可见性，再尽量只对最终可见的表面执行片元着色。

这就是 TBDR 中 Deferred（延迟）的重要含义之一。

但是，不能认为所有采用 Tile-Based Rendering 的 GPU 都具有完全相同的隐藏面消除机制。

例如 Mali、Adreno、Apple GPU 的实现细节存在差异。

## 4\. 为什么透明物体往往更难优化？

因为透明物体通常需要与后面的颜色混合。

例如：

\[
C_{out}=\alpha C_{front}+(1-\alpha)C_{back}
\]

如果前面的透明物体 Alpha = 0.5，那么后面的颜色仍然会影响最终结果。

因此，GPU 不能像处理完全不透明物体那样，简单丢弃所有被透明表面覆盖的片元。

Unity 中常见的透明材质通常：

```shaderlab
ZWrite Off
Blend SrcAlpha OneMinusSrcAlpha
```

这意味着：

- 透明物体一般不写入深度缓冲。
- 后续透明物体仍可能被继续绘制。
- 多层透明物体可能产生大量 Fragment Shader 工作和颜色混合。

这也是为什么手游中，大面积半透明粒子、全屏 UI 特效、透明叠层经常会带来明显的 GPU 开销。

---

# 六、一个 Unity 手游的实际例子

假设你的 MMO 游戏中有：

- 20 个角色。
- 100 个半透明粒子特效。
- 多层透明 UI。
- Bloom 后处理。

当 GPU 性能下降时，可能存在两类不同瓶颈。

| 瓶颈类型 | 典型表现 | 优化方向 |
|--------|--------|--------|
| Fragment Shader / Overdraw | 大量透明特效重叠，片元计算过多 | 减少屏幕覆盖面积、透明层数和 Shader 复杂度 |
| 内存带宽 | 多次全屏后处理、大量 RT 读写 | 降低后处理分辨率、减少不必要的中间纹理读写 |

当然，这两类瓶颈也可能同时存在。

例如 Bloom 的降采样 Shader 本身需要多次纹理采样，既消耗计算资源，也可能消耗带宽。

## 最后总结

你最初的问题可以归纳为：

**内存容量决定能够存放多少数据，内存带宽决定单位时间内能够搬运多少数据，而 GPU 计算能力决定能够执行多少运算。**

三者相互关联，但不是同一个概念。

在 Unity 移动端性能优化中，最重要的是先判断当前瓶颈属于：

- GPU 计算 / Fragment Shader。
- GPU 内存带宽。
- 几何处理。
- CPU 提交和脚本。
- 同步等待。

然后再决定是降低 Render Scale、减少 Overdraw、优化 Shader，还是调整 Render Pass 和 RenderTexture 的使用方式。

只有这样，才能避免“减少了 DrawCall，但帧率没有提升”或者“复用了 RenderTexture，但 GPU 耗时仍然很高”这类常见问题。

