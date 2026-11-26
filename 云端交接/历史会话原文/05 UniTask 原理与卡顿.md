# UniTask 原理与卡顿

会话 ID：`6afab7be-b40c-83ec-a991-6734042d3670`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 8e0e8349-1cc9-49c7-a564-12be3f8cf80b

### 用户

**UniTask 的原理是什么？ 如果主线程 卡顿， unitask 是不是也会卡顿？**

### 助手

**会。UniTask 如果运行在 Unity 主线程上，那么主线程发生卡顿时，UniTask 同样会卡顿。**

但要理解这个问题，首先需要区分三个概念：

1. **异步（Async）**：允许一段逻辑暂停，等条件满足后继续执行。
2. **多线程（Multithreading）**：允许代码在不同线程上执行。
3. **非阻塞（Non-blocking）**：等待某个操作时，不占用当前线程持续执行。

UniTask 主要解决的是 Unity 中的异步编程问题，**并不意味着使用 UniTask 就会自动创建线程，也不意味着代码不会阻塞主线程。**

## 一、UniTask 的核心原理

UniTask 是基于 C\# `async/await` 机制实现的轻量级异步任务框架，针对 Unity 的运行环境进行了优化。

它主要依赖三个机制：

- C\# 编译器生成的异步状态机。
- UniTask 自己的任务和等待器机制。
- Unity PlayerLoop 驱动的任务调度机制。

### 1\. async/await 本质是状态机

例如：

```csharp
public async UniTask TestAsync()
{
    Debug.Log("A");

    await UniTask.Delay(1000);

    Debug.Log("B");
}
```

编译器会把这个方法转换成一个状态机。

逻辑大致相当于：

```csharp
enum State
{
    Start,
    Waiting,
    Finished
}
```

执行过程：

简化的 UniTask 状态机执行流程

注意：执行到 `await` 时，并不是整个线程暂停。

如果等待的任务尚未完成，状态机会保存当前执行位置，将控制权交还给调用方。后续等待条件满足，再恢复执行。

而如果等待的任务已经完成，`await` 可能直接同步继续执行，不会发生挂起。

### 2\. UniTask 如何利用 PlayerLoop

Unity 的主线程每帧都会执行 PlayerLoop，其中包含：

- Update
- FixedUpdate
- LateUpdate 所在的相关阶段
- 渲染及其他引擎阶段

UniTask 可以将需要轮询或恢复的任务注册到指定的 PlayerLoop 时机。

例如：

```csharp
await UniTask.Yield(PlayerLoopTiming.Update);
```

表示将后续执行安排到对应的 PlayerLoop 调度阶段。

注意，`UniTask.Yield` 和 `UniTask.Delay` 并不是完全相同的调度机制，`Delay` 还需要检查时间条件。

所以 UniTask 的很多异步操作，本质上是：

**把等待和恢复逻辑交给 Unity 每帧执行的调度系统，而不是创建一个线程等待。**

---

## 二、为什么主线程卡顿会影响 UniTask？

假设你的代码：

```csharp
public async UniTask TestAsync()
{
    Debug.Log("开始");

    await UniTask.Delay(1000);

    Debug.Log("结束");
}
```

如果执行过程中，Unity 主线程被某段同步逻辑阻塞了 3 秒：

```csharp
Thread.Sleep(3000);
```

那么即使 UniTask 的 1 秒等待时间早已达到，后续的 `Debug.Log("结束")` 仍然无法及时执行。

因为它需要主线程重新运行到对应的调度阶段。

下面是一个简化时间线：

主线程阻塞时，UniTask 的恢复时间

这里还有一个容易忽略的细节：

`UniTask.Delay(1000)` 默认使用 `Time.deltaTime` 累计时间，受 `Time.timeScale` 和 Unity 时间更新机制影响。因此，实际延迟不一定恰好是现实世界的 1 秒。

如果需要按真实时间计算，可以使用：

```csharp
await UniTask.Delay(
    1000,
    DelayType.Realtime
);
```

但即便使用 `Realtime`，**主线程卡住时也无法按时执行后续代码**。citeturn303245search2turn303245search5

## 三、UniTask 能不能真正使用多线程？

可以，但需要显式切换。

```csharp
public async UniTask TestAsync()
{
    // 主线程
    Debug.Log("开始");

    await UniTask.SwitchToThreadPool();

    // 线程池线程
    int result = HeavyCalculation();

    await UniTask.SwitchToMainThread();

    // 回到 Unity 主线程
    Debug.Log(result);
}
```

假设主线程卡住了 3 秒：

- `HeavyCalculation()` 如果已经在线程池开始执行，仍然有机会继续计算。
- `SwitchToMainThread()` 后面的逻辑需要等待主线程恢复。
- 后台计算也不是绝对不受影响，例如 CPU 资源竞争、线程调度等仍可能影响速度。

注意，后台线程不要直接调用大多数 Unity 对象 API。citeturn303245search0turn303245search1

## 四、UniTask、Coroutine、Callback 的区别

| 特性 | UniTask | Coroutine | Callback |
|--------|--------|--------|--------|
| 主线程卡顿影响 | 会 | 会 | 取决于回调执行线程 |
| 默认创建新线程 | 否 | 否 | 否 |
| 支持多线程 | 支持显式切换 | 需借助其他机制 | 可以 |
| 异步流程组合 | 很方便 | 相对麻烦 | 容易嵌套 |
| GC 开销 | 可做到很低 | 迭代器通常有分配 | 取决于实现 |
| 取消、异常传播 | 支持 | 需自行组织 | 需自行设计 |

**Callback 也不意味着不会卡顿。** 如果网络线程收到数据后，将回调投递到 Unity 主线程执行，那么主线程卡住时，回调同样无法执行。

## 五、从源码角度，UniTask 为什么能做到低 GC？

这是 UniTask 相比传统 `Task` 的一个重要设计点。

它主要使用：

```csharp
public readonly partial struct UniTask
{
    // 内部包含任务源和版本标识等信息
}
```

核心设计包括：

1. `UniTask` 是值类型，减少普通任务对象的堆分配。
2. 使用自定义 `AsyncMethodBuilder`，优化异步状态机。
3. 通过 `IUniTaskSource` 表示异步操作的状态和结果。
4. 通过对象池复用部分异步任务源，降低重复分配成本。

不过，UniTask 并不保证所有异步调用都零 GC，例如捕获变量、异常、部分组合操作仍可能产生分配。citeturn303245search0turn303245search8

---

## 六、在中大型 MMO 项目中应该如何使用？

我更建议按工作类型划分，而不是所有异步操作都扔进线程池。

| 工作类型 | 建议方案 |
|--------|--------|
| UI 动画、流程等待 | UniTask + PlayerLoop |
| AssetBundle 异步加载 | Unity AsyncOperation + UniTask |
| 网络请求等待 | UniTask 包装异步接口 |
| 网络收包、协议解析 | 网络线程 + 消息队列 |
| 大量纯 C\# 数据计算 | ThreadPool / Job System |
| GameObject、Transform 操作 | 主线程 |

最重要的是区分：

**异步等待解决的是流程阻塞问题，多线程解决的是计算占用问题。**

如果想进一步研究 UniTask 原理，下一步最值得看的是这条源码调用链：

`UniTask.Delay → DelayPromise → PlayerLoopHelper.AddAction → PlayerLoopRunner → MoveNext → continuation`

它能够解释三个关键问题：

- 为什么 UniTask 不需要每个任务都创建线程？
- Unity 每帧是如何检查成千上万个 UniTask 的？
- UniTask 的状态机究竟在什么时机被唤醒？

这也是理解 UniTask 性能、GC 和调度开销的核心。

## 轮次 405928e9-3bb8-4b47-83b0-9c4b1825d0e0

### 用户

什么是 coroutine？  C# 携程 是啥

### 助手

**Coroutine（协程）是一种允许函数执行到一半时暂停，之后再从暂停位置继续执行的编程机制。**

在 Unity 中，协程通常指 `IEnumerator + yield return + StartCoroutine`。

但要注意：

**协程不是线程。Unity 的协程默认运行在主线程上，不会自动创建新线程。**

## 一、先看一个普通函数

```csharp
void Test()
{
    Debug.Log("A");
    Debug.Log("B");
    Debug.Log("C");
}
```

执行结果：

```text
A
B
C
```

这三个操作会连续执行，中间不会主动暂停。

现在我们希望：

- 输出 A。
- 等待 2 秒。
- 输出 B。
- 再等待一帧。
- 输出 C。

如果使用普通函数，就需要自己管理时间和状态。

而协程可以这样写：

```csharp
IEnumerator Test()
{
    Debug.Log("A");

    yield return new WaitForSeconds(2f);

    Debug.Log("B");

    yield return null;

    Debug.Log("C");
}
```

启动：

```csharp
StartCoroutine(Test());
```

执行效果：

```text
第 0 秒：输出 A

等待约 2 秒

第 2 秒：输出 B

等待下一帧

输出 C
```

这就是协程最直观的作用：**让一段跨越多帧的逻辑可以按照顺序书写。**

## 二、协程的底层原理是什么？

这里需要区分 C\# 和 Unity。

### 1\. C\# 本身提供的是迭代器机制

C\# 语言有 `yield return`，编译器会将包含 `yield` 的迭代器方法转换为一个状态机。

例如：

```csharp
IEnumerator Test()
{
    Debug.Log("A");

    yield return null;

    Debug.Log("B");
}
```

编译器生成的状态机大致类似：

```csharp
class TestIterator : IEnumerator
{
    private int state = 0;

    public object Current { get; private set; }

    public bool MoveNext()
    {
        switch (state)
        {
            case 0:
                Debug.Log("A");

                Current = null;
                state = 1;
                return true;

            case 1:
                Debug.Log("B");

                state = -1;
                return false;
        }

        return false;
    }

    public void Reset()
    {
        throw new NotSupportedException();
    }
}
```

这只是简化后的伪实现，但足以说明原理。

关键接口是：

```csharp
bool MoveNext();
```

每调用一次 `MoveNext()`，状态机就会向前执行，直到遇到下一个 `yield return` 或执行结束。

### 2\. Unity 负责调度 IEnumerator

C\# 编译器只负责生成状态机，并不会自动每帧执行它。

Unity 的 `StartCoroutine()` 会将这个迭代器交给 Unity 的协程调度系统。

这里有个重要结论：

**协程的暂停，不是 CPU 暂停，也不是主线程暂停，而是当前迭代器暂时不再继续执行。**

主线程仍然可以执行其他 Update、渲染逻辑和协程。

## 三、协程和线程有什么区别？

| 对比 | Coroutine（协程） | Thread（线程） |
|--------|--------|--------|
| 是否拥有独立线程 | 否 | 是 |
| Unity 中默认执行线程 | 主线程 | 取决于创建方式 |
| 能否真正并行计算 | 不能单独实现 | 可以 |
| 能否跨帧执行 | 可以 | 可以，但不是按帧调度 |
| 主线程卡顿是否影响 | 会 | 后台线程不一定 |
| 能否直接操作 Unity API | 主线程协程通常可以 | 后台线程大多不可以 |

例如：

```csharp
IEnumerator Test()
{
    // 假设这里执行了耗时 3 秒的同步计算
    HeavyCalculation();

    yield return null;
}
```

如果 `HeavyCalculation()` 阻塞主线程 3 秒，那么 Unity 就会卡顿 3 秒。

`yield return null` 只能让出后续执行，**无法把前面的耗时计算变成异步计算。**

## 四、C\# 协程和 UniTask 有什么关系？

二者都涉及编译器生成的状态机，但不是同一种机制。

|  | Unity Coroutine | UniTask |
|--------|--------|--------|
| 主要语法 | `IEnumerator / yield return` | `async / await` |
| 底层机制 | 迭代器状态机 | 异步状态机 |
| 谁负责恢复执行 | Unity 协程调度器 | Awaiter、任务完成通知或 PlayerLoop |
| 返回结果 | 不直接支持强类型结果 | 支持 `UniTask<T>` |
| 异常处理 | 有一定限制 | 更接近正常 `try/catch` |
| 线程切换 | 无内建线程切换语义 | 支持显式切换线程 |

例如，同样等待 2 秒：

**Unity Coroutine：**

```csharp
IEnumerator LoadAsync()
{
    yield return new WaitForSeconds(2f);

    Debug.Log("加载完成");
}
```

**UniTask：**

```csharp
async UniTask LoadAsync()
{
    await UniTask.Delay(2000);

    Debug.Log("加载完成");
}
```

它们在这个场景下表现相似，但底层调度方式不同。

## 五、C\# 本身有没有协程？

严格来说，**C\# 没有一个独立的、名为 Coroutine 的语言关键字或统一协程运行时**。

C\# 提供了两套相关机制：

- `yield return`：迭代器状态机，Unity 用它实现协程。
- `async/await`：异步状态机，`Task` 和 `UniTask` 都建立在这套机制之上。

所以不能简单认为 C\# 协程就等于 Unity Coroutine，也不能把所有 `async/await` 都直接称为 Unity 协程。

---

## 六、一个值得深入理解的问题

假设：

```csharp
IEnumerator Test()
{
    Debug.Log("A");

    yield return null;

    Debug.Log("B");
}
```

调用：

```csharp
StartCoroutine(Test());

Debug.Log("C");
```

在 Unity 正常启动协程的情况下，输出顺序是：

```text
A
C
B
```

原因是 `StartCoroutine` 会先执行协程，直到第一次 `yield return`，随后返回调用方。后续代码继续执行，而协程下一次恢复时才输出 B。

**真正值得理解的底层问题是：`yield return` 为什么能够保留局部变量、执行位置以及循环状态？**

答案就在 C\# 编译器生成的 `IEnumerator` 状态机中。它与 UniTask 的异步状态机有相似之处，但保存状态、等待完成和恢复执行的具体机制不同。

## 轮次 38256f60-4a6f-4f42-bdd1-e55773c427d3

### 用户

抛开 unity ， C# 原生 携程是什么样子？

### 助手

抛开 Unity，**C\# 原生并没有一个叫 `Coroutine` 的独立语言机制**。

但 C\# 提供了两种能够实现类似协程行为的机制：

1. **`yield return` \+ `IEnumerator`**：迭代器状态机，可以暂停执行、保存状态、下次继续。
2. **`async/await` \+ `Task`**：异步状态机，可以等待异步操作完成后恢复执行。

如果你想理解协程最底层的原理，建议先从 `yield return` 开始，因为它能非常直观地展示协程如何暂停和恢复。

## 一、最原始的 C\# 协程是什么样子？

下面是一段纯 C\# 代码，不依赖 Unity，可以直接在控制台程序中运行。

```csharp
using System;
using System.Collections;
using System.Threading;

class Program
{
    static IEnumerator MyCoroutine()
    {
        Console.WriteLine("A");

        yield return null;

        Console.WriteLine("B");

        yield return null;

        Console.WriteLine("C");
    }

    static void Main()
    {
        IEnumerator coroutine = MyCoroutine();

        Console.WriteLine("开始");

        coroutine.MoveNext();

        Console.WriteLine("第一次暂停");

        coroutine.MoveNext();

        Console.WriteLine("第二次暂停");

        coroutine.MoveNext();

        Console.WriteLine("结束");
    }
}
```

输出结果：

```text
开始
A
第一次暂停
B
第二次暂停
C
结束
```

这里有几个关键点。

**1\. 调用 `MyCoroutine()` 并不会立即执行函数体。**

```csharp
IEnumerator coroutine = MyCoroutine();
```

只是获取一个迭代器对象。

**2\. `MoveNext()` 才是真正驱动代码执行的接口。**

```csharp
coroutine.MoveNext();
```

第一次调用执行到第一个 `yield return`。

第二次调用从上次暂停的位置继续执行。

第三次调用执行剩余代码。

这就是最基本的协作式执行机制。

## 二、为什么它能记住上一次执行的位置？

因为 C\# 编译器会把 `yield return` 方法转换成一个状态机。

例如：

```csharp
static IEnumerator Test()
{
    int count = 10;

    Console.WriteLine(count);

    yield return null;

    count++;

    Console.WriteLine(count);
}
```

你可能会疑惑：

第一次 `MoveNext()` 执行完后，函数不是已经返回了吗？

为什么第二次调用还能访问 `count`？

原因是编译器把需要跨越暂停点的局部变量提升成了状态机对象的字段。

编译器生成的代码大致相当于：

```csharp
class TestStateMachine : IEnumerator
{
    private int state = 0;
    private int count;

    public object Current => null;

    public bool MoveNext()
    {
        switch (state)
        {
            case 0:
                count = 10;

                Console.WriteLine(count);

                state = 1;
                return true;

            case 1:
                count++;

                Console.WriteLine(count);

                state = -1;
                return false;
        }

        return false;
    }

    public void Reset()
    {
        throw new NotSupportedException();
    }
}
```

真正的编译器生成代码会更复杂，但核心就是：

- `state` 保存执行位置。
- `count` 保存局部变量。
- `MoveNext()` 恢复执行。
- `Current` 保存当前 `yield return` 产生的值。

因此，**协程并不是把整个线程的调用栈冻结起来，而是把需要保存的状态转移到了状态机对象中。**

## 三、纯 C\# 能不能实现类似 Unity 的协程调度器？

可以。

我们自己写一个非常简单的调度器：

```csharp
using System;
using System.Collections;
using System.Collections.Generic;
using System.Threading;

class CoroutineScheduler
{
    private readonly List<IEnumerator> coroutines = new();

    public void Start(IEnumerator coroutine)
    {
        coroutines.Add(coroutine);
    }

    public void Update()
    {
        for (int i = coroutines.Count - 1; i >= 0; i--)
        {
            if (!coroutines[i].MoveNext())
            {
                coroutines.RemoveAt(i);
            }
        }
    }
}

class Program
{
    static IEnumerator Test(string name)
    {
        for (int i = 0; i < 3; i++)
        {
            Console.WriteLine($"{name}: {i}");

            yield return null;
        }
    }

    static void Main()
    {
        var scheduler = new CoroutineScheduler();

        scheduler.Start(Test("A"));
        scheduler.Start(Test("B"));

        while (true)
        {
            scheduler.Update();

            Thread.Sleep(1000);
        }
    }
}
```

输出：

```text
B: 0
A: 0

等待 1 秒

B: 1
A: 1

等待 1 秒

B: 2
A: 2
```

这就实现了一个最简单的协程调度器。

这里所有协程都运行在同一个线程中。

它们并没有真正并行，只是在每次 `Update()` 时轮流向前执行一段。

另外，这个简化调度器只支持每次 `yield` 暂停一次，并没有实现等待时间、嵌套迭代器、取消和异常管理。

## 四、那 C\# 的 async/await 算不算协程？

从广义上讲，`async/await` 也具备协程式的暂停与恢复能力，但它属于另一套异步编程机制。

例如：

```csharp
using System;
using System.Threading.Tasks;

class Program
{
    static async Task TestAsync()
    {
        Console.WriteLine("A");

        await Task.Delay(1000);

        Console.WriteLine("B");
    }

    static async Task Main()
    {
        Task task = TestAsync();

        Console.WriteLine("C");

        await task;
    }
}
```

输出：

```text
A
C

等待约 1 秒

B
```

这段代码与 `IEnumerator` 有一个非常重要的区别。

对于 `IEnumerator`：

```csharp
yield return null;
```

暂停后，必须有人调用 `MoveNext()` 才能继续。

而对于 `async/await`：

```csharp
await Task.Delay(1000);
```

当等待的操作完成后，异步机制会安排状态机继续执行。

不需要你手动调用 `MoveNext()`。

不过，`async/await` 编译生成的状态机内部同样有一个 `MoveNext()` 方法，只是它由异步方法构建器及其续体机制驱动，而不是由你直接调用。

## 五、两种机制的本质区别

| 对比 | `yield return` | `async/await` |
|--------|--------|--------|
| 状态机 | 迭代器状态机 | 异步状态机 |
| 谁驱动恢复 | 调用方调用 `MoveNext()` | 等待器与续体调度机制 |
| 是否自动创建线程 | 否 | 否 |
| 是否能保存局部变量 | 是 | 是 |
| 是否能返回结果 | 通过 `Current` 逐个产出 | `Task<T>` 返回最终结果 |
| 主要用途 | 惰性迭代、自定义协作式调度 | 异步 I/O、任务组合与等待 |
| 是否必须有调度器 | 需要外部代码推进迭代 | 依赖具体等待操作及其调度机制 |

## 六、一个更深层的问题：协程是不是没有线程切换成本？

对于上面这个单线程 `IEnumerator` 调度器，确实没有操作系统线程之间的上下文切换。

但它仍然有成本：

- 调用 `MoveNext()` 的成本。
- 状态机的分支跳转成本。
- 状态机对象的内存分配。
- 调度器遍历和管理任务的成本。

而且协程不会抢占正在运行的代码。

假设：

```csharp
IEnumerator Test()
{
    while (true)
    {
        HeavyCalculation();

        yield return null;
    }
}
```

如果 `HeavyCalculation()` 执行 500ms，那么调度器当前线程就会被占用 500ms。

其他协程只能等待它执行到 `yield return` 后才能获得执行机会。

这就是\*\*协作式调度（Cooperative Scheduling）\*\*与操作系统抢占式线程调度的一个核心区别。

---

**总结：**

C\# 原生的 `yield return` 是编译器提供的迭代器状态机机制，而不是一个完整的协程框架。你可以在它之上自己实现协程调度器。

`async/await` 则是另一种更完整的异步编程机制，支持通过等待器自动安排恢复执行。

理解了这两套状态机，再去研究 Unity Coroutine、UniTask、`Task`，就会发现它们最大的差异并不只是语法，而是**状态机由谁驱动、在什么线程执行、什么时候恢复，以及如何管理任务生命周期**。

## 轮次 09788631-a93a-46b3-9d19-9b5100c24168

### 用户

我很好奇 unity 的 player loop 是如何实现的？ 它怎么保证 固定帧率 执行？

### 助手

Unity 的 `PlayerLoop` 本质上是一个**由 Unity 引擎原生层驱动的主循环调度系统**。

它负责协调：

- 输入处理
- 物理模拟
- `FixedUpdate`
- `Update`
- `LateUpdate`
- 动画更新
- 渲染
- 协程恢复
- 其他引擎子系统

但首先要纠正一个非常重要的概念：

**Unity 并不能保证每秒执行固定数量的渲染帧。它真正实现的是固定时间步长的物理模拟，以及尽可能满足目标帧率的渲染调度。**

这两者完全不同。

## 一、PlayerLoop 本质上就是一个 while 循环

如果我们用 C\# 模拟 Unity 引擎的主循环，最简化的版本大概是：

```csharp
while (applicationRunning)
{
    ProcessInput();

    Update();

    LateUpdate();

    Render();
}
```

实际的 Unity PlayerLoop 要复杂得多，包含多个阶段及大量子系统。

注意：这只是概念模型，并不是 Unity 原生 C++ 的实际源码。

Unity 的原生引擎负责驱动这些阶段，而 C\# 层通过 `PlayerLoopSystem` 可以查看和定制部分调度结构。

---

## 二、Unity 如何实现 FixedUpdate 的固定频率？

假设：

```csharp
Time.fixedDeltaTime = 0.02f;
```

理论上的物理更新频率是：

\[
f = \frac{1}{0.02} = 50\ \text{Hz}
\]

也就是说，Unity 希望每经过 0.02 秒的游戏时间，就执行一次固定时间步长更新。

但是，**它并不是创建一个独立线程，每隔 20ms 调用一次 FixedUpdate。**

Unity 使用的核心思想是：

**时间累加器（Time Accumulator）+ 固定步长（Fixed Timestep）。**

我们可以自己实现一个简化版本：

```csharp
double accumulator = 0;
double fixedDeltaTime = 0.02;

while (running)
{
    double frameDelta = GetElapsedTime();

    accumulator += frameDelta;

    while (accumulator >= fixedDeltaTime)
    {
        FixedUpdate();
        PhysicsSimulation();

        accumulator -= fixedDeltaTime;
    }

    Update();
    LateUpdate();
    Render();
}
```

这里有几个非常关键的细节：

1. `frameDelta` 表示两次循环之间经过的时间。
2. `accumulator` 保存尚未用于固定步长模拟的时间。
3. 如果累计时间超过 20ms，就执行一次固定更新。
4. 如果累计时间达到 40ms，可能连续执行两次固定更新。
5. 如果累计时间不足 20ms，这一帧可能完全不执行 `FixedUpdate`。

实际 Unity 还会处理最大允许时间步长、物理系统配置和时间缩放等问题。

## 三、用时间线理解 FixedUpdate 和 Update

假设：

- 渲染帧率：60 FPS，每帧约 16.67ms。
- 物理频率：50 Hz，每个固定步长 20ms。

模拟 6 个渲染帧，FixedUpdate 如何分布？

理想化时间线：100ms 内执行 6 次 Update、5 次 FixedUpdate。实际每帧的固定更新次数取决于累计时间。

这说明：

- `Update()` 随渲染帧更新。
- `FixedUpdate()` 随固定模拟时间推进。
- 两者不一定一一对应。

Unity 官方文档也明确指出，固定更新的真实调用间隔并不一定固定，因为它必须依附于主循环执行。citeturn911389search0turn911389search2

### 如果主线程突然卡顿 100ms 呢？

假设 `fixedDeltaTime = 0.02`，而某一帧累计了 100ms 的待模拟时间。

那么下一轮 PlayerLoop 可能需要执行：

```text
FixedUpdate()
FixedUpdate()
FixedUpdate()
FixedUpdate()
FixedUpdate()

Update()
LateUpdate()
Render()
```

这就是物理模拟的追帧机制。

但这里有一个危险：

如果每次 FixedUpdate 都非常耗时，那么连续追帧又会导致下一帧变慢，形成恶性循环。

所以 Unity 还提供：

```csharp
Time.maximumDeltaTime
```

它限制单帧能够推进的游戏时间和固定模拟追赶量，避免无限追赶。超过限制的真实时间不会全部补进物理模拟。citeturn911389search9turn911389search11

---

## 四、Unity 如何控制 60 FPS？

现在讨论另一个问题：`Application.targetFrameRate = 60` 是怎么实现的？

60 FPS 意味着理想情况下：

\[
T = \frac{1000}{60} \approx 16.67ms
\]

Unity 希望每隔约 16.67ms 产生一个渲染帧。

假设一帧 CPU 和 GPU 相关工作能够在 8ms 内完成，那么还有约 8.67ms 的时间预算。

引擎可以通过等待机制进行帧率限制，而不是无休止地运行下一帧。

简化示意：

```csharp
double targetFrameTime = 1.0 / 60.0;

while (running)
{
    double frameStart = Clock.Now();

    RunPlayerLoop();
    Render();

    double elapsed = Clock.Now() - frameStart;
    double remaining = targetFrameTime - elapsed;

    if (remaining > 0)
    {
        Wait(remaining);
    }
}
```

这里的 `Wait` 是抽象示意，并不是 Unity 的真实实现。实际帧调度涉及平台计时器、显示同步、GPU 提交以及操作系统调度。

**如果一帧本来就花了 25ms，Unity 不可能通过等待把它变成 16.67ms。**

因此，目标帧率是上限或目标，而不是硬实时保证。

### VSync 又是什么？

桌面平台可以使用：

```csharp
QualitySettings.vSyncCount = 1;
```

在 60Hz 屏幕上，理想情况下每次屏幕刷新对应一帧，也就是 60 FPS。

如果设置：

```csharp
QualitySettings.vSyncCount = 2;
```

理想情况下每两次屏幕刷新显示一帧，即 30 FPS。

桌面平台启用 VSync 时，通常会覆盖 `Application.targetFrameRate` 的软件限帧设置；移动平台则通常使用 `targetFrameRate` 控制目标帧率。citeturn911389search12turn911389search14

---

## 五、Unity 的 PlayerLoop 到底是 C\# 还是 C++ 实现的？

这是理解 Unity 架构的关键。

Unity 的核心主循环由原生引擎驱动，C\# 暴露了一套用于查看和修改调度结构的 API：

```csharp
UnityEngine.LowLevel.PlayerLoop
UnityEngine.LowLevel.PlayerLoopSystem
```

可以通过以下接口获取：

```csharp
PlayerLoop.GetCurrentPlayerLoop();
PlayerLoop.GetDefaultPlayerLoop();
PlayerLoop.SetPlayerLoop(...);
```

其中，`GetCurrentPlayerLoop()` 返回当前引擎系统的更新顺序，`SetPlayerLoop()` 允许自定义部分执行顺序。citeturn911389search5turn911389search15

### 1\. 实际查看 PlayerLoop 的结构

你可以直接在 Unity 中运行下面的代码：

```csharp
using UnityEngine;
using UnityEngine.LowLevel;

public class PlayerLoopInspector : MonoBehaviour
{
    private void Start()
    {
        var loop = PlayerLoop.GetCurrentPlayerLoop();

        PrintLoop(loop, 0);
    }

    private void PrintLoop(
        PlayerLoopSystem system,
        int depth)
    {
        string indent = new string(' ', depth * 2);

        Debug.Log($"{indent}{system.type}");

        if (system.subSystemList == null)
            return;

        foreach (var subSystem in system.subSystemList)
        {
            PrintLoop(subSystem, depth + 1);
        }
    }
}
```

你会看到类似：

```text
UnityEngine.PlayerLoop.Initialization
  PlayerUpdateTime
  ...

UnityEngine.PlayerLoop.EarlyUpdate
  ...

UnityEngine.PlayerLoop.FixedUpdate
  ScriptRunBehaviourFixedUpdate
  PhysicsFixedUpdate
  ...

UnityEngine.PlayerLoop.Update
  ScriptRunBehaviourUpdate
  ...

UnityEngine.PlayerLoop.PreLateUpdate
  ScriptRunBehaviourLateUpdate
  ...

UnityEngine.PlayerLoop.PostLateUpdate
  ...
```

具体子系统名称和结构随 Unity 版本、平台及配置变化。

### 2\. PlayerLoopSystem 是什么？

它可以理解为一个调度节点。

其核心成员包括：

```csharp
public Type type;
public PlayerLoopSystem[] subSystemList;
public UpdateFunction updateFunction;
public IntPtr updateFunction;
```

这里需要纠正一下上面的示意：实际 API 中 `updateFunction` 是 `UpdateFunction` 委托，原生函数指针成员名为 `updateFunction` 的说法不准确，原生指针字段是 `updateFunction` 以外的 `updateFunction` 对应内部实现；在公开结构中使用的是 `updateFunction` 和 `updateDelegate` 等成员，具体以安装版本的 Unity API 为准。

更重要的是它表达的结构：

```text
PlayerLoopSystem
    |
    +-- type
    |
    +-- subSystemList
    |       |
    |       +-- 子系统 A
    |       +-- 子系统 B
    |
    +-- 原生更新函数或托管委托
```

因此，PlayerLoop 可以看成一棵调度树。

引擎每帧按照规定的结构执行各个子系统。

不过，**它不是一个可以完整反映 Unity 内部所有 C++ 调用的公开执行树**，部分底层工作并不会以独立 C\# 节点呈现。

## 六、如果我要自己实现一个 Unity PlayerLoop 呢？

可以将前面讨论的固定时间步长、普通帧更新和目标帧率组合起来：

```csharp
using System;
using System.Diagnostics;
using System.Threading;

class GameLoop
{
    private const double FixedStep = 0.02;
    private const double TargetFrame = 1.0 / 60.0;
    private const double MaxFrameDelta = 0.333;

    public void Run()
    {
        var clock = Stopwatch.StartNew();

        double previousTime = clock.Elapsed.TotalSeconds;
        double accumulator = 0;

        while (true)
        {
            double frameStart = clock.Elapsed.TotalSeconds;

            double delta = frameStart - previousTime;
            previousTime = frameStart;

            // 限制单帧模拟时间
            delta = Math.Min(delta, MaxFrameDelta);

            accumulator += delta;

            // 固定步长更新
            while (accumulator >= FixedStep)
            {
                FixedUpdate(FixedStep);
                accumulator -= FixedStep;
            }

            // 普通帧更新
            Update(delta);

            // 渲染
            Render();

            // 简化的软件限帧
            double elapsed =
                clock.Elapsed.TotalSeconds - frameStart;

            double remaining = TargetFrame - elapsed;

            if (remaining > 0)
            {
                Thread.Sleep(
                    (int)(remaining * 1000)
                );
            }
        }
    }

    void FixedUpdate(double dt) { }
    void Update(double dt) { }
    void Render() { }
}
```

这个例子只是用于理解原理，不是生产级游戏主循环。尤其是 `Thread.Sleep` 的唤醒精度并不足以保证稳定的 60 FPS，也没有实现平台消息泵、显示同步和真实的 GPU 渲染调度。

## 七、最值得记住的三个结论

1. **PlayerLoop 是调度系统，不是一个固定频率的定时器。** 它负责按阶段执行引擎系统，运行速度受实际工作负载影响。
2. **FixedUpdate 固定的是模拟时间步长，不是实际调用间隔。** 主线程卡顿时，多个 FixedUpdate 可能集中在同一帧执行。
3. **60 FPS 是渲染目标，不是绝对保证。** Unity 可以通过软件限帧或 VSync 控制帧节奏，但无法保证耗时超过 16.67ms 的帧按时完成。

还有一个与前面 UniTask 讨论直接相关的问题：

**如果 UniTask 将 10,000 个任务注册到 `PlayerLoopTiming.Update`，Unity 是如何在每帧执行这些任务的？**

这就涉及 `PlayerLoopHelper`、`PlayerLoopRunner`、`IPlayerLoopItem.MoveNext()`，以及 UniTask 如何将自己的调度器插入 Unity 的原生 PlayerLoop。它们构成了 UniTask 主线程异步调度的核心实现。

## 轮次 03030477-440f-4381-8f72-c1c367c45b90

### 用户

继续

### 助手

接下来我们深入 UniTask 的源码实现，重点研究：

**UniTask 是如何将自己的调度器注入 Unity PlayerLoop，以及如何在单线程中管理成千上万个异步任务的。**

这部分涉及几个核心类：

- `PlayerLoopHelper`：负责将 UniTask 的调度节点注册到 Unity PlayerLoop。
- `PlayerLoopRunner`：负责执行需要逐帧检查的异步任务。
- `IPlayerLoopItem`：UniTask 内部可被 PlayerLoop 驱动的任务接口。
- `ContinuationQueue`：负责执行已经安排好的后续逻辑。

## 一、先理解 UniTask 的整体架构

假设有这样的代码：

```csharp
async UniTask TestAsync()
{
    Debug.Log("A");

    await UniTask.Delay(1000);

    Debug.Log("B");
}
```

这里发生的事情，并不是 UniTask 为 `Delay` 创建了一个后台线程。

它会创建或复用一个用于表示等待状态的任务源，并把需要逐帧检查的对象注册到自己的 PlayerLoop 调度器。

UniTask 主线程调度架构示意。不同等待操作可能使用不同的任务源和调度路径。

这里最重要的是：

**Unity PlayerLoop 不需要知道每个 UniTask 的存在，它只需要执行 UniTask 注入的调度节点。**

至于有多少异步任务、哪些已经完成、哪些需要继续等待，都由 UniTask 自己管理。

## 二、PlayerLoopHelper 如何把调度器注入 Unity？

我查了 UniTask 官方 GitHub 源码，核心文件是：

urlPlayerLoopHelper.cs 源码https://github.com/Cysharp/UniTask/blob/master/src/UniTask/Assets/Plugins/UniTask/Runtime/PlayerLoopHelper.cs

核心思路只有三步。

### 第一步：获取 Unity 当前 PlayerLoop

```csharp
var playerLoop = PlayerLoop.GetCurrentPlayerLoop();
```

这个结构包含了 Unity 的主要更新阶段。

### 第二步：创建自己的调度节点

下面是从源码提炼出来的关键逻辑：

```csharp
var yieldLoop = new PlayerLoopSystem
{
    type = loopRunnerYieldType,
    updateDelegate = cq.Run
};

var runnerLoop = new PlayerLoopSystem
{
    type = loopRunnerType,
    updateDelegate = runner.Run
};
```

这里的 `cq.Run` 和 `runner.Run` 是两个托管委托。

Unity 执行到对应的 PlayerLoop 节点时，就会调用这些委托。

注意，UniTask 并不是把每个异步任务直接注册到 Unity PlayerLoop，而是注册少量调度节点，任务由这些节点内部管理。

### 第三步：修改 PlayerLoop 并提交

```csharp
playerLoop.subSystemList = copyList;

PlayerLoop.SetPlayerLoop(playerLoop);
```

于是 Unity 后续执行 PlayerLoop 时，就会调用 UniTask 的调度器。citeturn304897search0turn304897search1

---

## 三、PlayerLoopRunner 如何管理 10,000 个任务？

官方源码：

urlPlayerLoopRunner.cshttps://github.com/Cysharp/UniTask/blob/master/src/UniTask/Assets/Plugins/UniTask/Runtime/Internal/PlayerLoopRunner.cs

它的核心数据结构并不是每个任务一个线程，也不是每个任务一个 Unity GameObject。

而是类似下面这样的结构：

```csharp
internal sealed class PlayerLoopRunner
{
    IPlayerLoopItem[] loopItems;

    MinimumQueue<IPlayerLoopItem> waitQueue;

    int tail;

    bool running;
}
```

其中：

- `loopItems`：保存正在被调度的任务。
- `tail`：记录有效任务范围。
- `waitQueue`：暂存调度器执行期间新加入的任务。
- `running`：表示当前是否正在执行调度。

### 1\. 每个任务只需要实现 MoveNext

```csharp
public interface IPlayerLoopItem
{
    bool MoveNext();
}
```

返回值的意义：

- `true`：任务尚未结束，后续还需要继续调度。
- `false`：任务已完成，可以从调度器移除。

这与我们前面研究的 `IEnumerator.MoveNext()` 很像。

但注意：**接口名字相同，不代表两个接口属于同一套机制。**

`IEnumerator` 用 `MoveNext()` 推进迭代器；UniTask 的 `IPlayerLoopItem` 用它检查任务是否仍需参与 PlayerLoop 调度。

### 2\. 每帧遍历任务

我们用一段简化代码还原其核心思想：

```csharp
void Run()
{
    for (int i = 0; i < tail; i++)
    {
        IPlayerLoopItem item = loopItems[i];

        if (item == null)
            continue;

        bool keepRunning = item.MoveNext();

        if (!keepRunning)
        {
            loopItems[i] = null;
        }
    }

    // 整理已完成任务
    // 合并执行期间新加入的任务
}
```

实际源码使用了更复杂的数组管理、锁和整理逻辑，以减少不必要的分配，并处理任务执行过程中添加新任务的情况。

例如，10,000 个任务都在等待时间到达：

```csharp
await UniTask.Delay(1000);
```

在通常的 PlayerLoop 驱动实现中，调度器会逐帧检查这些尚未完成的等待任务。

一次 PlayerLoopRunner.Run() 的工作过程

整理任务数组

**保留未完成任务**

移除已完成任务，并接纳待加入的任务

### 3\. 为什么要有 waitQueue？

假设在执行任务 A 时，又注册了任务 B：

```csharp
bool MoveNext()
{
    PlayerLoopHelper.AddAction(
        PlayerLoopTiming.Update,
        anotherTask
    );

    return false;
}
```

如果直接修改正在遍历的数组，就可能造成调度顺序混乱，甚至在错误的实现中导致迭代问题。

所以 UniTask 使用待加入队列，在适当时机把新任务合并进调度数组。

这与游戏网络系统中常见的“处理队列 + 待处理队列”思路相似，但 UniTask 的具体实现并不是简单交换两个队列。

---

## 四、ContinuationQueue 和 PlayerLoopRunner 有什么区别？

这是整个 UniTask 调度系统中最容易被忽略的设计。

它们虽然都挂在 PlayerLoop 上，但承担的工作不同。

|  | ContinuationQueue | PlayerLoopRunner |
|--------|--------|--------|
| 保存内容 | `Action` 续体 | `IPlayerLoopItem` |
| 主要工作 | 在指定阶段执行排队的回调 | 逐帧检查任务状态 |
| 是否需要持续轮询 | 通常不需要 | 需要 |
| 典型场景 | `UniTask.Yield`、线程切回主线程 | `UniTask.Delay`、`WaitUntil` |

官方源码中分别通过以下接口注册：

```csharp
// 将任务加入逐帧检查调度器
PlayerLoopHelper.AddAction(
    PlayerLoopTiming.Update,
    item
);

// 将续体加入指定阶段的执行队列
PlayerLoopHelper.AddContinuation(
    PlayerLoopTiming.Update,
    continuation
);
```

因此，不是所有 UniTask 都需要每帧轮询。citeturn304897search0turn304897search6

## 五、以 UniTask.Delay 为例，完整走一遍执行过程

```csharp
async UniTask TestAsync()
{
    Debug.Log("A");

    await UniTask.Delay(1000);

    Debug.Log("B");
}
```

1. **执行到 `UniTask.Delay(1000)`**
   
   UniTask 创建或复用等待任务源，例如 `DelayPromise`，并将其加入对应的 `PlayerLoopRunner`。
2. **编译器生成的异步状态机挂起**
   
   因为任务尚未完成，`await` 注册续体，当前异步方法返回控制权。
3. **Unity 每帧执行 PlayerLoop**
   
   UniTask 的 `PlayerLoopRunner.Run()` 被调用，进而调用 `DelayPromise.MoveNext()`。
4. **检查等待时间**
   
   如果尚未达到指定延迟，返回 `true`，继续保留任务。
5. **等待时间满足**
   
   `DelayPromise` 将任务标记为完成，并触发已注册的续体。续体可能在这次任务完成通知过程中同步执行。
6. **恢复 async 状态机**
   
   状态机继续执行 `await` 后面的 `Debug.Log("B")`。

这里需要特别注意：

**UniTask 并不是统一将所有已完成任务再投递到下一帧。** 任务完成时，续体可能直接在当前调用栈上执行。

这意味着如果 `await` 后面的代码非常耗时，它也可能直接增加当前 PlayerLoop 阶段的耗时。

## 六、10,000 个 UniTask 会不会卡顿？

答案是：**取决于任务类型、每次检查成本，以及有多少任务在同一帧恢复。**

我们做一个假设性的性能预算。

UniTask 逐帧轮询开销估算器

活跃轮询任务数  个

> **滑块**
>
> 当前值不可用。
>
> **范围：** 1000 至 50000
>
> **步长：** 1000

每任务检查耗时（假设）  μs

> **滑块**
>
> 当前值不可用。
>
> **范围：** 0.1 至 2
>
> **步长：** 0.1

---

每帧总轮询时间

# ms

占 60 FPS 帧预算

# %

这是数学估算，不是 UniTask 的实测性能。实际耗时受 CPU、IL2CPP、任务类型、缓存命中率和续体逻辑等因素影响。

例如，假设每个任务检查耗时 0.2 微秒：

\[
10000 \times 0.2\mu s = 2ms
\]

如果这些任务都在同一帧完成，还需要额外计算恢复 10,000 个异步状态机及执行后续业务逻辑的成本。

这往往比单纯检查任务状态更值得关注。

## 七、中大型 MMO 项目应该怎么优化？

我的建议不是避免使用 UniTask，而是避免把所有周期性工作都设计成大量独立的逐帧轮询。

例如：

```csharp
await UniTask.WaitUntil(() => player.HP <= 0);
```

如果有 10,000 个这样的等待任务，就可能每帧执行 10,000 次条件检查。

而对于角色死亡这种明确的状态变化，事件通知往往更合适：

```csharp
player.OnDead += HandleDead;
```

可以按任务特点选择：

- **时间等待**：使用 UniTask.Delay，数量极大时可以考虑集中式定时器。
- **状态变化等待**：优先考虑事件驱动。
- **异步 I/O**：优先利用操作完成通知，而不是自己每帧轮询。
- **大量 CPU 计算**：使用线程池或 Job System，而不是让 UniTask 主线程轮询承担计算。
- **逐帧逻辑**：使用 PlayerLoop，但要控制任务数量和单次执行成本。

还有一个重要区别：`UniTask.Delay` 的 PlayerLoop 实现属于逐帧检查，但 `Task.Delay` 在常规 .NET 环境下主要依靠计时器等机制，不是 Unity PlayerLoop 逐帧检查。因此，不能笼统地说所有 `async/await` 都有相同的每帧开销。

---

## 八、接下来最值得深入的是 UniTask 的状态机内存管理

我们已经知道：

`PlayerLoopRunner → IPlayerLoopItem.MoveNext() → 完成任务 → 恢复 async 状态机`

但这里还隐藏着一个非常关键的问题：

**既然 C\# 的 async 状态机需要保存局部变量和执行位置，UniTask 又是如何减少 GC 的？**

下一步可以沿着这条源码链继续：

```text
AsyncUniTaskMethodBuilder
        ↓
AsyncUniTask<TStateMachine>
        ↓
UniTaskCompletionSourceCore<T>
        ↓
IUniTaskSource
        ↓
TaskPool
```

其中最有价值的两个问题是：

1. 为什么 `UniTask` 是 `struct`，异步执行过程中却仍然可能需要堆对象？
2. 为什么一个普通 `UniTask` 通常不能像 `Task` 一样被反复 `await`？

这两个问题能把 **C\# 编译器状态机、UniTask 零分配优化、对象池和任务生命周期**真正串联起来。

源码参考：urlStateMachineRunner.cshttps://github.com/Cysharp/UniTask/blob/master/src/UniTask/Assets/Plugins/UniTask/Runtime/CompilerServices/StateMachineRunner.cs。

