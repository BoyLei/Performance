# UGUI 概述解析

会话 ID：`6a44e53f-ff00-83ea-9d79-5ac452e077f2`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 788d0426-17af-40f5-b9c4-91aa5e4a360e

### 用户

对于 UGUI , 说说你的理解

### 助手

UGUI 是 Unity 里比较经典的一套 **运行时 UI 系统**，全称通常指 Unity UI，也就是基于 `Canvas`、`RectTransform`、`Graphic`、`EventSystem` 这一套组件构建的 UI 框架。它主要用于做游戏内界面，比如主菜单、背包、血条、弹窗、设置界面、HUD 等。

我对 UGUI 的理解可以从几个层面来看。

## 1. UGUI 的核心是 Canvas

`Canvas` 可以理解为 UI 世界里的“画布”。所有 UGUI 元素，比如 `Image`、`Text`、`Button`、`Toggle`、`ScrollView`，最终都要挂在 Canvas 下面才能被渲染出来。

Canvas 常见有三种渲染模式：

### Screen Space - Overlay

最常见的模式，UI 直接覆盖在屏幕上，不需要摄像机。

适合：

```text
主菜单
血条
普通 HUD
弹窗
设置界面
```

### Screen Space - Camera

UI 由指定摄像机渲染，可以和摄像机的深度、后处理、分辨率等结合。

适合：

```text
需要和摄像机效果配合的 UI
需要控制 UI 层级和相机关系的场景
```

### World Space

UI 存在于 3D 世界中，像普通物体一样有位置、旋转、缩放。

适合：

```text
角色头顶血条
NPC 对话气泡
场景内交互面板
VR/AR UI
```

简单说，Canvas 是 UGUI 的渲染边界，也是性能优化时最需要关注的对象之一。

---

## 2. UGUI 的布局基础是 RectTransform

普通物体用 `Transform`，UGUI 用的是 `RectTransform`。

`RectTransform` 不只是控制位置、旋转、缩放，它还多了 UI 特有的概念：

```text
Anchor    锚点
Pivot     轴心点
Size      宽高
Position 位置
Stretch  拉伸
```

其中最重要的是 **Anchor**。

Anchor 决定 UI 元素如何跟随父物体变化。比如按钮固定在右下角、血条固定在左上角、面板居中铺满屏幕，基本都靠 Anchor 实现。

可以这样理解：

```text
Transform 关心“物体在世界中的位置”
RectTransform 关心“UI 在矩形区域中的位置和适配关系”
```

所以 UGUI 的 UI 适配，本质上就是在处理 `RectTransform + Anchor + CanvasScaler`。

---

## 3. CanvasScaler 决定分辨率适配

`CanvasScaler` 是 UGUI 里非常重要但经常被忽略的组件。

常见设置是：

```text
UI Scale Mode: Scale With Screen Size
Reference Resolution: 1920 x 1080
Screen Match Mode: Match Width Or Height
```

它的作用是让 UI 在不同分辨率下保持相对一致的大小。

比如你的 UI 是按 1920x1080 做的，如果运行在 2560x1440 或手机屏幕上，CanvasScaler 会帮你按规则缩放。

常见经验：

```text
横屏游戏：通常 Match 偏向 Width 或中间值
竖屏游戏：通常 Match 偏向 Height 或中间值
```

但最终还是要根据 UI 设计稿和目标设备来调。

---

## 4. UGUI 的交互依赖 EventSystem

按钮能点击、ScrollView 能拖动、Toggle 能切换，背后都依赖 `EventSystem`。

UGUI 的交互大概是这样工作的：

```text
输入设备
   ↓
EventSystem
   ↓
GraphicRaycaster
   ↓
找到被点击的 UI
   ↓
执行 Button / Toggle / ScrollRect 等组件逻辑
```

其中 `GraphicRaycaster` 负责在 Canvas 上检测鼠标或手指点到了哪个 UI 元素。

所以如果 UI 点不动，常见检查点是：

```text
场景里有没有 EventSystem
Canvas 上有没有 GraphicRaycaster
目标 UI 的 Raycast Target 是否开启
是否被其他透明 UI 挡住
CanvasGroup 是否禁用了交互
```

---

## 5. UGUI 的显示组件本质上都是 Graphic

`Image`、`RawImage`、`Text` 这类组件都继承自 `Graphic`。

它们最终会生成顶点数据，然后交给 Canvas 渲染。

常见组件：

```text
Image      显示 Sprite
RawImage   显示 Texture
Text       显示文字，老版文本组件
Button     点击组件，本身通常配合 Image
Toggle     开关
Slider     滑动条
ScrollRect 滚动区域
InputField 输入框
```

实际项目里，现在文字通常更推荐使用 **TextMeshPro**，因为它比旧版 `Text` 清晰、灵活、功能更强。

---

## 6. UGUI 的布局系统很方便，但要注意性能

UGUI 提供了很多自动布局组件：

```text
Horizontal Layout Group
Vertical Layout Group
Grid Layout Group
Content Size Fitter
Layout Element
Aspect Ratio Fitter
```

它们适合快速做动态 UI，比如背包格子、排行榜、任务列表等。

但是要注意：

`Layout Group + Content Size Fitter` 如果大量嵌套，或者频繁刷新，会带来比较高的重建开销。

例如：

```text
背包有 500 个格子
每个格子里又有 Layout
每次数量变化都刷新整个列表
```

这种情况下性能会变差。

更好的做法通常是：

```text
减少 Layout 嵌套
静态 UI 尽量不用自动布局
大列表使用对象池
ScrollView 做虚拟列表
必要时手动计算位置
```

---

## 7. UGUI 性能优化的重点是 Canvas 重建

UGUI 最大的性能坑之一是 **Canvas Rebuild**。

当 Canvas 下某个 UI 元素发生变化时，比如：

```text
位置变化
大小变化
文字变化
图片变化
显隐变化
布局变化
```

Canvas 可能需要重新计算和生成渲染数据。

如果一个很大的 Canvas 里有很多 UI，只要其中一个频繁变化，就可能导致整个 Canvas 的重建成本变高。

所以常见优化思路是：

```text
把静态 UI 和动态 UI 分到不同 Canvas
频繁变化的 UI 单独放 Canvas
减少频繁 SetActive
减少频繁修改 Text
减少透明遮挡和 Raycast Target
复杂列表使用对象池
```

比如：

```text
MainCanvas
 ├── StaticPanel       静态背景、固定按钮
 ├── DynamicCanvas     血条、倒计时、金币数量
 └── PopupCanvas       弹窗层
```

频繁变化的金币、倒计时、血条不要和大量静态 UI 混在同一个 Canvas 里。

---

## 8. UGUI 的层级管理很重要

UI 项目稍微复杂一点，就需要清晰的层级结构。

常见做法是把 UI 分成几层：

```text
SceneLayer    场景内 UI
MainLayer     主界面
WindowLayer   普通窗口
PopupLayer    弹窗
GuideLayer    新手引导
ToastLayer    飘字提示
LoadingLayer  加载界面
```

这样做的好处是：

```text
层级清楚
弹窗不会被主界面挡住
提示不会被弹窗挡住
方便统一管理打开和关闭
```

大型一点的项目一般会有自己的 UI 管理器，比如：

```csharp
UIManager.Open<InventoryWindow>();
UIManager.Close<InventoryWindow>();
UIManager.ShowToast("金币不足");
```

这样比到处 `Instantiate` 和 `SetActive` 更容易维护。

---

## 9. UGUI 适合大多数游戏 UI，但不是唯一选择

UGUI 的优点：

```text
成熟稳定
学习成本低
组件丰富
运行时 UI 支持好
适合游戏 HUD、弹窗、背包、商城等
社区资料多
```

缺点：

```text
复杂 UI 容易层级混乱
大量动态 UI 可能有性能问题
自动布局嵌套多了开销较高
样式复用能力不如一些现代 UI 框架
```

Unity 现在还有 UI Toolkit，它更偏声明式、样式化，适合编辑器扩展和一些复杂界面。但在很多游戏运行时 UI 里，UGUI 依然非常常用。

---

## 我的总结

UGUI 可以理解为：

```text
Canvas 负责渲染范围
RectTransform 负责 UI 布局
CanvasScaler 负责分辨率适配
Graphic 负责显示内容
EventSystem 负责交互输入
Layout 负责自动排版
```

真正用好 UGUI，不只是会拖按钮和图片，更重要的是理解：

```text
UI 如何适配不同屏幕
UI 如何分层管理
UI 如何减少 Canvas 重建
UI 如何避免 ScrollView 和 Layout 的性能坑
UI 如何通过代码组织成可维护的窗口系统
```

如果只是小项目，UGUI 可以很快搭界面；如果是中大型项目，就要把它当成一套完整的 UI 架构来设计。

## 轮次 32219ce7-3516-4a25-9f52-f822796ed527

### 用户

现在你是一个资深的unity工程师，让你来面试我，你会问些什么

### 助手

如果我是一个**资深 Unity 工程师（5~10 年经验）**来面试你，我不会一直问 API，而是会围绕 **"原理、架构、性能、项目经验、解决问题能力"** 来考察。很多候选人会写代码，但真正拉开差距的是对 Unity 底层机制的理解。

我一般会按照下面几个模块来问。

---

# 第一部分：Unity 基础（考察底层理解）

这些问题基本每个人都会问。

### 生命周期

> MonoBehaviour 的生命周期有哪些？Awake、OnEnable、Start 的执行顺序是什么？

继续追问：

- Instantiate 一个 Prefab 后执行顺序？
- SetActive(true) 会调用哪些函数？
- Destroy(gameObject) 后 OnDisable 和 OnDestroy 谁先执行？
- Application Quit 时会发生什么？

---

### Update 家族

> Update、LateUpdate、FixedUpdate 分别什么时候执行？

继续问：

为什么角色移动一般放 Update？

为什么物理移动放 FixedUpdate？

为什么摄像机跟随一般放 LateUpdate？

Time.deltaTime 和 Time.fixedDeltaTime 区别？

---

### GameObject 与 Component

> GameObject 和 Component 的关系是什么？

继续追问：

为什么 Unity 要设计成 Component 模式？

Transform 为什么不能删除？

GetComponent 为什么慢？

有没有优化方法？

---

# 第二部分：UGUI（几乎必问）

我一般会重点问。

### Canvas

> Canvas 为什么建议拆分？

继续问：

为什么修改一个 Text 会导致整个 Canvas Rebuild？

Canvas Rebuild 过程了解吗？

GraphicRaycaster 做了什么？

---

### RectTransform

> Anchor 是什么？

继续问：

Anchor 和 Pivot 有什么区别？

为什么改 Anchor UI 就适配了？

Stretch 是怎么工作的？

---

### ScrollView

> ScrollView 为什么数据多会卡？

继续追问：

10000 条数据怎么办？

对象池怎么做？

虚拟列表原理是什么？

---

### EventSystem

> Button 点击为什么能收到事件？

继续问：

GraphicRaycaster 做了什么？

RaycastTarget 为什么会影响性能？

PointerEventData 了解吗？

---

# 第三部分：资源管理

这是面试重点。

### Resources

> Resources.Load 有什么问题？

继续问：

为什么官方不推荐？

什么时候可以用？

---

### AssetBundle

> AssetBundle 加载流程是什么？

继续追问：

依赖怎么办？

Manifest 是干什么的？

如何更新资源？

---

### Addressables

> Addressables 和 AssetBundle 什么关系？

继续问：

Addressables 为什么更方便？

引用计数了解吗？

Release 为什么重要？

---

# 第四部分：性能优化（重点）

我最喜欢问。

### GC

> Unity 为什么会 GC？

继续问：

哪些操作容易产生 GC？

例如：

```csharp
string +=
foreach
LINQ
new List()
GetComponent
Instantiate
Destroy
```

继续：

GC Alloc 怎么查？

Profiler 怎么看？

---

### Draw Call

> 什么是 Draw Call？

继续：

为什么 Draw Call 高？

Batch 为什么失败？

Dynamic Batch 和 Static Batch 区别？

GPU Instancing 呢？

---

### CPU

> 游戏 CPU 高怎么办？

继续：

Profiler 怎么分析？

Hierarchy 看什么？

Timeline 看什么？

Deep Profile 什么情况下开？

---

### 内存

> 怎么查内存泄漏？

继续：

Texture 为什么占内存？

Mesh 为什么占内存？

Native Memory 和 Managed Memory 区别？

---

# 第五部分：C#

如果是高级岗位，这部分很多。

### 引用类型和值类型

> struct 和 class 区别？

继续：

为什么 struct 放栈？

真的全部放栈吗？

装箱拆箱什么时候发生？

---

### 委托

> delegate、Action、Func 区别？

继续：

事件为什么用 event？

为什么 event 外部不能 Invoke？

Lambda 为什么会 GC？

---

### 泛型

> 泛型为什么快？

继续：

为什么不用 object？

泛型约束有哪些？

where T : class

where T : new()

为什么？

---

### async

> async await 在 Unity 怎么用？

继续：

Unity 主线程安全吗？

Task 能操作 Transform 吗？

协程和 async 区别？

---

# 第六部分：Lua（如果项目用了）

> tolua、xlua、slua 区别？

Lua GC 怎么做？

C# 和 Lua 怎么通信？

热更新原理？

---

# 第七部分：设计模式

这里不是让背八股。

### 单例

> 为什么很多人说不要滥用单例？

---

### MVC

> Unity 怎么做 MVC？

---

### MVP

> 为什么很多 UI 用 MVP？

---

### 状态机

> 写一个角色状态机。

Idle

↓

Run

↓

Jump

↓

Attack

↓

Dead

如何设计？

---

### 对象池

> 为什么对象池可以优化？

继续：

什么时候不用对象池？

---

### 观察者

> UnityEvent、delegate、event 有什么区别？

---

# 第八部分：项目经验（最重要）

这是决定 Offer 的部分。

我一般不会问：

> 你负责什么？

而会问：

---

> 你觉得你项目里最难的问题是什么？

---

> 当时为什么这样设计？

---

> 有没有更好的方案？

---

> 如果重构，你会怎么做？

---

> 做过哪些性能优化？

继续：

优化前 FPS？

优化后 FPS？

怎么测出来？

---

> 有没有踩过坑？

例如：

Canvas Rebuild

Shader Variant

Addressables

GC

Android 卡顿

iOS Crash

IL2CPP

AOT

等等。

---

# 第九部分：现场写代码

一般不会太难。

例如：

### 第一题

实现对象池。

---

### 第二题

实现事件中心。

---

### 第三题

写一个有限状态机。

---

### 第四题

实现 Timer。

要求：

支持暂停

支持恢复

支持循环

支持取消

---

### 第五题

实现一个 UIManager。

要求：

```text
Open()

Close()

Push()

Pop()

缓存窗口

异步加载
```

---

# 第十部分：开放题（真正拉开差距）

这是高级岗位最喜欢问的。

例如：

> 如果让你设计整个 UI 框架，你会怎么设计？

我会看：

- 模块划分
- 生命周期
- 窗口管理
- 资源管理
- 动画
- 多 Canvas
- 输入管理
- 适配
- 多语言

---

> 如果一个项目越来越卡，你从哪里开始排查？

我希望听到的是一种系统化思路，而不是直接说“打开 Profiler”。

例如：

1. 先确认 CPU、GPU 还是内存瓶颈。
2. 使用 Profiler 定位主线程耗时，观察 Update、Physics、Rendering 等模块。
3. 查看 GC Alloc 是否异常，分析 Managed Memory。
4. 检查 Draw Call、Batch、Overdraw 等渲染指标。
5. 结合 Frame Debugger、Memory Profiler 等工具进一步定位。
6. 根据问题类型制定优化方案，并验证优化效果。

---

## 如果是我面试一个 3～5 年 Unity 开发，我最关注这 5 点

1. **是否理解 Unity 的运行机制**：生命周期、渲染流程、物理、UI，而不仅仅会调用 API。
2. **是否有性能优化经验**：能够结合 Profiler、Frame Debugger、Memory Profiler 分析和解决实际问题。
3. **是否具备架构设计能力**：例如 UI 框架、资源管理、事件系统、状态机、对象池等是否设计合理、易维护。
4. **是否能结合真实项目说明技术决策**：为什么这样做、遇到了什么问题、如何权衡方案。
5. **是否有排查复杂问题的能力**：面对 Bug、卡顿、崩溃时，是否有清晰、可复现、可验证的定位思路。

**一句话概括：**初级工程师考的是“会不会用”，中级工程师考的是“为什么这样设计”，而资深工程师更关注“你如何做技术决策，以及如何在复杂项目中解决问题”。这也是面试中最容易体现能力差异的地方。

## 轮次 ddf55ece-3e9a-423c-abd8-0a1e9ebf6cb1

### 用户

如果让你面试一个十年工作经验的，你会问啥

### 助手

如果是**10 年 Unity 开发**，我基本不会问：

> 什么是 Update？
> 什么是协程？
> 什么是 AssetBundle？

因为这些问题已经没有区分度了。

对于 10 年经验，我会默认你已经是 **Tech Lead / Client Lead / 主程** 的水平。我想知道的是：

> **你有没有设计过一个大型项目？有没有踩过坑？有没有做过技术决策？**

我的问题会越来越偏向**架构、原理、经验和决策**。

---

# 第一部分：先聊项目（我一定会问）

第一个问题往往就是：

> **说一个你认为最有代表性的项目。**

但是这里不是介绍项目。

我会一直追问。

例如：

> 为什么当时这么设计？

> 为什么不用 XXX？

> 有没有第二种方案？

> 如果重新做，你还会这么设计吗？

我会一直挖。

例如他说：

> 我做了一个 MMO。

我会继续问：

> UI 怎么管理？

> 网络怎么同步？

> 热更新怎么做？

> 为什么用 XLua？

> 为什么不用 HybridCLR？

> 为什么 Addressables？

> 为什么不用 YooAsset？

直到发现他的知识边界。

---

# 第二部分：UI 架构

假设他说负责整个 UI。

我会直接问：

---

> **如果现在让你从零设计一个 UI Framework，你怎么设计？**

我希望听到：

```
UIManager

WindowBase

Layer

Canvas

Async Load

Animation

Mask

Back Stack

Popup

Cache

ObjectPool

Addressables
```

然后继续追问：

---

为什么要分 Layer？

为什么 Loading 不放 Popup？

为什么 WindowBase 要抽象？

为什么 Open 不同步？

为什么 Close 不 Destroy？

为什么缓存？

什么时候释放？

什么时候常驻？

如果热更新怎么办？

---

# 第三部分：资源管理

我一般会问：

---

假设：

游戏有

20GB

30万资源

每天更新

如何设计资源系统？

他如果回答：

Addressables。

我继续问：

Addressables 底层是什么？

Catalog 怎么更新？

Hash 怎么比较？

Remote Catalog 怎么下载？

依赖怎么下载？

什么时候 Release？

引用计数什么时候减？

如何避免重复下载？

如果 Catalog 损坏怎么办？

---

# 第四部分：性能

这个最喜欢问。

例如：

游戏上线。

安卓：

偶现：

```
FPS

60

↓

15

↓

恢复
```

Profiler 看不到。

怎么办？

这里我想听的是：

不是：

> 打开 Profiler。

而是：

```
日志

采样

线上监控

埋点

Crash

Memory

GPU

Thermal

GC

Native

ANR
```

有没有线上分析经验。

---

继续。

如果：

```
CPU 20%

GPU 20%

FPS 15
```

为什么？

有没有遇过？

---

再继续。

如果：

Profiler：

```
Rendering

2ms

Scripts

3ms

Physics

2ms

```

但是：

FPS

20

为什么？

有没有可能：

```
WaitForPresent

VSync

GPU

Driver

Thermal

```

---

# 第五部分：GC

不会问：

GC 是什么。

而是：

---

为什么：

```
foreach(List)

不会 GC

foreach(Dictionary)

有时候会

```

为什么？

---

为什么：

Lambda 会 GC？

什么时候不会？

---

UnityEvent 为什么慢？

为什么 Event 更快？

Delegate Combine 为什么 GC？

---

IL2CPP 下：

GC 行为有没有区别？

---

# 第六部分：Unity 底层

这个很多人挂。

例如：

---

Canvas Rebuild。

整个流程。

从：

```
Text.text=
```

开始。

一直说。

直到 GPU。

包括：

```
Graphic

Vertex

Batch

Mesh

CanvasRenderer

Render
```

---

或者：

Instantiate。

到底干了什么？

包括：

```
Native Object

Managed Object

Awake

OnEnable

Transform

Hierarchy

```

---

Destroy 为什么不是立即销毁？

---

# 第七部分：渲染

很多 Unity 老程序其实不会。

我会问。

---

为什么：

UI

Overdraw

严重？

怎么优化？

---

SRP Batcher。

为什么快？

---

Dynamic Batch。

为什么失败？

---

Static Batch。

为什么内存增加？

---

GPU Instancing。

什么时候不能合批？

---

为什么：

两个一样材质。

DrawCall 还是两个？

---

# 第八部分：网络

如果他说做过 MMO。

继续。

---

状态同步：

为什么不用 LockStep？

为什么 Snapshot？

为什么 Prediction？

为什么 Rollback？

---

断线重连。

怎么设计？

---

消息乱序怎么办？

---

TCP 粘包怎么办？

---

服务器 Tick。

客户端 Tick。

如何同步？

---

# 第九部分：工程架构

这里才是真正高级。

例如：

---

假设：

100万行代码。

100人团队。

怎么管理？

---

程序集怎么拆？

Assembly Definition。

怎么拆？

---

依赖怎么控制？

---

模块通信？

---

EventBus？

MessageCenter？

IOC？

DI？

为什么？

---

插件怎么管理？

---

第三方升级怎么办？

---

循环引用怎么办？

---

# 第十部分：团队

这是十年经验最重要。

例如：

---

新人：

写了一坨：

5000 行 MonoBehaviour。

怎么办？

---

Code Review。

怎么看？

---

如何制定编码规范？

---

如何推动重构？

---

为什么很多重构失败？

---

如何说服策划？

---

如何和 TA 合作？

---

如何和服务器合作？

---

# 第十一部分：开放题（最喜欢）

例如：

---

Unity 如果没有 MonoBehaviour。

你怎么设计？

---

为什么 ECS 能快？

不是 DOTS。

原理。

---

如果 Unity 今天重写。

你会删掉哪些 API？

---

如果让你设计：

Addressables。

你怎么设计？

---

如果让你设计：

GameObject。

你怎么设计？

---

# 最后一个问题（也是我最喜欢的）

我一般都会问：

> **过去十年，你做过的哪个技术决策，现在回头看觉得是错的？为什么？**

这个问题几乎没有标准答案，但非常能看出一个资深工程师的水平。

一个经验丰富的人通常不会回答“没有”。更常见的是会分享类似这样的反思：

- 当初把所有 UI 都放在一个 Canvas，后期因为频繁 Rebuild 导致性能问题。
- 过度使用单例，模块耦合严重，后来重构成本很高。
- 过早引入复杂框架，项目规模其实并不需要，增加了团队维护成本。
- 没有尽早建立自动化测试和 CI/CD，导致版本回归问题频发。
- 热更新方案选型只看功能，没有充分考虑团队维护能力和后续升级成本。

这些回答比“我会用 XX 框架”“我写过 XX 系统”更有价值，因为它体现的是**技术判断、复盘能力和工程思维**。

---

## 如果让我总结，10 年工程师和 3～5 年工程师最大的区别是什么？

我会用一句话来概括：

- **3～5 年**：关注的是“你能不能把功能做好、性能调优、代码写稳”。
- **10 年**：关注的是“你能不能带团队做正确的技术决策，并且让项目在 3 年后依然可维护”。

所以，我更少问 API 和记忆性的知识，而更关注**为什么这样设计、当时有哪些方案可选、为什么最终做出这个选择、如果今天重来会不会做得不同**。这些问题更能反映一位资深工程师的真实水平。

## 轮次 39f283c5-c214-49f4-ade4-2c51d206760c

### 用户

现在分类型一个个问，关于ugui，你会怎么问

### 助手

如果我是面试官，并且你面试的是**中高级 Unity（3~10 年）**，UGUI 我不会问"Button 有哪些事件"这种问题，而是会按照**由浅入深**的方式问，看看你的知识边界在哪里。

下面就是我真实会采用的一套面试流程。

---

# 第一轮：基础（5分钟）

这些问题主要确认你是不是"真正用过 UGUI"。

### Q1：UGUI 的整体架构是什么？

我希望你至少能说到：

- Canvas
- CanvasRenderer
- RectTransform
- Graphic
- GraphicRaycaster
- EventSystem
- Layout System

如果你还能说出：

> **Graphic 负责生成 Mesh，Canvas 负责收集和 Batch，CanvasRenderer 最终提交渲染。**

说明基础不错。

---

### Q2：Canvas 有哪几种模式？

继续追问：

- Overlay 为什么最快？
- Camera 模式什么时候用？
- World Space 的 EventSystem 是怎么工作的？

---

### Q3：RectTransform 和 Transform 有什么区别？

继续问：

- Anchor 是什么？
- Pivot 是什么？
- anchoredPosition 和 localPosition 有什么区别？
- Stretch 的计算规则是什么？

很多人其实答不完整。

---

# 第二轮：布局（10分钟）

这里开始看理解。

---

### Q4：Anchor 为什么能做屏幕适配？

我会一直追问。

例如：

父节点宽度：

1920

Anchor：

```text
Min(0)

Max(1)
```

Left

100

Right

100

最终宽度怎么算？

很多人不会。

---

### Q5：ContentSizeFitter 为什么容易出问题？

继续：

为什么官方建议少用？

为什么 LayoutGroup 嵌套会卡？

LayoutRebuilder 是什么时候工作的？

---

### Q6：HorizontalLayoutGroup 底层怎么排版？

如果有：

Preferred Width

Flexible Width

Min Width

它怎么算？

---

# 第三轮：事件系统（10分钟）

这是很多人不会。

---

### Q7：Button 点击到底发生了什么？

希望听到：

```text
Input

↓

EventSystem

↓

GraphicRaycaster

↓

RaycastResult

↓

ExecuteEvents

↓

IPointerClickHandler

↓

Button.onClick
```

而不是：

"Button 被点击了。"

---

### Q8：GraphicRaycaster 做了什么？

继续：

为什么 UI 可以挡住 3D？

RaycastTarget 为什么影响性能？

GraphicRegistry 是什么？

---

### Q9：EventSystem 每帧干了什么？

有没有 Update？

StandaloneInputModule 做了什么？

InputSystemUIInputModule 呢？

---

# 第四轮：渲染（15分钟）

这里开始拉开差距。

---

### Q10：Image 为什么能显示？

我希望他说：

Sprite

↓

Graphic

↓

OnPopulateMesh

↓

VertexHelper

↓

Mesh

↓

CanvasRenderer

↓

Canvas

↓

Batch

↓

Render

如果只说：

Image 显示 Sprite。

基本就是初级。

---

### Q11：UGUI 是怎么 Batch 的？

继续：

什么情况下不能 Batch？

例如：

不同材质

不同 Texture

Mask

Stencil

不同 Canvas

都会影响。

---

### Q12：为什么 Text 修改一下整个 Canvas Rebuild？

这是经典题。

希望回答：

Graphic SetVerticesDirty

↓

CanvasUpdateRegistry

↓

Layout

↓

Graphic

↓

Rebuild

↓

Batch

↓

Upload Mesh

而不是：

"因为 Unity 就这样。"

---

# 第五轮：Canvas（15分钟）

这是性能重点。

---

### Q13：为什么官方建议拆 Canvas？

继续：

什么时候拆？

什么时候不能拆？

拆太多有什么问题？

---

### Q14：Canvas Rebuild 分几个阶段？

有没有：

```text
PreLayout

Layout

PostLayout

PreRender

LatePreRender
```

知道的人很少。

---

### Q15：CanvasUpdateRegistry 是干什么的？

Dirty 怎么管理？

为什么不会立即刷新？

---

# 第六轮：性能（20分钟）

这是高级题。

---

### Q16：一个 ScrollView 有 10000 条数据怎么办？

我希望听到：

对象池

虚拟列表

可见区域计算

回收 Item

复用 RectTransform

如果他说：

Instantiate。

基本结束。

---

### Q17：为什么 UGUI 会卡？

希望他说：

Canvas Rebuild

Layout

Overdraw

Mask

GC

Raycast

Text

Atlas

Batch

---

### Q18：Mask 为什么慢？

继续：

Stencil Buffer 怎么工作的？

RectMask2D 为什么快？

---

### Q19：为什么 RaycastTarget 要关？

继续：

GraphicRaycaster 每帧会遍历什么？

为什么 Image 多了就慢？

---

# 第七轮：源码（高级）

如果你说：

看过源码。

那我开始问源码。

---

### Q20：Graphic 是什么时候注册到 Canvas 的？

GraphicRegistry。

什么时候 Register？

什么时候 Unregister？

---

### Q21：CanvasRenderer 是干什么的？

为什么不能直接 Render？

---

### Q22：VertexHelper 为什么存在？

为什么不用 Mesh？

---

### Q23：MaskableGraphic 做了什么？

为什么 Image 继承它？

---

### Q24：Selectable 为什么能导航？

Navigation 是怎么做的？

---

# 第八轮：架构

如果你说做过大型项目。

---

### Q25：你们 UI 怎么管理？

WindowBase？

UIManager？

Layer？

Stack？

Popup？

Modal？

Animation？

Async？

---

### Q26：一个 Window 生命周期怎么设计？

Create

Load

Show

Hide

Destroy

什么时候缓存？

什么时候释放？

---

### Q27：UI 怎么异步加载？

Addressables？

AssetBundle？

Resources？

什么时候实例化？

什么时候绑定数据？

---

### Q28：MVC 怎么拆？

View

Presenter

Model

谁监听谁？

---

# 第九轮：开放题（真正高级）

例如：

---

### Q29：

如果让你重写 UGUI。

你觉得哪些地方设计不好？

---

### Q30：

为什么现在越来越多人转 UI Toolkit？

UGUI 最大的问题是什么？

---

### Q31：

如果你负责一个大型 MMO。

UI 有：

```text
主界面

商城

邮件

排行榜

好友

聊天

战斗 HUD

副本

Loading

弹窗

Guide
```

你怎么设计整个 UI Framework？

---

# 最后一题（我最喜欢）

我会直接问：

> **如果现在打开 Unity Profiler，发现 UI 占了 12ms，你会怎么排查？**

我希望听到的是一套完整的分析流程，而不是一句"看看 Profiler"。

例如：

1. **确认瓶颈位置**：是 Layout、Canvas.BuildBatch、GraphicRaycaster、Text 更新，还是 GPU Overdraw。
2. **检查 Canvas 是否合理拆分**：动态 UI 是否影响了大量静态 UI 的重建。
3. **观察是否频繁触发 Dirty**：例如 Text、Image、RectTransform 是否持续变化。
4. **检查 Layout 系统**：是否存在 LayoutGroup + ContentSizeFitter 嵌套导致频繁重排。
5. **分析 ScrollView**：是否一次创建大量 Item，是否需要对象池和虚拟列表。
6. **查看 Raycast 开销**：关闭不需要交互元素的 Raycast Target，减少射线检测对象。
7. **评估渲染开销**：检查 Batch 是否被打断、是否存在严重 Overdraw、Mask 使用是否合理。
8. **优化后再次验证**：确认 CPU、GPU 和内存指标是否达到预期。

---

## 我对 UGUI 面试的评价标准

如果是 **3 年经验**，我希望你能解释清楚 **"怎么用，以及为什么这么用"**。

如果是 **5 年经验**，我希望你能说清楚 **UGUI 的运行机制、性能瓶颈和优化思路**。

如果是 **8～10 年经验**，我更希望听到你结合**源码理解、框架设计和真实项目经验**来回答，而不仅仅是背概念。比如，你是否知道 `Graphic`、`CanvasUpdateRegistry`、`GraphicRegistry`、`LayoutRebuilder` 等类在整个 UGUI 生命周期中的职责，以及你是否在项目中解决过复杂的 UI 性能问题。

如果你想按照**真正的大厂技术面**来练习，我们可以从 **Q1** 开始，我会像真实面试一样不断追问，直到你的知识边界。

## 轮次 4e298729-58e8-4282-bfa0-5ec47ec9de0a

### 用户

Yes

### 助手

好，那我们就按**真实技术一面**来。

规则如下：

- 我一次只问**一个问题**。
- 你回答后，我会根据你的回答**不断追问**，不会直接进入下一题。
- 如果你的回答不完整，我会提示你，但不会直接给答案。
- 我会按照**P6/P7（高级 Unity 工程师）**的标准来追问。

---

## 第一题：UGUI 的整体架构

> **请你介绍一下 UGUI 的整体架构。**
>
> 不要只说有哪些组件，而是说说：
>
> 1. UGUI 的核心组成有哪些？
> 2. 一个 `Image` 从创建到最终显示到屏幕上，大致经历了哪些流程？
> 3. `Canvas`、`Graphic`、`CanvasRenderer`、`EventSystem` 分别承担什么职责？
>
> 你可以把整个流程串起来讲，就像在给团队新人介绍 UGUI 的工作原理一样。

---

💡 **面试提示（不是答案）：**

很多候选人会停留在：

> Canvas、Button、Image、Text……

这样的回答只能拿到基础分。

我更希望听到的是类似：

> `Image` 继承自 `Graphic`，当需要刷新时会标记 Dirty，在 Canvas 更新阶段重建顶点数据，通过 `CanvasRenderer` 提交给渲染系统；交互则由 `EventSystem` 配合 `GraphicRaycaster` 完成射线检测……

---

**现在开始面试。**

请开始回答，不用担心是否完全正确，我会根据你的回答继续深入追问。

