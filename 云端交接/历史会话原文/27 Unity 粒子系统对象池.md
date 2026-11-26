# Unity 粒子系统对象池

会话 ID：`6a2a67e5-9de8-83ea-b415-d82c68bd4698`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 6fb38c1a-d7bc-4f66-9b3a-a440672d9bb0

### 用户

给我讲讲业内常见的特效对象池 + SubEmitter + Timeline 特效回收架构

### 助手

如果你看过大厂项目（腾讯、网易、米哈游、莉莉丝）的特效框架，会发现他们管理的不是单个 ParticleSystem，而是一个完整的 **Effect（特效实例）**。

架构大概长这样：

```text
Effect
│
├── ParticleSystem
├── ParticleSystem
├── ParticleSystem
│
├── TrailRenderer
├── TrailRenderer
│
├── Animator
│
├── AudioSource
│
├── MeshRenderer
│
└── Timeline
```

对象池回收的单位是：

```text
Effect
```

不是：

```text
ParticleSystem
```

---

# 第一层：EffectPool

例如：

```text
FireBallHit
ExplosionBig
ExplosionSmall
IceBoom
```

每种特效一个池：

```text
FireBallHitPool
ExplosionBigPool
IceBoomPool
```

使用：

```csharp
EffectHandle handle =
    EffectManager.Play(
        "ExplosionBig",
        pos,
        rot);
```

内部：

```text
Pool
 ↓
取出对象
 ↓
Reset
 ↓
Play
```

---

# 第二层：统一接口

所有特效都实现：

```csharp
public interface IEffect
{
    void Play();
    void Stop();
    void Recycle();
}
```

例如：

```csharp
public class EffectRoot : MonoBehaviour
{
    public ParticleSystem[] particles;
    public TrailRenderer[] trails;

    public void Recycle()
    {
        ResetParticles();
        ResetTrails();

        gameObject.SetActive(false);
    }
}
```

---

# 第三层：SubEmitter处理

这是新人最容易踩的坑。

例如爆炸：

```text
Explosion
 ├── Smoke
 ├── Fire
 └── Spark
         ↓
      SubEmitter
         ↓
      SmallSpark
```

如果：

```csharp
mainParticle.Stop();
```

经常出现：

```text
主粒子停了

子粒子还在飞
```

结果：

```text
对象回池

池里继续冒火花
```

---

所以大厂一般递归处理：

```csharp
ParticleSystem[]
allParticles;
```

初始化缓存：

```csharp
allParticles =
    GetComponentsInChildren<ParticleSystem>(true);
```

回收：

```csharp
foreach(var ps in allParticles)
{
    ps.Stop(
        true,
        ParticleSystemStopBehavior.StopEmittingAndClear
    );

    ps.Clear(true);
}
```

全部一起清。

---

# 第四层：TrailRenderer处理

第二个超级大坑。

例如：

```text
剑光
拖尾
子弹尾迹
```

回收后：

```text
重新取出来
```

出现：

```text
上一帧拖尾还在
```

像瞬移一样。

---

解决：

```csharp
trail.Clear();
```

回收时：

```csharp
foreach(var trail in trails)
{
    trail.Clear();
}
```

---

# 第五层：Timeline特效

现在越来越多项目：

```text
技能特效
CG
Boss演出
```

都是：

entity["software","Unity Timeline","Unity Sequencing System"]

控制。

例如：

```text
Timeline
├── Particle
├── Audio
├── Animation
├── CameraShake
└── Signal
```

---

问题来了：

Timeline播完怎么回池？

很多人写：

```csharp
yield return new WaitForSeconds(xx);
```

这是错的。

策划改Timeline长度：

```text
3秒
 ↓
5秒
```

代码全废。

---

正确做法：

监听：

```csharp
PlayableDirector.stopped
```

```csharp
director.stopped += OnTimelineEnd;
```

结束：

```csharp
void OnTimelineEnd(
    PlayableDirector director)
{
    Recycle();
}
```

---

# 第六层：自动回收系统

很多项目会做：

```csharp
AutoRecycle
```

播放时自动计算寿命。

例如：

```text
Particle A = 2s

Particle B = 1s

Particle C = 3s
```

最终：

```text
Lifetime = 3s
```

记录：

```csharp
float maxLife;
```

播放：

```csharp
recycleTime =
    Time.time + maxLife;
```

管理器检测：

```csharp
if(Time.time > recycleTime)
{
    pool.Release(effect);
}
```

---

# 第七层：句柄系统（米哈游常见）

不要这样：

```csharp
Instantiate
Destroy
```

而是：

```csharp
EffectHandle
```

```csharp
var handle =
    EffectManager.Play(
        "Explosion",
        pos);
```

返回：

```csharp
handle.Stop();

handle.Recycle();

handle.SetPosition(pos);
```

游戏逻辑永远不知道对象池存在。

---

# 一个完整的工业级结构

```text
EffectManager
│
├── EffectPool
│
├── EffectHandle
│
├── AutoRecycleSystem
│
└── TimelineSystem
        │
        ▼
    EffectRoot
        │
        ├── ParticleSystem[]
        ├── TrailRenderer[]
        ├── AudioSource[]
        ├── Animator[]
        ├── Timeline
        └── SubEmitter
```

这种架构可以支撑：

- 技能特效
- 子弹命中特效
- Boss大招
- Timeline演出
- UI特效
- 场景环境特效

同时做到：

- 零 Instantiate
- 零 Destroy
- 极低 GC
- 支持 SubEmitter
- 支持 Timeline
- 自动回收

这基本就是目前 Unity 商业项目里最主流的特效管理思路。

## 轮次 0ff00346-15ee-4091-be4e-9bd8eaab47de

### 用户

粒子特效如何预热

### 助手

粒子特效的**预热（Prewarm）**本质上是：

> 不让粒子从「第 0 帧」开始播放，而是让它看起来已经运行了一段时间。

例如：

```text
火焰
```

如果不预热：

```text
第0帧
  *
第1秒
 ***
第2秒
******
```

玩家会看到火焰慢慢长出来。

但现实中：

```text
火堆
```

应该是一出现就是：

```text
******
******
******
```

这时候就需要预热。

---

# Unity自带Prewarm

如果粒子：

```csharp
Looping = true
```

可以直接勾选：

```text
Main
 └─ Prewarm
```

Unity会自动：

```text
Simulate(Duration)
```

一次。

效果：

```text
生成出来
=
已经运行一个周期
```

适合：

- 火焰
- 烟雾
- 云层
- 飘雪
- 雨

---

# Prewarm的原理

例如：

```text
Duration = 5秒
```

Unity实际上会：

```csharp
particle.Simulate(
    5f,
    true,
    true,
    true);
```

然后暂停。

真正播放时：

```csharp
particle.Play();
```

此时已经是：

```text
第5秒状态
```

而不是：

```text
第0秒状态
```

---

# 代码预热

有时候你不想开：

```text
Prewarm
```

而是自己控制。

例如对象池初始化：

```csharp
void Awake()
{
    ps.Simulate(
        3f,
        true,
        true,
        true);

    ps.Stop(
        true,
        ParticleSystemStopBehavior.StopEmittingAndClear);
}
```

---

更常见：

```csharp
ps.Simulate(
    ps.main.duration,
    true,
    true,
    true);
```

相当于官方Prewarm。

---

# 大厂项目常用方案

对于对象池里的循环特效：

```text
CampFire
TorchFire
MagicCircle
```

初始化时：

```text
Pool Create
 ↓
Instantiate
 ↓
Prewarm
 ↓
进入池
```

这样第一次取出来：

```text
直接是满状态
```

不会看到成长过程。

---

# Timeline里的预热

例如Boss登场：

```text
烟雾
 ↓
持续存在
```

如果Timeline刚激活：

```text
烟雾从0开始冒
```

会很假。

常见做法：

```csharp
ps.Simulate(
    2f,
    true,
    true,
    true);

ps.Play();
```

让它像已经存在了2秒。

---

# SubEmitter预热

这里有个坑。

例如：

```text
Smoke
 └── Spark(SubEmitter)
```

你预热主粒子：

```csharp
Smoke.Simulate(5);
```

子发射器不一定同步到你想要的状态。

因此很多项目会：

```csharp
foreach(var ps in allParticles)
{
    ps.Simulate(
        prewarmTime,
        true,
        true,
        true);
}
```

递归预热整棵特效树。

---

# 对象池里的正确姿势

很多人这样：

```csharp
取出来
 ↓
Simulate(5)
 ↓
Play()
```

这是错的。

因为每次取出都会：

```text
CPU模拟5秒
```

很贵。

---

正确做法：

```text
创建对象
 ↓
Prewarm一次
 ↓
放入池
```

之后：

```text
取出
 ↓
Play
```

不再重复预热。

---

# VFX Graph的预热

如果以后用：

entity["software","Visual Effect Graph","Unity VFX System"]

里面有专门的：

```text
PreWarm Step Count
PreWarm Delta Time
```

例如：

```text
PreWarm Step Count = 100

PreWarm Delta Time = 0.03
```

表示：

```text
启动前模拟100帧
```

比 Shuriken 的 Prewarm 更灵活。

---

实际项目里最常见的经验是：

| 特效类型 | 是否预热 |
|----------|---------|
| 爆炸 | ❌ 不预热 |
| 受击火花 | ❌ 不预热 |
| 技能命中特效 | ❌ 不预热 |
| 火焰 | ✅ 预热 |
| 烟雾 | ✅ 预热 |
| 雨雪 | ✅ 预热 |
| 魔法阵 | ✅ 预热 |
| 环境粒子 | ✅ 预热 |

因为预热主要解决的是**持续存在的循环特效突然从零开始长出来的问题**，而爆炸、火花这类瞬时特效本来就是从零开始出现的，不需要预热。

## 轮次 675df1a8-db13-465e-8f16-ba1a3dd94c80

### 用户

预热是否对播放卡顿有影响

### 助手

预热确实会对播放的流畅性有影响，但主要取决于**何时执行预热**以及**粒子系统的复杂度**。

---

## 1. 如果在播放时预热

比如：

```csharp
particle.Simulate(5f, true, true, true);
particle.Play();
```

- 这时游戏帧会被占用做 5 秒的粒子模拟
- 对复杂特效（大量粒子、子发射器、多层碰撞、多材质）尤其明显
- 结果就是**取出特效那一帧可能出现卡顿**

---

## 2. 正确做法：提前预热

- **对象池初始化阶段**提前调用 `Simulate()`，并不在渲染帧中
- 预热完成后放入池中
- 播放时直接 `Play()`，不会再做模拟计算

这样可以：

- 避免玩家第一帧看到“粒子慢慢长出来”
- 避免第一帧的卡顿

---

## 3. 对复杂特效的额外注意

- **子发射器（SubEmitter）**  
  预热时需要递归调用所有子粒子系统，否则子粒子可能不一致，导致视觉跳动。
  
- **TrailRenderer 或 Ribbon 特效**  
  预热时要调用 `Clear()` 清除拖尾，否则可能出现错误的残影。

- **Timeline + 粒子**  
  Timeline 内的粒子特效如果在播放帧做预热，也会卡顿。建议对象池阶段完成预热。

---

## 4. 总结建议

| 场景 | 是否卡顿 | 优化方法 |
|------|----------|----------|
| 播放帧实时预热 | 高 | 不要在播放帧做，提前预热 |
| 对象池初始化预热 | 低 | 只模拟一次，放入池中 |
| 大型子粒子特效 | 中 | 递归预热所有子粒子，控制粒子总数 |
| Timeline 特效 | 中 | 在非渲染帧预热，Timeline 开始直接播放 |

✅ **核心原则**：  
**预热操作应尽量在非渲染帧（对象池初始化）完成，而不是在玩家看到的那一帧执行**，这样既能保持预热效果，又不会引起卡顿。  

如果你需要，我可以:chatgpt-content-reference{index="0"}，让整个流程更直观。  

你想让我画吗？

## 轮次 51c18f0d-105a-47dd-935f-e4377d27c07d

### 用户

预热和Simulate 接口有什么区别

### 助手

很多人以为 **Prewarm = Simulate(duration)**，其实它们相关，但不是同一个东西。

可以这么理解：

```text
Prewarm 是功能
Simulate 是接口
```

---

## Prewarm是什么

Inspector里面：

```text
Main
 ├─ Looping
 └─ Prewarm
```

勾选后：

```text
特效启动前
先模拟一个Duration
```

例如：

```text
Duration = 5秒
```

Unity内部大概相当于：

```csharp
particle.Simulate(
    5f,
    true,
    true,
    true
);
```

然后把结果保存下来。

所以：

```text
Prewarm
=
自动执行一次Simulate
```

---

## Simulate是什么

Simulate是开发者主动调用的API：

```csharp
particle.Simulate(
    time,
    withChildren,
    restart,
    fixedTimeStep
);
```

你可以模拟任意时间：

```csharp
particle.Simulate(1);
particle.Simulate(3);
particle.Simulate(10);
particle.Simulate(100);
```

而Prewarm只能：

```text
模拟一个Duration
```

不能指定：

```text
2.3秒
7.8秒
15秒
```

---

## 最重要的区别

### Prewarm

只执行一次。

```text
创建
 ↓
预热
 ↓
播放
```

之后正常运行。

---

### Simulate

随时都能调用。

例如：

```csharp
ps.Simulate(10);
```

立即跳到：

```text
第10秒状态
```

就像视频拖进度条。

---

## 一个形象例子

假设火焰：

```text
Duration = 5秒
```

### 不开Prewarm

生成：

```text
第0秒

*
```

1秒：

```text
***
```

5秒：

```text
******
```

---

### 开Prewarm

生成：

```text
******
```

直接满状态。

---

### Simulate(2)

生成：

```text
****
```

相当于火已经烧了2秒。

---

### Simulate(10)

生成：

```text
******
```

相当于已经烧了10秒。

---

## 性能区别

### Prewarm

通常：

```text
Awake
Instantiate
Scene Load
```

执行一次。

代价：

```text
一次性CPU开销
```

---

### Simulate

每调用一次：

```text
重新计算粒子状态
```

例如：

```csharp
Update()
{
    ps.Simulate(5);
}
```

这是灾难。

因为：

```text
每帧重新模拟5秒
```

CPU直接爆炸。

---

## 对象池里的区别

很多人写：

```csharp
Get()
{
    ps.Simulate(5);
    ps.Play();
}
```

这是错的。

因为：

```text
每次取出
都重新预热
```

---

正确：

```csharp
Create()
{
    ps.Simulate(5);
}
```

只在创建池对象时执行。

之后：

```csharp
Get()
{
    ps.Play();
}
```

---

## 实际开发经验

对于对象池里的循环特效：

```text
火焰
烟雾
魔法阵
瀑布
```

一般：

```text
池创建
 ↓
Simulate(duration)
 ↓
入池
```

等价于自己实现Prewarm。

对于：

```text
爆炸
火花
受击
```

通常：

```text
不Prewarm
不Simulate
```

因为这些特效本来就是从0开始播放的。

---

所以可以记一个简单结论：

```text
Prewarm
=
Unity自动帮你调用一次
Simulate(Duration)

Simulate
=
开发者手动控制粒子时间轴的接口
```

在工业项目里，真正常用的是 `Simulate()`，因为对象池、Timeline、特效编辑器都需要精确控制粒子状态，而不仅仅是简单的 Prewarm。

## 轮次 8c8bd991-a2f6-4437-a3ee-88a2c712553a

### 用户

游戏运行时CPU占用高，你会怎么排查

### 助手

如果这是面试题，尤其是 **Unity 客户端开发**岗位，我一般不会直接说"打开 Profiler 看一下"，而是按照**"先定位，再分析，再优化"**的思路回答。这样面试官会觉得你有工程经验。

---

# 第一步：确认CPU瓶颈

首先确认：

```text
CPU高？
还是GPU高？
还是CPU在等待GPU？
```

很多人第一步就开始优化代码，这是错误的。

Unity Profiler 先看：

```
CPU Usage
GPU Usage
Timeline
```

如果：

```
CPU 25ms
GPU 8ms
```

说明：

CPU瓶颈。

如果：

```
CPU 8ms
GPU 25ms
```

不要优化CPU。

---

# 第二步：看Main Thread

Unity大部分逻辑都跑在：

```
Main Thread
```

先展开：

```
PlayerLoop
```

看看：

```
PlayerLoop
    Update
    LateUpdate
    Rendering
    Physics
    Animation
```

到底是谁最耗时。

例如：

```
Scripts.Update()

占了12ms
```

那就是脚本问题。

如果：

```
Physics.Simulate()

10ms
```

说明物理。

如果：

```
RenderLoop

15ms
```

说明渲染准备阶段。

---

# 第三步：定位具体函数

Profiler继续展开：

例如：

```
Update()

EnemyManager.Update()

Enemy.Update()

AI.Update()

PathFinding()

```

直到找到：

```
FindTarget()

8ms
```

这样才能开始优化。

---

# 第四步：常见CPU热点

这是Unity项目最容易出现的问题。

---

## ① 大量Update()

例如：

```
1000个NPC

每个都有：

Update()
```

Profiler：

```
BehaviourUpdate

15ms
```

优化：

改成：

```
Manager统一Update

或者

定时刷新

或者

Job System
```

---

## ② GC

Profiler：

```
GC.Alloc

3MB/frame
```

说明：

不停分配内存。

典型：

```
new List()

new String()

LINQ

foreach(Boxing)

```

优化：

对象池

缓存List

StringBuilder

避免装箱

---

## ③ Instantiate / Destroy

Profiler：

```
Instantiate

Destroy
```

很多。

优化：

对象池。

例如：

```
子弹

特效

UI

```

全部对象池。

---

## ④ Physics

Profiler：

```
Physics.Simulate

10ms
```

原因：

```
碰撞体太多

RigidBody太多

Continuous

```

优化：

Layer

Collision Matrix

降低FixedUpdate

减少Raycast

---

## ⑤ Animator

Profiler：

```
Animator.Update

7ms
```

原因：

```
Animator太多

Layer太多

IK

```

优化：

LOD

距离停止Animator

减少Layer

---

## ⑥ UI

Profiler：

```
Canvas.BuildBatch

Canvas.SendWillRenderCanvases
```

说明：

Canvas一直重建。

优化：

拆Canvas。

例如：

```
Static Canvas

Dynamic Canvas

```

---

## ⑦ 粒子

Profiler：

```
ParticleSystem.Update()

```

原因：

```
粒子太多

SubEmitter

Collision

Noise

```

优化：

减少粒子数

关闭Collision

对象池

---

## ⑧ Animation

Profiler：

```
Animation.Update

```

大量骨骼。

优化：

LOD

GPU Skinning

停止远处动画。

---

# 第五步：深度分析

如果：

Profiler看不出来。

我会：

打开：

```
Deep Profile
```

或者：

```
Profile Analyzer
```

比较：

```
优化前

优化后
```

哪些函数下降。

> **注意**：`Deep Profile` 开销很大，会显著拖慢游戏，因此只建议用于开发环境定位问题，不建议长期开启或在真机性能测试时使用。

---

# 第六步：平台分析

PC：

```
CPU Usage

Memory

Timeline
```

Android：

```
Android GPU Inspector

Perfetto

```

iOS：

```
Xcode Instruments
```

看：

```
CPU

Thread

Energy

Memory
```

---

# 我自己的排查顺序

真正项目里，我一般按下面顺序：

```
CPU高
     │
     ▼
CPU Usage
     │
     ▼
Timeline
     │
     ▼
Main Thread
     │
     ▼
PlayerLoop
     │
     ▼
Update?
Physics?
Rendering?
Animation?
     │
     ▼
找到具体函数
     │
     ▼
看GC
     │
     ▼
看对象池
     │
     ▼
优化
     │
     ▼
再次Profiler验证
```

---

# 如果这是高级开发岗位（3~5年以上经验）

面试官更希望听到的是一种**系统化的排查方法**，而不是零散的优化技巧。一个比较完整的回答可以概括为：

1. **先判断瓶颈是在 CPU、GPU 还是同步等待**，避免优化错方向。
2. **用 Profiler 的 Timeline 定位耗时线程和 PlayerLoop 阶段**，逐层展开到具体函数。
3. **分析热点类型**：脚本（Update）、GC、物理、动画、UI、粒子、资源加载等。
4. **针对性优化**：例如对象池减少 Instantiate/Destroy、缓存减少 GC、批量更新代替大量 Update、优化 Canvas 重建、降低物理和动画开销等。
5. **优化后重新 Profile 验证**，确保耗时确实下降，没有引入新的性能问题。

这样的回答既体现了排查思路，也体现了工程实践，比单纯罗列优化技巧更符合实际开发流程。

