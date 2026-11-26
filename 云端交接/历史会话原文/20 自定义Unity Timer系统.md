# 自定义Unity Timer系统

会话 ID：`6a322a18-69f8-83ea-99a5-e28cb82c903f`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 c3227596-627a-428c-84b5-efdeeb9e0ac4

### 用户

unity 项目中如何自定义一个timer 系统，需要不被gc 影响

### 助手

如果你的目标是**高性能、低GC、可控、不卡顿**，那业内（Unity大型项目）一般不会直接用 `Invoke`、`Coroutine` 或 `System.Timers.Timer`，而是自己写一个 **TimerManager**。

不过，先说一个容易误解的地方：

> **没有任何 Timer 能"不受 GC 影响"。**

因为 Unity 的所有脚本都是运行在主线程上的。

GC Stop-The-World 的时候：

```
GC开始
|
|-----------------------50ms------------------------|
               Timer 不会执行
               Update 不会执行
               Coroutine 不会执行
               Animator 不会执行
```

所以真正能做到的是：

> **GC结束以后 Timer 能立刻追赶（Catch Up），而不是越来越慢。**

---

# 一个好的 Timer 系统应该满足什么

例如：

```
Timer.Create(
    delay:2,
    callback:OnFinish
);

Timer.CreateLoop(
    interval:0.2f,
    callback:OnTick
);

Timer.Cancel(id);
```

要求：

- 不产生GC
- O(1) 删除
- O(n) 更新
- 支持暂停
- 支持恢复
- 支持缩放时间(TimeScale)
- 支持UnscaledTime
- GC结束后自动补帧

---

# Timer 数据结构

业内一般不会 new 一个对象。

而是

```csharp
struct Timer
{
    public int id;

    public float interval;

    public float remain;

    public bool loop;

    public Action callback;

    public bool active;
}
```

全部存在

```csharp
Timer[] timers;
```

或者

```
List<Timer>
```

里面。

避免：

```
new Timer()
```

避免：

```
LinkedList
Dictionary
```

因为容易产生GC。

---

# Update 更新

每帧

```csharp
float delta = Time.deltaTime;

for(int i=0;i<count;i++)
{
    if(!timers[i].active)
        continue;

    timers[i].remain -= delta;

    if(timers[i].remain<=0)
    {
        timers[i].callback();

        if(timers[i].loop)
            timers[i].remain += timers[i].interval;
        else
            timers[i].active = false;
    }
}
```

这是最简单版本。

---

# 为什么它不会怕GC？

假设：

```
interval = 0.1
```

正常：

```
0.1
0.2
0.3
0.4
```

突然GC

```
0.4

==========
GC 500ms
==========

0.9
```

这时候

```
deltaTime = 0.5
```

于是：

```
remain -=0.5
```

立即触发。

Timer 不会越来越慢。

---

# 更好的写法（补帧）

很多项目会这样：

```csharp
remain -= delta;

while(remain<=0)
{
    callback();

    if(loop)
        remain += interval;
    else
        break;
}
```

例如：

```
interval=100ms

GC=350ms
```

回来以后：

```
Tick1

Tick2

Tick3

Tick4
```

一次补回来。

很多 MMO 都这么干。

---

# 也可以限制补帧次数

否则：

```
GC 5 秒
```

回来以后：

```
50 次 callback
```

CPU 爆炸。

所以：

```csharp
int count=0;

while(remain<=0 && count<5)
{
    callback();

    remain+=interval;

    count++;
}
```

最多补：

```
5 次
```

剩下继续下一帧。

---

# 不要使用 Time.time

很多人写：

```csharp
if(Time.time>endTime)
```

其实业内更推荐：

```
remain -= delta
```

原因：

不用反复读取

```
Time.time
```

而且支持：

```
scaled
unscaled
custom delta
```

更方便。

---

# 如何做到零GC

最大的GC来源其实不是 Timer，而是：

## ① Lambda

例如：

```csharp
Timer.Start(()=>{
    xxx
});
```

每次：

```
new Delegate
```

GC。

---

应该：

```csharp
Timer.Start(OnFinish);
```

或者

```csharp
static readonly Action callback = OnFinish;
```

---

## ② foreach

避免：

```csharp
foreach(var timer in timers)
```

用：

```csharp
for(int i=0;i<count;i++)
```

---

## ③ RemoveAt

不要：

```csharp
list.RemoveAt(i);
```

可以采用**交换删除（Swap Back）**：

```csharp
list[i] = list[last];
list.RemoveAt(last);
```

O(1)。

---

## ④ Timer 对象

不要：

```csharp
new TimerNode()
```

直接：

```
Timer[]
```

或者对象池。

---

# 如果有几十万个 Timer 怎么办？

Update 每帧遍历：

```
100000
```

还是很慢。

业内一般使用：

## 小根堆（最小堆）

按照：

```
expireTime
```

排序。

例如：

```
Heap

0.2

0.5

1.0

2.0

5.0
```

Update：

```
只检查顶部
```

```
while(heap.top<=now)
{
    pop();

    callback();
}
```

复杂度：

```
O(logN)
```

很多服务器和大型客户端都这么实现。

---

# Unity 大型项目常见 Timer 架构

对于一般游戏（几百到几千个 Timer），推荐：

```
Game
│
├── TimerManager
│     │
│     ├── Timer[]
│     ├── FreeList
│     ├── Update()
│     ├── Add()
│     ├── Cancel()
│     └── Pause()
│
└── MonoBehaviour(Update)
        │
        └── TimerManager.Update(Time.deltaTime)
```

这种架构具有以下特点：

- **几乎零GC**（运行过程中不分配对象，避免闭包和临时集合）。
- **受 GC 暂停影响，但能自动追赶时间**，不会因为一次 GC 而永久延后定时器。
- **支持高性能管理大量 Timer**；如果定时器数量非常多（上万级），可将线性遍历升级为**最小堆**或**时间轮（Timing Wheel）**，进一步降低每帧开销。

对于绝大多数 Unity 客户端项目，**数组/列表 + FreeList + `remain -= deltaTime` + `while(remain <= 0)` 补帧机制**已经是成熟且性能很高的方案；只有在 MMO、大规模模拟等场景，才会进一步采用最小堆或时间轮等更复杂的数据结构。

## 轮次 6984b03f-4096-4e9a-b18e-9e585286608c

### 用户

详细说下基于最小堆的 实现

### 助手

如果你的 Timer 数量达到 **几万甚至几十万个**，那每帧遍历所有 Timer（O(n)）就开始浪费 CPU 了。

这时候业内最常用的方案就是 **最小堆（Min Heap）**。

> Unity、很多游戏服务器、Node.js 的 libuv、Go runtime 等，都使用了类似思想管理定时器。

---

# 先理解为什么 List 不够好

假设有 100000 个 Timer。

```
10ms
20ms
35ms
60ms
...
500000ms
```

普通做法：

```csharp
for(...)
{
    if(timer.expire <= now)
        callback();
}
```

每帧：

```
扫描100000个
```

实际上：

真正到时间的可能只有

```
2个
```

结果：

```
99898 次判断都是白做
```

CPU 全浪费了。

---

# 最小堆是什么

最小堆是一棵完全二叉树。

例如：

```
           10
        /      \
      20        35
     /  \      /  \
   40   50   60   70
```

特点：

> **父节点一定比子节点小。**

但是：

左右孩子不用排序。

例如：

```
      10
     /  \
   20   15
```

也是合法的。

因为

```
10 <20
10 <15
```

即可。

---

## 为什么叫最小堆

因为：

根节点永远最小。

```
heap[0]
```

就是

> 最快到期的 Timer。

因此：

Update 根本不用扫描。

直接看：

```
heap[0]
```

即可。

---

# Unity Timer 数据

每个 Timer 保存：

```csharp
struct Timer
{
    public int id;

    public float expireTime;

    public float interval;

    public bool loop;

    public Action callback;
}
```

注意：

这里不用

```
remain
```

而是直接记录：

```
expireTime
```

例如：

当前

```
Time = 100
```

创建

```
delay=5
```

得到

```
expire=105
```

以后永远比较：

```
expire <= now
```

即可。

---

# Heap 用数组实现

实际上不是树。

就是数组。

例如：

```
Index

0

1

2

3

4

5

6
```

存：

```
      5
    /   \
   8    10
  / \   /
20 30 15
```

数组就是：

```
[5,
 8,
10,
20,
30,
15]
```

不用指针。

不用 Node。

GC 为零。

---

# 下标关系

假设：

```
i
```

左孩子：

```
2*i+1
```

右孩子：

```
2*i+2
```

父节点：

```
(i-1)/2
```

例如：

```
index=2
```

父：

```
0
```

因为：

```
(2-1)/2=0
```

---

# 插入 Timer

新增：

```
expire=25
```

先放最后。

```
5
8
10
20
30
15
25
```

然后开始：

**上浮（Sift Up）**

比较父节点：

```
25
```

父：

```
10
```

已经大。

停止。

---

再插：

```
expire=3
```

先放最后：

```
5
8
10
20
30
15
25
3
```

然后：

和父：

```
20
```

交换：

```
5
8
10
3
30
15
25
20
```

继续：

父：

```
8
```

交换：

```
5
3
10
8
30
15
25
20
```

继续：

父：

```
5
```

交换：

```
3
5
10
8
30
15
25
20
```

结束。

这叫：

```
Sift Up
```

复杂度：

```
O(logN)
```

---

# 删除最早 Timer

例如：

```
3
5
10
8
30
15
25
20
```

根：

```
3
```

已经触发。

怎么办？

最后一个：

```
20
```

放到根：

```
20
5
10
8
30
15
25
```

然后：

开始

**下沉（Sift Down）**

比较：

```
20

孩子：

5

10
```

最小：

```
5
```

交换：

```
5
20
10
8
30
15
25
```

继续：

```
20

孩子

8

30
```

交换：

```
5
8
10
20
30
15
25
```

结束。

---

# Update 怎么写

这是整个 TimerManager 最核心的代码：

```csharp
float now = Time.time;

while(heap.Count > 0)
{
    Timer timer = heap.Peek();

    if(timer.expireTime > now)
        break;

    heap.Pop();

    timer.callback?.Invoke();

    if(timer.loop)
    {
        timer.expireTime += timer.interval;

        heap.Push(timer);
    }
}
```

整个 Update：

没有

```
for
```

没有扫描。

只处理：

已经到期的 Timer。

---

# GC 卡顿怎么办？

例如：

Timer：

```
100ms
```

GC：

```
500ms
```

回来：

```
now=10.5
```

Timer：

```
expire=10.1
```

进入：

```
while(expire<=now)
```

执行：

```
callback()
```

然后：

```
expire+=0.1
```

变：

```
10.2
```

继续：

```
10.2<=10.5
```

再执行。

于是：

```
10.1

10.2

10.3

10.4

10.5
```

一次全部补回来。

这就是：

**Catch Up**。

---

# 删除任意 Timer 怎么办？

最小堆最大的缺点就在这里。

例如：

```
取消 Timer 10086
```

它可能在：

```
heap[5634]
```

不知道在哪。

如果遍历：

```
O(N)
```

太慢。

---

业内一般做法：

## 方法一：Dictionary

维护：

```csharp
Dictionary<int,int>
```

保存：

```
TimerID

↓

HeapIndex
```

例如：

```
1001

↓

5
```

删除：

直接找到：

```
heap[5]
```

然后：

和最后一个交换。

再：

```
SiftUp

或者

SiftDown
```

即可。

复杂度：

```
O(logN)
```

注意：`Dictionary` 本身不会在正常读写时产生 GC，真正需要注意的是扩容，因此初始化时应预留容量。

---

## 方法二：Lazy Delete（很多服务器喜欢）

Timer：

```
active=true
```

取消：

```csharp
timer.active=false;
```

不用删除。

Update：

```csharp
Timer t=heap.Pop();

if(!t.active)
    continue;
```

直接跳过。

这样：

不用维护 Index。

实现简单。

---

# 最小堆的优缺点

| 优点 | 缺点 |
|------|------|
| 插入 O(logN) | 删除指定 Timer 需要额外索引或懒删除 |
| 获取最近 Timer O(1) | 实现比 List 稍复杂 |
| 到期处理高效 | 不适合频繁随机删除 |
| 大量 Timer 性能优秀 | 不按创建顺序执行 |

对于 **几千到几万个 Timer**，最小堆通常是非常合适的选择。

但如果你的项目存在**几十万甚至上百万个短周期 Timer**（例如服务器模拟、弹幕系统、大规模 AI），很多引擎和服务器会进一步采用 **时间轮（Timing Wheel）**。它可以把插入和删除的平均复杂度降到 **O(1)**，性能比最小堆还高，只是实现复杂度也更高。

**如果是在 Unity 客户端开发**，我通常建议：
- **< 1000 个 Timer**：数组/List 顺序扫描，简单且足够快。
- **1000～50000 个 Timer**：最小堆是综合性能和实现复杂度最好的方案。
- **> 50000 且大量短周期 Timer**：可以考虑时间轮或分层时间轮。

## 轮次 eee99f3b-74cf-4e64-9761-1c02f2906f49

### 用户

System.Threading.Timer

### 助手

`System.Threading.Timer` 是 .NET 提供的定时器，它和 Unity 自己的 Update/Coroutine 完全不是一个东西。

很多人看到它会觉得：

> **"既然它在后台线程执行，那是不是比 Update Timer 更好？"**

实际上，在 **Unity 项目中，大多数情况下不建议用它来做游戏逻辑 Timer。**

下面详细解释。

---

# 它的工作原理

创建：

```csharp
using System.Threading;

Timer timer = new Timer(
    callback: OnTimer,
    state: null,
    dueTime: 1000,
    period: 500
);
```

表示：

```
1 秒后执行

以后每 500ms 执行一次
```

注意：

**OnTimer 不是在 Unity 主线程执行。**

而是在：

```
ThreadPool Thread
```

也就是：

```
Main Thread

Update()

Render()

Physics()

-------------

ThreadPool

Timer Callback()
```

两个线程。

---

# 回调在哪里执行？

例如：

```csharp
void OnTimer(object state)
{
    Debug.Log(Thread.CurrentThread.ManagedThreadId);
}
```

打印出来通常不是：

```
1
```

而是：

```
7

11

15
```

说明：

它来自线程池。

---

# 最大的问题

Unity API **绝大多数都不是线程安全的。**

例如：

```csharp
transform.position = Vector3.zero;
```

Timer 回调：

```csharp
void OnTimer(object state)
{
    transform.position = Vector3.zero;
}
```

可能直接报错：

```
UnityException:

get_transform can only be called from main thread
```

或者：

```
Not allowed to access Unity objects
```

所以：

不能：

- Transform
- GameObject
- Animator
- Rigidbody
- AudioSource
- ParticleSystem
- UI

全部不能碰。

---

# 那它能干什么？

可以做：

## 网络

例如：

```
每10秒发送一次心跳
```

```csharp
socket.Send(...)
```

如果你的 Socket 本身支持多线程。

---

## 数据处理

例如：

```
每秒统计一次：

FPS

CPU

日志
```

这些纯 C# 数据。

---

## 超时检测

例如：

```
10 秒没收到服务器响应

关闭连接
```

可以。

---

## 缓存清理

例如：

```
Dictionary

Queue

缓存
```

这些都可以。

---

# 为什么游戏里很少用？

因为：

最终：

还是要：

```
GameObject

UI

角色

动画
```

都要切回：

```
Main Thread
```

例如：

```csharp
void OnTimer(object state)
{
    MainThreadDispatcher.Enqueue(() =>
    {
        ui.text = "OK";
    });
}
```

于是：

```
Thread Timer

↓

Queue

↓

Update()

↓

真正执行
```

那：

不如直接：

```
Update Timer
```

更简单。

---

# GC 怎么样？

`System.Threading.Timer` 本身不是零 GC。

例如：

```csharp
new Timer(...)
```

会：

```
分配 Timer 对象
```

回调：

```
Delegate

state

等等
```

都会有分配。

另外：

```
Dispose()
```

也有一定成本。

---

# 精度怎么样？

例如：

```
500ms
```

并不是：

```
500.0000ms
```

因为：

线程池调度：

```
CPU繁忙

↓

Timer 到时间

↓

线程池没线程

↓

等待

↓

520ms 才执行
```

因此：

它不是实时 Timer。

---

# GC 卡顿会怎样？

很多人觉得：

> "它在后台线程，GC 就不会影响了。"

其实不一定。

.NET 的垃圾回收通常会影响所有托管线程（具体取决于 GC 模式和运行时实现）。

例如：

```
Main Thread

GC

ThreadPool

GC

Timer

暂停
```

Timer 也会暂停。

因此：

它也不能保证：

```
100ms

200ms

300ms
```

绝对准时。

---

# 和 Unity Timer 对比

| 特性 | Update Timer | System.Threading.Timer |
|------|--------------|-------------------------|
| 执行线程 | 主线程 | 线程池 |
| 能操作 Unity API | ✅ | ❌ |
| 精度 | 跟随帧率 | 受线程调度影响 |
| GC 影响 | 会 | 会 |
| 适合游戏逻辑 | ✅ | ❌ |
| 适合后台任务 | ❌ | ✅ |

---

# 实际项目中的使用建议

通常会这样分工：

```
                Main Thread
                      │
        ┌─────────────┼─────────────┐
        │             │             │
     Update       Coroutine     TimerManager(最小堆)
        │             │             │
        └─────────────┴─────────────┘
                 游戏逻辑
```

而：

```
ThreadPool

│

├── Socket 心跳

├── HTTP Timeout

├── 日志刷新

├── 数据统计

└── 文件写入
```

使用：

```
System.Threading.Timer
```

因此，**如果你的目标是实现 Unity 项目中的游戏逻辑 Timer（技能 CD、Buff、UI 倒计时、资源超时、AI 行为等）**，最佳实践仍然是在**主线程**实现一个 `TimerManager`（例如基于最小堆），而不是使用 `System.Threading.Timer`。这样可以直接与 Unity 生命周期和 API 配合，性能也更容易控制。

