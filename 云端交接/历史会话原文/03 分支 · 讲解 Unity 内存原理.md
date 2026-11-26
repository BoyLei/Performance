# 分支 · 讲解 Unity 内存原理

会话 ID：`6afd4816-be60-83ec-b35b-3f6759b55037`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 5735f7ed-be37-4256-abf8-24bc0f7d0da8

### 用户

如果 解析接口是 无状态的函数， 那么 同时在多个线程调用这个接口， 没问题吧

### 助手

**对。如果 Protobuf 解析接口是真正无状态的，并且所有输入、输出数据互相独立，那么多个线程同时调用同一个解析接口，通常是线程安全的。**

但需要区分两个概念：

- **函数无状态**：函数本身不保存可变状态。
- **线程安全**：函数执行过程中访问的所有共享资源都不会产生数据竞争。

无状态是线程安全的重要条件，但还需要检查函数内部调用的其他代码。

## 一、线程安全的例子

假设使用 Google.Protobuf：

```csharp
public static PlayerInfo ParsePlayer(byte[] bytes)
{
    return PlayerInfo.Parser.ParseFrom(bytes);
}
```

多个线程并发调用：

```csharp
Task.Run(() => ParsePlayer(bytesA));
Task.Run(() => ParsePlayer(bytesB));
Task.Run(() => ParsePlayer(bytesC));
```

这种写法通常是安全的。

原因是：

1. `PlayerInfo.Parser` 是可共享的解析器，Google.Protobuf 的 `MessageParser<T>` 支持并发解析。
2. 每次解析会创建独立的 `PlayerInfo` 对象。
3. 每个线程读取自己的输入数据。
4. 各线程之间没有共享可变的解析结果。

因此，**不需要为了保护这个解析接口而额外加 `lock`**。

## 二、看起来无状态，但实际上不安全

例如：

```csharp
private static readonly byte[] TempBuffer = new byte[4096];

public static PlayerInfo Parse(byte[] bytes)
{
    // 多线程同时修改共享缓冲区
    Array.Copy(bytes, TempBuffer, bytes.Length);

    return PlayerInfo.Parser.ParseFrom(TempBuffer);
}
```

虽然 `Parse()` 没有实例字段，但使用了共享的静态缓冲区。

两个线程同时执行时，就可能相互覆盖数据。

还有一种情况：

```csharp
public static PlayerInfo Parse(byte[] bytes)
{
    return PlayerInfo.Parser.ParseFrom(bytes);
}
```

接口本身安全，但如果 `bytes` 在解析期间被网络接收线程重新写入，同样不安全。

所以必须保证：

**输入缓冲区在整个解析过程中保持不变。**

## 三、Protobuf 多线程解析的安全边界

| 对象或操作 | 能否并发使用 |
|--------|--------|
| 同一个 `MessageParser<T>` 解析不同输入 | 可以 |
| 多线程分别创建独立消息对象 | 可以 |
| 多线程只读同一份不变的 `byte[]` | 可以 |
| 多线程同时修改同一个消息对象 | 不安全 |
| 解析期间修改输入 `byte[]` | 不安全 |
| 多线程使用同一个可变 `CodedInputStream` | 不安全 |
| 多线程写同一个普通 `Dictionary` | 不安全 |

这里假设使用的是 Google.Protobuf 官方 C\# 实现；其他 Protobuf 库需要分别确认其线程安全约束。

## 四、对于你的 MMO 网络系统

如果你准备让多个 Worker 并发解析网络消息，可以这样设计：

```csharp
public static IMessage ParsePacket(
    int messageId,
    byte[] payload)
{
    return messageId switch
    {
        1001 => PlayerInfo.Parser.ParseFrom(payload),
        1002 => MonsterInfo.Parser.ParseFrom(payload),
        1003 => SkillInfo.Parser.ParseFrom(payload),
        _ => throw new Exception("Unknown message")
    };
}
```

每个 Worker 都可以调用同一个 `ParsePacket()`，前提是 `payload` 在解析期间不会被修改或归还对象池。

但需要特别注意：

**解析函数线程安全，不代表整个网络消息处理流程线程安全。**

例如：

```text
接收顺序：A → B → C
解析完成：B → C → A
```

即使三个解析过程完全正确，业务消息仍然可能乱序。

所以多线程解析时，仍然需要通过序列号或其他机制保证需要保序的消息按正确顺序进入业务层。

**总结：对于 Google.Protobuf 的纯解析函数，只要解析器支持并发、输入缓冲区不可变、输出对象独立，就可以放心让多个线程同时调用，无须加锁。真正需要额外处理的是缓冲区生命周期、消息顺序以及共享业务状态。**

## 轮次 22ed631b-df35-4a85-bfd3-a5b6ac0e890b

### 用户

我们在进入游戏的主界面后，会默默的 预加载 玩家技能特效 等等 资源， 这样导致 随机性的 游戏卡顿。 有没有办法，避免这种预加载的卡顿

### 助手

有办法，而且对于 Unity MMO，这类问题应该从**预加载调度、资源加载阶段、主线程预算、GPU 上传和 Shader 预热**几个方面一起解决。

你描述的现象很典型：

> 玩家进入主界面后，后台持续预加载技能特效等资源。大多数时候正常，但偶尔某一帧突然卡顿。

这里最容易误判的一点是：

**`AssetBundle.LoadAssetAsync()` 或 `Addressables.LoadAssetAsync()` 不等于整个资源加载过程都不会阻塞主线程。**

Unity 可以把部分 IO、解压和资源加载工作放在后台，但资源对象创建、依赖处理、GPU 资源准备、实例化和 Shader 首次使用等阶段，仍可能给主线程或渲染线程带来压力。

因此，单纯把预加载写成 `async/await`，不能保证完全不卡顿。

## 一、先把卡顿来源拆开

这些是可能发生的成本，不代表每次资源加载都会依次执行全部阶段。单纯加载 Prefab 资产通常不会执行其实例的 Awake。

例如一个技能特效 Prefab，可能包含：

- 多个 ParticleSystem。
- Mesh、Texture、Material。
- 多个 Shader Variant。
- TrailRenderer、Animator、子发射器。
- 自定义脚本和对象池初始化。

即使 Prefab 已经加载进内存，第一次实例化、激活或渲染时，仍可能发生额外开销。

所以要先区分两种预加载：

**资源预加载**：只把资源加载进内存。

**运行时预热**：提前完成实例化、组件初始化、粒子初始化以及部分渲染准备工作。

两者不是一回事。

## 二、我建议采用「分级预加载 + 帧预算调度」

不要在进入主界面后，把所有技能特效一次性提交给 Addressables。

例如：

```csharp
foreach (var key in allEffectKeys)
{
    Addressables.LoadAssetAsync<GameObject>(key);
}
```

即使没有 `await`，这些请求也可能同时进入 Unity 的资源加载系统，产生集中加载和资源集成压力。

更合理的是把预加载拆成三个等级：

| 优先级 | 资源类型 | 策略 |
|--------|--------|--------|
| P0 | 当前角色常用技能、即将使用的特效 | 优先加载，必要时在加载界面完成 |
| P1 | 当前职业其他技能、附近玩家常见特效 | 低并发后台预加载 |
| P2 | 其他职业、稀有技能、大型 Boss 特效 | 空闲时加载或按需加载 |

而且要设置两个独立限制：

- **加载并发限制**：例如同时最多发起 1～2 个大型资源加载请求。
- **主线程工作预算**：每帧只执行少量可控的实例化、预热或缓存初始化工作。

这里有一个重要限制：主线程预算只能控制你自己调度的操作，**无法强制 Unity 内部每个异步加载完成阶段都严格遵守这个预算**。

### 预加载调度器示例

下面是一个控制 Addressables 加载并发的基础实现：

```csharp
using System.Collections.Generic;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;

public sealed class EffectPreloader
{
    private readonly SemaphoreSlim _slots = new(1, 1);

    private readonly Dictionary<string, AsyncOperationHandle<GameObject>>
        _loaded = new();

    // 从 Unity 主线程调用
    public async UniTask PreloadAsync(
        string key,
        CancellationToken token)
    {
        await _slots.WaitAsync(token);

        try
        {
            await UniTask.SwitchToMainThread();

            if (_loaded.ContainsKey(key))
                return;

            var handle =
                Addressables.LoadAssetAsync<GameObject>(key);

            // 不取消底层加载，保证完成后能够清理 handle
            await handle;

            if (handle.Status != AsyncOperationStatus.Succeeded)
            {
                Addressables.Release(handle);
                throw new System.Exception($"Load failed: {key}");
            }

            if (token.IsCancellationRequested)
            {
                Addressables.Release(handle);
                token.ThrowIfCancellationRequested();
            }

            _loaded.Add(key, handle);
        }
        finally
        {
            _slots.Release();
        }
    }
}
```

这是简化示例，假设同一调度器拥有这些 Handle，且释放操作也由主线程统一管理。正式项目还应处理重复请求合并、生命周期结束时的释放、优先级队列和内存预算。

这里的 `SemaphoreSlim(1, 1)` 表示同一时刻只允许一个请求进入加载流程，并不表示 Unity 内部只有一个加载线程。

---

## 三、Prefab 预热要分帧，而不是一次性实例化

假设你需要为 50 种技能特效建立对象池，每种预创建 5 个实例。

总计 250 个特效对象。

如果在一帧中全部 `Instantiate`，很容易出现明显的主线程尖峰。

可以使用一个基于耗时预算的预热器：

```csharp
using System.Collections.Generic;
using System.Diagnostics;
using Cysharp.Threading.Tasks;
using UnityEngine;

public static class EffectWarmup
{
    public static async UniTask WarmupAsync(
        GameObject prefab,
        Transform poolRoot,
        int count,
        double budgetMs = 1.0)
    {
        var stopwatch = new Stopwatch();
        stopwatch.Start();

        for (int i = 0; i < count; i++)
        {
            // 每帧最多安排约 1ms 的主动工作
            if (stopwatch.Elapsed.TotalMilliseconds >= budgetMs)
            {
                await UniTask.Yield(PlayerLoopTiming.Update);
                stopwatch.Restart();
            }

            var instance = Object.Instantiate(prefab, poolRoot);
            instance.SetActive(false);

            // 实际项目中加入对象池
        }
    }
}
```

这个方案可以把 250 次实例化分散到多个帧中。

但要注意：**它无法中断单次 Instantiate。**

如果某个复杂 Prefab 的一次实例化就需要 8 ms，即使设置了 1 ms 的预算，这一帧仍然可能卡顿。

所以，对于特别复杂的技能特效，还需要优化 Prefab 自身，例如减少层级、组件、初始化逻辑和粒子系统数量。

另外，实例化后立即 `SetActive(false)` 并不代表完成了渲染预热。Shader 首次使用、粒子模拟和 GPU 上传等成本可能仍然发生在后续激活或首次绘制时。

---

## 四、Shader 和 GPU 预热要单独处理

这可能是技能特效随机卡顿的重要来源之一。

比如资源已经加载完成，但第一次释放技能时才发生：

```text
首次使用 Shader Variant
        ↓
驱动侧程序准备 / 编译
        ↓
GPU 资源准备
        ↓
首帧渲染卡顿
```

建议针对高频技能建立明确的预热流程：

1. 收集实际会使用的 Shader Variant。
2. 在合适阶段执行 Shader Variant 预热。
3. 对必要的特效进行受控实例化和首次渲染测试。
4. 对频繁出现的技能特效使用有限容量的对象池。

Unity 提供 `ShaderVariantCollection.WarmUp()`，但它可能造成一次性的明显耗时，不能直接在游戏运行过程中随意调用大量预热操作。

即使完成 Shader 预热，也不能保证所有 GPU 驱动状态和资源上传都已完成。具体行为与图形 API、平台和 Unity 版本有关。

对于移动端，建议在加载界面完成最关键的 Shader 预热，其他低优先级资源在运行期间渐进处理。

## 五、如果希望尽量不影响游戏帧率，还要监控运行状态

我会给预加载调度器增加一个动态控制器。

**预加载动态调度示例** 

- 60 FPS
- 30 FPS
当前所选项不可用。

模拟当前帧耗时  ms

> **滑块**
>
> 当前值不可用。
>
> **范围：** 5 至 40
>
> **步长：** 0.5

目标帧预算

# ms

剩余预算

# ms

交互示意：实际调度应使用平滑后的帧耗时、连续超预算帧数及恢复滞回，避免状态频繁切换。暂停新请求不能立即停止已在执行的 Unity 原生加载工作。

这里不要只依赖 `Time.deltaTime`，因为它反映的并不完全是 CPU 主线程耗时。正式项目建议结合 Unity Profiler 的主线程耗时、渲染线程耗时以及目标设备上的 GPU 数据进行判断。

---

## 六、先用 Profiler 找到真正的尖峰

这一步比直接改预加载架构更重要。

| Profiler 现象 | 重点排查 |
|--------|--------|
| `Loading`、资源加载相关标记耗时高 | Bundle 加载、资源集成、依赖关系 |
| `Instantiate`、`Awake`、`OnEnable` 耗时高 | 对象池预创建和组件初始化 |
| `GC.Collect` 耗时高 | 临时分配、对象池和托管堆压力 |
| `Shader.CreateGPUProgram` 等标记耗时高 | Shader Variant 首次使用 |
| `Gfx.WaitForPresentOnGfxThread` 等等待标记较高 | 结合 GPU/渲染线程数据判断，不能仅凭等待标记归因 |
| `UnloadUnusedAssets` 耗时高 | 是否在预加载期间触发了集中卸载 |

建议使用 Unity Profiler 的 Timeline 模式，在真实手机上捕获一次卡顿前后几十帧，查看 Main Thread、Render Thread、Loading Thread 及 GC Alloc。

特别注意，卡顿不一定发生在你调用 `LoadAssetAsync` 的那一帧，也可能发生在请求完成、实例化、首次激活或首次渲染时。

## 七、我会怎么落地到 MMO 项目

我会把预加载分成两套独立机制：

**AssetPreloadScheduler**：负责资源下载、Bundle 加载、Addressables Handle 生命周期、并发数量和内存预算。

**EffectWarmupScheduler**：负责特效实例化、对象池填充、Shader 预热和逐帧工作预算。

这两者不能混在一起。资源加载完成，并不代表特效已经达到首次使用不卡顿的状态。

最终目标也不应该是“所有技能特效都提前加载”，而是：

**保证当前玩家和即将进入视野的高概率技能能够及时使用，同时不让低优先级预加载影响正在运行的游戏。**

我想先确认一个关键点：**你现在的预加载是只调用 `Addressables.LoadAssetAsync` / `AssetBundle.LoadAssetAsync`，还是加载完成后还会 `Instantiate` 特效 Prefab 并放进对象池？**

这两种情况的卡顿来源和优化方案会有很大差别。

## 轮次 3a3b8f2d-579d-4239-873b-c803a2a20c55

### 用户

只预加载部分 特效/prefab， 但是发现 主界面还是会 随机的 卡顿

### 助手

既然你**只预加载特效 Prefab，没有 Instantiate**，那么排查范围可以明显缩小。

这说明卡顿不一定来自特效脚本的 `Awake`、`OnEnable` 或粒子系统初始化，而更值得怀疑的是：

1. **AssetBundle / Addressables 异步加载完成时，Unity 主线程的资源集成开销。**
2. **Prefab 依赖的 Material、Texture、Mesh、Shader 等资源加载。**
3. **多个异步请求同时完成，造成某些帧的加载工作集中。**
4. **后台 IO、解压、内存分配与主线程或渲染线程竞争资源。**
5. **其他系统恰好在预加载期间触发 GC 或资源卸载。**

不过，目前还不能断定卡顿就是预加载造成的。需要先建立时间关联，再确认具体耗时点。

## 一、为什么只加载 Prefab，也可能卡顿？

例如：

```csharp
var handle =
    Addressables.LoadAssetAsync<GameObject>("SkillEffect");

await handle;
```

Unity 并不是简单地把 Prefab 的二进制数据读取到内存。

这是概念性流程，实际执行阶段及线程分工取决于 Unity 版本、资源类型和加载路径。

`LoadAssetAsync` 只能保证调用方不必同步等待整个加载过程，**不能保证所有加载工作都在后台线程，更不能保证某一帧的主线程成本为零**。

即使没有 Instantiate，Unity 仍需要加载并建立 Prefab 资产及其依赖资源。这里的成本和实例化 GameObject 的成本是不同的。

## 二、我建议你先做三个对照实验

这比立即重构资源管理系统更有效。

| 实验 | 操作 | 目的 |
|--------|--------|--------|
| A | 完全关闭主界面预加载 | 确认卡顿是否与预加载相关 |
| B | 开启预加载，但严格串行加载，每次完成后间隔数帧 | 检查并发请求或集中完成是否是诱因 |
| C | 只加载单个特效 Prefab，反复测试冷启动 | 找出是否存在特别昂贵的资源或依赖 |

建议在同一台真机、相同场景和相似运行条件下比较，而不是只在 Editor 里测试。

如果 A 仍然卡顿，说明预加载可能不是主要原因。

如果 B 明显改善，说明限制加载请求并发和节奏值得继续研究。

如果 C 能稳定复现，就应该重点检查该 Prefab 所在 Bundle 的依赖结构、资源大小、Shader 和加载阶段。

## 三、重点排查 Unity 的异步加载集成开销

打开 Unity Profiler 的 Timeline 模式，在卡顿帧查看：

- Main Thread 是否出现 `Loading`、`AssetBundle`、`AsyncUpload` 或其他资源加载相关工作。
- Loading Thread 是否同时执行大量资源加载。
- Render Thread 是否存在资源创建或上传相关开销。
- 是否出现 `GC.Collect`、`UnloadUnusedAssets`。
- 是否有其他脚本在加载完成回调里执行大量同步逻辑。

**不要只看 `LoadAssetAsync` 调用本身耗时。**

例如：

```csharp
var handle = Addressables.LoadAssetAsync<GameObject>(key);

// 调用本身可能很快
await handle;

// 这里不一定卡
// 但 Unity 可能在前面某一帧已经完成大量主线程加载工作
```

即使 `await` 之后只做了一次字典赋值，之前的资源集成过程也可能已经造成帧尖峰。

## 四、两个值得测试的 Unity 加载参数

### 1\. Application.backgroundLoadingPriority

Unity 提供了后台加载优先级控制：

```csharp
Application.backgroundLoadingPriority =
    ThreadPriority.Low;
```

这个设置可以影响 Unity 后台资源加载线程的优先级，以及相关主线程加载集成工作的时间预算。

对于运行中低优先级的特效预加载，可以测试 `Low` 或 `BelowNormal`。

但需要注意：

- 它是全局设置，不是单个 Addressables 请求的优先级。
- 会影响其他使用 Unity 加载系统的操作。
- 低优先级通常意味着加载完成更慢。
- 不能保证彻底消除卡顿。

因此，不建议不加区分地长期设置为最低优先级。可以在低优先级预加载阶段临时调整，并在结束后恢复原值。

### 2\. QualitySettings.asyncUploadTimeSlice

如果卡顿与异步纹理、网格上传有关，可以测试：

```csharp
QualitySettings.asyncUploadTimeSlice = 2;
```

它用于控制异步上传时间片，单位为毫秒。

但它**不是 AssetBundle 加载总时间预算**，也不能限制所有资源创建和主线程集成成本。只有实际使用异步上传路径的资源才可能受益。

如果 Profiler 没有显示相关上传开销，修改它可能没有明显效果。

## 五、预加载节流可以这样做

假设你有 100 个待预加载的特效 Prefab。

不要一次性发起 100 个请求，而是先尝试串行加载，并在请求之间留出帧间隔。

```csharp
public async UniTask PreloadEffectsAsync(
    IReadOnlyList<string> keys,
    CancellationToken token)
{
    await UniTask.SwitchToMainThread(token);

    foreach (var key in keys)
    {
        token.ThrowIfCancellationRequested();

        var handle =
            Addressables.LoadAssetAsync<GameObject>(key);

        // 这里不能随意取消底层请求后丢弃 Handle
        await handle;

        if (handle.Status != AsyncOperationStatus.Succeeded)
        {
            Addressables.Release(handle);
            continue;
        }

        if (token.IsCancellationRequested)
        {
            Addressables.Release(handle);
            token.ThrowIfCancellationRequested();
        }

        // 由资源管理器持有成功的 Handle
        _loadedHandles.Add(handle);

        // 加载完成后间隔 2 帧，再发起下一个
        await UniTask.DelayFrame(2, cancellationToken: token);
    }
}
```

这里 `_loadedHandles` 假设是资源管理器维护的 Handle 容器，生命周期结束时需要逐一 Release。正式实现还要保证异常和取消路径不会遗失已经创建的 Handle。

这个实验的意义在于：**限制同时处于加载过程中的资源数量，减少集中完成的概率。**

但它不能保证完全不卡顿。如果单个 Prefab 的加载集成就会造成 10 ms 的尖峰，串行加载仍然可能卡顿。

---

## 六、我最想确认的一个信息

你说的是进入主界面后随机卡顿，而不是首次释放技能时卡顿。

所以我会优先怀疑 **Prefab 资产加载阶段的主线程工作**，而不是首次渲染的 Shader 编译。但这仍然只是排查假设。

**你现在用的是 `AssetBundle.LoadAssetAsync`，还是 `Addressables.LoadAssetAsync`？**

这两个接口背后的资源调度、依赖管理和加载流程不同。确认这一点后，就可以进一步定位：究竟是 Unity 的原生加载线程、主线程资源集成、Bundle 依赖加载，还是 Addressables 自身的操作调度导致卡顿。

## 轮次 d2640b3d-74dc-47bf-a6e3-e0024445fceb

### 用户

`Addressables.LoadAssetAsync`

### 助手

既然使用的是 `Addressables.LoadAssetAsync<GameObject>()`，而且**只加载 Prefab，不实例化**，那么我建议重点排查 Addressables 底层的 AssetBundle 加载、依赖资源加载，以及 Unity 主线程的资源集成。

有一个关键点：

**Addressables 是异步资源管理系统，不是保证每帧零卡顿的资源加载系统。**

## 一、Addressables.LoadAssetAsync 内部发生了什么？

假设你执行：

```csharp
var handle = Addressables.LoadAssetAsync<GameObject>(
    "SkillEffect_Fire"
);

await handle;
```

大致会经历：

```text
Addressables.LoadAssetAsync
          │
          ▼
定位资源（Resource Location）
          │
          ▼
解析 AssetBundle 依赖关系
          │
          ▼
加载依赖 Bundle
          │
          ▼
加载目标 Bundle
          │
          ▼
AssetBundle.LoadAssetAsync<GameObject>
          │
          ▼
Unity 创建 / 加载 Prefab 资产及其依赖
          │
          ▼
Addressables 完成回调
```

其中，IO、解压和部分资源加载可以由 Unity 后台加载系统处理，但某些资源对象创建、集成和回调仍然需要主线程参与。

另外，Addressables 可能复用已经加载的 Bundle，所以不是每次加载都会重新执行全部阶段。

## 二、一个特别容易忽略的问题：你可能加载了远超预期的依赖

假设：

```text
SkillEffect_Fire.prefab
    ├── Material_Fire
    │     ├── Shader_Effect
    │     └── Texture_Fire
    ├── Mesh_Fire
    └── SubEffect.prefab
```

你以为只是加载一个 Prefab，实际上可能还需要加载多个依赖 Bundle。

更值得注意的是：

**AssetBundle 的打包粒度，会影响实际加载和内存占用。**

例如：

```text
EffectShared.bundle
    ├── 200 个特效共用的 Material
    ├── 100 张 Texture
    └── 其他依赖
```

加载其中一个特效时，可能需要加载整个共享 Bundle 的相关数据和元信息，但不代表 Bundle 中所有 Texture 都会立即创建成 Unity Texture 对象。

因此，不能简单认为一个 Bundle 中有 100 张纹理，就一定会把 100 张纹理全部加载到显存。

不过，如果多个特效都依赖同一个大型共享 Bundle，首次加载时可能出现比较明显的成本。

### 建议检查

使用 Addressables 的 Build Layout Report，查看：

- 一个特效 Prefab 被分配到哪个 Bundle。
- 它依赖哪些 Bundle。
- 是否存在特别大的共享 Bundle。
- 是否有不合理的资源依赖。
- 是否存在资源重复打包。

这比单纯查看 Prefab 文件大小更有价值。

## 三、我建议先测试这两个参数

### 1\. 降低后台加载优先级

```csharp
Application.backgroundLoadingPriority =
    ThreadPriority.Low;
```

这可能减少后台资源加载对游戏运行的干扰，但也会降低加载吞吐。

可以做 A/B 测试：

| 测试 | 设置 |
|--------|--------|
| A | `ThreadPriority.Normal` |
| B | `ThreadPriority.BelowNormal` |
| C | `ThreadPriority.Low` |

观察主线程 P99 帧耗时、最长帧耗时和资源加载总时间，而不只是平均 FPS。

### 2\. 限制同时进行的 Addressables 请求

先测试严格串行加载：

```csharp
foreach (var key in effectKeys)
{
    var handle =
        Addressables.LoadAssetAsync<GameObject>(key);

    await handle;

    // 成功后保存 handle，供资源管理器统一释放

    await UniTask.DelayFrame(2);
}
```

注意，`DelayFrame(2)` 只是把**下一次请求的启动时间**错开，不会把单次加载操作自动切分成多个小任务。

如果串行后卡顿明显减少，说明并发请求集中加载是值得继续排查的方向。

如果没有改善，应该进一步定位单个资源的加载成本。

## 四、一个更有效的实验：找出究竟是哪张 Prefab 导致尖峰

我建议为每次预加载记录：

- 资源 Key。
- 加载开始帧。
- 加载结束帧。
- 加载总耗时。
- 当前正在加载的资源数量。

例如：

```csharp
private static readonly ProfilerMarker PreloadMarker =
    new ProfilerMarker("Game.EffectPreload");

public async UniTask PreloadAsync(string key)
{
    int startFrame = Time.frameCount;
    var watch = Stopwatch.StartNew();

    AsyncOperationHandle<GameObject> handle;

    using (PreloadMarker.Auto())
    {
        handle = Addressables.LoadAssetAsync<GameObject>(key);
    }

    await handle;

    watch.Stop();

    Debug.Log(
        $"Preload: {key}, " +
        $"Frames: {Time.frameCount - startFrame}, " +
        $"Time: {watch.ElapsedMilliseconds}ms"
    );
}
```

这里要注意：

**总加载耗时不是主线程卡顿耗时。**

一个资源加载用了 500 ms，不代表主线程被阻塞 500 ms。

而且 `ProfilerMarker` 只包住了发起请求的同步调用，不会自动覆盖整个异步加载过程。

正确做法是将这些记录与 Unity Profiler Timeline 对齐，找出发生尖峰的具体帧，再查看该帧加载线程、主线程和渲染线程的工作。

## 五、如何进一步降低随机卡顿？

我会按以下顺序处理：

| 优先级 | 优化 | 作用 |
|--------|--------|--------|
| 1 | 关闭预加载做对照 | 确认卡顿是否由预加载引起 |
| 2 | 严格串行加载 | 减少加载工作集中 |
| 3 | 降低后台加载优先级 | 减少加载线程竞争 |
| 4 | 检查 Build Layout | 排查依赖过大和 Bundle 划分 |
| 5 | 分离高频与低频特效 | 减少主界面加载总量 |
| 6 | 分析 Profiler Timeline | 定位无法靠节流解决的单次加载尖峰 |

另外，Addressables 有一些看似异步、实际上可能引起同步等待的调用需要排查，例如：

```csharp
handle.WaitForCompletion();
```

如果项目中的其他系统在预加载期间调用了 `WaitForCompletion()`，可能造成明显的主线程阻塞，甚至等待多个正在进行的资源操作。

所以需要全局检查是否存在这种同步等待，而不只是检查当前预加载代码。

## 六、我的判断

目前已知条件是：

- 使用 `Addressables.LoadAssetAsync<GameObject>()`。
- 预加载的是技能特效 Prefab。
- 不执行 Instantiate。
- 在主界面运行期间偶发卡顿。

我会优先检查 **Addressables 的 Bundle 依赖加载与 Unity 资源集成阶段**，同时排除 GC、同步等待和其他系统造成的尖峰。

我还想确认一个更关键的信息：

**你们的预加载是一次性同时发起几十、几百个 `LoadAssetAsync`，还是一个 `await` 完成之后再加载下一个？**

如果是前者，首先值得调整的是并发调度；如果已经是后者，继续降低并发通常帮助有限，应重点分析单次资源加载和主线程集成成本。

## 轮次 3242129d-8c46-443e-8d10-7126cf67c190

### 用户

在主界面的 地图上， 玩家移动，可能出发 一个随机副本， 但是策划要求 只有一个水波纹动画特效， 这相当于没有加载loading 界面。 所以 就会出现很明显的 特效播放时候，怪物创建出来 卡顿。 针对这种需求，有什么好的办法

### 助手

这个场景本质上是一个 **无 Loading 界面的副本切换问题**。

玩家在主界面地图移动，触发随机副本，策划希望只播放一个水波纹特效，然后怪物出现。技术上却需要在这段时间完成资源加载、怪物创建、组件初始化和渲染准备。

我的建议是：

**不要在水波纹播放期间集中创建怪物，而应该采用「预测预加载 + 隐藏场景准备 + 分帧创建 + 原子显示」的方案。**

这里最重要的不是把 `Instantiate` 改成异步，因为 Unity 的普通 `Instantiate` 仍然需要在主线程执行，而是**把昂贵的初始化工作从玩家可感知的出现时刻移走**。

## 一、先看问题出在哪里

假设水波纹动画持续 0.8 秒，而副本需要：

| 操作 | 假设耗时 |
|--------|--------|
| 加载怪物 Prefab 及依赖 | 120 ms（异步总耗时） |
| 创建 15 个怪物 GameObject | 18 ms 主线程累计 |
| `Awake` / `OnEnable` 初始化 | 12 ms 主线程累计 |
| Animator、粒子、碰撞体初始化 | 8 ms 主线程累计 |
| 首次渲染准备 | 可能出现额外尖峰 |

这里的数字只是用于说明问题，不是 Unity 的固定性能数据。

即使资源加载是异步的，**如果 15 个怪物在同一帧创建，主线程仍可能产生 30 ms 以上的额外工作**。

当前方案：工作集中在水波纹期间

```svg
<svg viewBox="0 0 340 132" width="100%" xmlns="http://www.w3.org/2000/svg"><text x="8" y="20" font-size="11" fill="currentColor">水波纹</text><rect x="78" y="6" width="249" height="22" rx="4" fill="#2563eb" fill-opacity=".7" /><text x="8" y="53" font-size="11" fill="currentColor">加载资源</text><rect x="101" y="39" width="120" height="22" rx="4" fill="#0d9488" fill-opacity=".75" /><text x="8" y="86" font-size="11" fill="currentColor">创建怪物</text><rect x="220" y="72" width="52" height="22" rx="4" fill="#b45309" fill-opacity=".85" /><text x="8" y="119" font-size="11" fill="currentColor">首次显示</text><rect x="272" y="105" width="55" height="22" rx="4" fill="#b91c1c" fill-opacity=".8" /><path d="M272 33 V129" stroke="#b91c1c" stroke-dasharray="3 3" /></svg>
```

创建和首次显示阶段可能产生明显的单帧尖峰。

更合理的流程是：

优化方案：提前准备，最后统一显示

```svg
<svg viewBox="0 0 340 156" width="100%" xmlns="http://www.w3.org/2000/svg"><text x="8" y="19" font-size="11" fill="currentColor">预加载</text><rect x="78" y="5" width="96" height="21" rx="4" fill="#0d9488" fill-opacity=".75" /><text x="8" y="50" font-size="11" fill="currentColor">分帧创建</text><rect x="137" y="36" width="110" height="21" rx="4" fill="#b45309" fill-opacity=".8" /><text x="8" y="81" font-size="11" fill="currentColor">水波纹</text><rect x="215" y="67" width="112" height="21" rx="4" fill="#2563eb" fill-opacity=".75" /><text x="8" y="112" font-size="11" fill="currentColor">统一显示</text><rect x="310" y="98" width="17" height="21" rx="3" fill="#7c3aed" /><text x="8" y="144" font-size="10" fill="currentColor">时间 →</text><path d="M215 1 V126" stroke="#64748b" stroke-dasharray="3 4" /><text x="219" y="139" font-size="9" fill="currentColor">触发</text></svg>
```

示意时间关系：预加载和分帧创建可以在触发前完成；触发后只处理必要的少量工作。

## 二、核心方案：副本预备池（Encounter Preparation Pool）

对于随机副本，我不会等到玩家触发时才开始创建怪物。

我会设计一个独立的 `EncounterPreparationManager`，负责提前准备可能出现的副本资源和怪物实例。

```svg
<svg viewBox="0 0 340 306" width="100%" xmlns="http://www.w3.org/2000/svg"><rect x="45" y="8" width="250" height="43" rx="7" fill="#64748b" fill-opacity=".1" stroke="#64748b" /><text x="170" y="25" text-anchor="middle" font-size="12" font-weight="bold" fill="currentColor">玩家在主界面地图移动</text><text x="170" y="40" text-anchor="middle" font-size="10" fill="currentColor">根据区域 / 触发概率预测候选副本</text><path d="M170 51 V69" stroke="#64748b" stroke-width="1.5" /><rect x="45" y="69" width="250" height="43" rx="7" fill="#0d9488" fill-opacity=".1" stroke="#0d9488" /><text x="170" y="86" text-anchor="middle" font-size="12" font-weight="bold" fill="currentColor">Addressables 资源预加载</text><text x="170" y="101" text-anchor="middle" font-size="10" fill="currentColor">怪物 Prefab / 材质 / 动画依赖</text><path d="M170 112 V130" stroke="#64748b" stroke-width="1.5" /><rect x="45" y="130" width="250" height="43" rx="7" fill="#b45309" fill-opacity=".1" stroke="#b45309" /><text x="170" y="147" text-anchor="middle" font-size="12" font-weight="bold" fill="currentColor">分帧创建怪物实例</text><text x="170" y="162" text-anchor="middle" font-size="10" fill="currentColor">初始化 / 放入隐藏的预备池</text><path d="M170 173 V191" stroke="#64748b" stroke-width="1.5" /><rect x="45" y="191" width="250" height="43" rx="7" fill="#2563eb" fill-opacity=".1" stroke="#2563eb" /><text x="170" y="208" text-anchor="middle" font-size="12" font-weight="bold" fill="currentColor">触发随机副本 + 播放水波纹</text><text x="170" y="223" text-anchor="middle" font-size="10" fill="currentColor">复用准备好的怪物</text><path d="M170 234 V252" stroke="#64748b" stroke-width="1.5" /><rect x="45" y="252" width="250" height="43" rx="7" fill="#7c3aed" fill-opacity=".1" stroke="#7c3aed" /><text x="170" y="269" text-anchor="middle" font-size="12" font-weight="bold" fill="currentColor">统一进入战斗状态</text><text x="170" y="284" text-anchor="middle" font-size="10" fill="currentColor">尽量避免触发时批量 Instantiate</text></svg>
```

### 1\. 预测不需要精确到具体副本

假设某个地图区域可能触发三个随机副本：

| 副本 | 资源特点 | 预加载策略 |
|--------|--------|--------|
| 野狼袭击 | 普通野狼、通用攻击特效 | 预创建少量野狼 |
| 哥布林伏击 | 哥布林、弓箭特效 | 预加载 Prefab，按预算预创建 |
| 精英魔物 | 大型精英怪、特殊技能 | 优先加载资源，视内存预算决定是否预创建 |

不必提前完整创建三个副本。

更好的方式是**按怪物类型准备可复用实例**，而不是为每个副本准备一整套场景。

这样，同一种怪物可以服务多个副本，避免重复占用内存。

## 三、分帧创建，但要注意 Awake 和 OnEnable

例如：

```csharp
public async UniTask PrepareMonstersAsync(
    GameObject prefab,
    Transform poolRoot,
    int count,
    CancellationToken token)
{
    await UniTask.SwitchToMainThread(token);

    // poolRoot 应提前处于非激活状态
    for (int i = 0; i < count; i++)
    {
        token.ThrowIfCancellationRequested();

        var monster = Object.Instantiate(prefab, poolRoot);

        // 根据项目的生命周期约定进行初始化
        monster.SetActive(false);

        _monsterPool.Push(monster);

        // 每帧最多创建一个
        await UniTask.Yield(PlayerLoopTiming.Update, token);
    }
}
```

不过，**每帧创建一个，不等于每帧一定不卡顿**。如果单个怪物 Prefab 实例化就需要 10 ms，仍然会造成尖峰。

而且这里存在一个重要的 Unity 生命周期问题：

- 如果实例化时 GameObject 处于激活层级，`Awake` 和 `OnEnable` 可能已经执行，之后 `SetActive(false)` 并不能消除这部分成本。
- 如果实例化到非激活父节点下，可以推迟部分生命周期工作，但也可能把成本留到之后激活时。
- 即使已经执行过 `Awake`，重新激活时仍会执行 `OnEnable`。

因此，我更推荐将怪物初始化拆成明确的三个阶段：

```csharp
public class MonsterView : MonoBehaviour
{
    // 创建时执行一次
    public void InitializeOnce()
    {
        // 缓存组件、建立不变的数据结构
    }

    // 每次从对象池取出时执行
    public void PrepareSpawn(MonsterSpawnData data)
    {
        // 设置位置、血量、表现参数
        // 尽量不进行大规模分配
    }

    // 真正进入战斗时执行
    public void EnterBattle()
    {
        // 开始 AI、动画、技能逻辑
    }
}
```

关键是把昂贵的工作从 `Awake`、`OnEnable` 和首次 `Update` 中拆出来，让它们能够被提前执行或分帧调度。

## 四、比对象池更重要：把“创建”和“显示”分开

假设随机副本需要 20 个怪物。

不建议：

```csharp
// 水波纹结束
for (int i = 0; i < 20; i++)
{
    Instantiate(monsterPrefab);
}
```

建议提前完成：

```text
准备阶段：
    创建怪物实例
    初始化组件引用
    绑定配置
    初始化动画参数
    准备 AI 状态
    放入预备池

触发阶段：
    播放水波纹
    设置出生位置
    取出预备实例
    激活必要的表现
    进入战斗
```

但是，**最后统一显示也不意味着必须在同一帧调用 20 次 `SetActive(true)`**。

如果激活过程很重，仍然可能卡顿。

更进一步，可以采用：

**提前激活但隐藏渲染，等水波纹结束再显示。**

例如，怪物对象已经完成必要的初始化，只是暂时关闭 Renderer，或者由统一的表现系统控制可见性。

这种方案可以避免部分 `OnEnable` 集中执行，但需要保证隐藏期间不会运行不必要的 AI、动画、粒子和物理逻辑。

同时要注意，关闭 Renderer 并不等于完成 Shader 首次渲染准备。隐藏对象的首次可见帧仍可能产生 GPU 相关开销。

## 五、策划要求只有一个水波纹，怎么办？

这里我会给策划一个技术上可控的方案：

**水波纹是视觉过渡，不是强制固定时长的加载窗口。**

例如：

水波纹和准备状态的协调

- 已准备完成
- 准备稍慢
- 准备失败
当前所选项不可用。

触发副本

播放水波纹

过渡动画持续，例如 0.8 秒

这里有一个不可回避的约束：

如果策划同时要求：

- 随机副本无法提前确定。
- 所有怪物都必须在触发后才创建。
- 水波纹固定 0.8 秒，不能延长。
- 任何设备都不能卡顿。
- 不允许额外内存用于预创建。

那么这些要求**无法保证同时满足**。

必须至少允许提前准备、延长过渡、降低副本复杂度或增加内存预算中的一种。

## 六、我会额外加入“副本就绪状态机”

```text
NotPrepared
     ↓
LoadingAssets
     ↓
CreatingInstances
     ↓
Initializing
     ↓
Ready
     ↓
Activated
```

只有进入 `Ready` 的副本，才能走最快的无 Loading 切换路径。

如果玩家触发时还没 Ready：

- 优先继续当前水波纹过渡。
- 如果允许，等待后台准备完成。
- 如果超出可接受时间，选择降级方案。
- 避免突然在一帧里同步创建所有怪物。

对于随机副本，还可以由服务器提前确定或下发候选副本信息，但需要保证不会泄露不该提前知道的游戏结果，也不能依赖预测一定命中。

## 七、如何验证优化是否有效？

不要只测副本总加载时间，而是记录：

| 指标 | 关注点 |
|--------|--------|
| 副本触发前 Ready 命中率 | 有多少副本已准备好 |
| 触发到怪物可见的延迟 | 玩家是否感知到等待 |
| 最大单帧耗时 | 是否出现明显卡顿 |
| Instantiate 耗时 | 怪物创建是否仍是瓶颈 |
| Awake / OnEnable 耗时 | 初始化是否集中发生 |
| 首次渲染耗时 | Shader、GPU 资源是否产生尖峰 |
| 预备池内存占用 | 是否用过多内存换取流畅度 |

特别建议在低端 Android 真机上测试。高端开发机上能够流畅创建 20 个怪物，不代表低端手机也可以。

---

## 我的建议

对于这个需求，我会优先采用：

**常用怪物对象池 + 地图区域预测预加载 + 分帧初始化 + 水波纹作为就绪屏障。**

其中最关键的是**把怪物创建和初始化提前到触发副本之前**，而不是在水波纹期间拼命优化 `Instantiate`。

最后需要确认一个会直接影响架构的问题：

**随机副本触发后，是在当前地图场景中直接刷出怪物，还是需要切换到一个新的 Unity Scene？**

如果只是当前场景刷怪，重点是怪物预备池和激活成本；如果涉及真正的 Scene 切换，还需要进一步处理 `LoadSceneAsync`、场景激活以及场景资源生命周期。

