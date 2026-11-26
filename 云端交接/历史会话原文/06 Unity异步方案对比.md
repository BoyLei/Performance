# Unity异步方案对比

会话 ID：`6af966d4-d3d4-83ec-85c9-2e9753187762`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 57490826-3353-4b5e-96d6-66b53832d39f

### 用户

以前我经历的 几个unity 项目， 异步逻辑都是采用 callback 的方式， 现在下一个中大型 mmo项目， 你觉得是 采用 unitask 还是 继续采用 callback 的方式

### 助手

对于一个准备从零搭建的**中大型 Unity MMO 项目，我更推荐采用 UniTask 作为业务异步逻辑的主要方案，同时保留 Callback 作为底层事件通知和部分异步接口的实现方式。**

但我不建议把项目里所有 Callback 都改成 UniTask。

原因不是 UniTask 语法更简洁，而是中大型 MMO 的异步系统会涉及大量**生命周期管理、取消、并发、超时、错误传播和资源释放**。这些问题才是技术选型的核心。

## 一、先明确：UniTask 和 Callback 并不是完全对立的

Callback 是一种异步完成通知机制，而 UniTask 是基于 C\# `async/await` 的异步编程方案。

例如 MMO 中常见的登录流程：

Callback 模式

UniTask 模式

两者都能实现同样的功能，区别在于如何组织复杂的异步业务。

## 二、对 MMO 项目，我会这样选择

| 系统模块 | 推荐方案 | 原因 |
|--------|--------|--------|
| 登录、选角、进入游戏 | UniTask | 多步骤串行、异常和取消 |
| 场景切换、加载界面 | UniTask | 进度、取消、生命周期 |
| AssetBundle / Addressables 加载 | UniTask + 引用计数 | 异步操作与资源所有权分离 |
| UI 打开、关闭、动画等待 | UniTask | 方便表达流程 |
| 网络 Socket 收包 | Callback / 消息队列 | 持续事件流，不是单次结果 |
| 网络请求并等待响应 | UniTask | 请求与响应一一对应 |
| 战斗技能事件 | Callback / 事件系统 | 高频、持续通知 |
| 每帧战斗逻辑 | 同步 Update / Tick | 不需要为每个实体创建异步任务 |
| 定时器 | 自定义 Timer | 大量高频计时可控性更好 |
| SDK 登录、支付回调 | Callback + UniTask 适配 | 外部 SDK 通常以回调为基础 |

**核心原则：**

- 一次性、有明确完成结果的操作：优先 UniTask。
- 持续发生的事件通知：优先 Callback / Event。
- 高频、确定性的游戏循环：优先同步逻辑。
- 底层原生 API：保留其适合的实现方式，必要时向上提供 UniTask 封装。

## 三、UniTask 在 MMO 中真正的优势

### 1\. 复杂业务流程的可维护性

假设进入游戏需要完成：

1. 建立连接。
2. 登录认证。
3. 获取角色数据。
4. 加载场景。
5. 加载玩家角色。
6. 等待场景准备。
7. 通知服务器进入完成。

Callback 方案随着分支增多，会出现大量状态管理、错误回调和取消判断。

UniTask 则可以这样写：

```csharp
public async UniTask EnterGameAsync(
    CancellationToken token)
{
    await ConnectAsync(token);
    await LoginAsync(token);
    await LoadPlayerDataAsync(token);

    await LoadSceneAsync(token);
    await LoadPlayerAsync(token);

    await WaitSceneReadyAsync(token);
    await NotifyEnterCompleteAsync(token);
}
```

你可以使用 `try/catch/finally` 统一处理失败、取消和清理，而不必让每一层 Callback 都传递错误。

不过这里有个非常重要的问题：

**UniTask 让异步代码看起来像同步代码，但它并不会自动解决业务状态一致性。**

例如进入场景过程中取消，可能需要卸载部分资源、撤销待处理请求、恢复 UI 状态。这些都需要业务层设计。

### 2\. 异步任务生命周期管理

我认为这是中大型 MMO 最值得重视的问题。

比如玩家点击进入副本：

```text
开始加载副本
    ↓
异步加载 AssetBundle
    ↓
异步实例化场景对象
    ↓
异步初始化角色
```

如果中途玩家退出游戏、断线、切换账号，旧任务怎么办？

UniTask 可以利用 `CancellationToken` 将取消意图向下传递：

```csharp
private CancellationTokenSource _cts;

public async UniTask LoadDungeonAsync()
{
    _cts = new CancellationTokenSource();

    try
    {
        await LoadSceneAsync(_cts.Token);
        await LoadCharactersAsync(_cts.Token);
    }
    catch (OperationCanceledException)
    {
        // 取消后的业务处理
    }
    finally
    {
        _cts.Dispose();
        _cts = null;
    }
}
```

这只是简化示例。正式项目还需要防止重复启动导致 `_cts` 被覆盖，并在退出流程中取消任务。

尤其要注意：

- `CancellationToken` 不保证底层 Unity API 真正停止执行。
- 取消等待不代表取消 AssetBundle 或 Addressables 的底层加载。
- 取消后仍然要考虑已经获取的资源如何释放。
- 任务完成与 UI、GameObject 的生命周期需要明确绑定。

因此我建议设计一套统一的异步作用域管理机制，而不是在每个业务模块里随意创建 `CancellationTokenSource`。

### 3\. 网络请求可以非常自然地封装

对于 MMO，我建议把网络层分成两种模型。

```svg
<svg viewBox="0 0 330 212" width="100%" xmlns="http://www.w3.org/2000/svg"><rect x="110" y="5" width="110" height="32" rx="6" fill="#7D92AA" fill-opacity=".18" stroke="#8294A6" /><text x="165" y="25" text-anchor="middle" font-size="12" fill="currentColor">Socket 接收</text><path d="M165 37 V53 M80 53 H250 M80 53 V70 M250 53 V70" fill="none" stroke="#8294A6" stroke-width="1.5" /><rect x="12" y="70" width="136" height="46" rx="6" fill="#647FA4" fill-opacity=".13" stroke="#8294A6" /><text x="80" y="88" text-anchor="middle" font-size="11" fill="currentColor">服务器主动推送</text><text x="80" y="103" text-anchor="middle" font-size="10" fill="#8294A6">事件 / Callback</text><rect x="182" y="70" width="136" height="46" rx="6" fill="#229D79" fill-opacity=".12" stroke="#229D79" /><text x="250" y="88" text-anchor="middle" font-size="11" fill="currentColor">请求响应匹配</text><text x="250" y="103" text-anchor="middle" font-size="10" fill="#229D79">UniTask</text><path d="M80 116 V142 M250 116 V142" stroke="#8294A6" stroke-width="1.5" /><rect x="12" y="142" width="136" height="55" rx="6" fill="#647FA4" fill-opacity=".07" stroke="#8294A6" stroke-dasharray="4 3" /><text x="80" y="162" text-anchor="middle" font-size="10" fill="currentColor">战斗广播 / 状态同步</text><text x="80" y="180" text-anchor="middle" font-size="10" fill="currentColor">事件分发器</text><rect x="182" y="142" width="136" height="55" rx="6" fill="#229D79" fill-opacity=".06" stroke="#229D79" stroke-dasharray="4 3" /><text x="250" y="162" text-anchor="middle" font-size="10" fill="currentColor">背包操作 / 登录</text><text x="250" y="180" text-anchor="middle" font-size="10" fill="currentColor">await Response</text></svg>
```

比如业务层：

```csharp
var response = await network.RequestAsync<
    BuyItemRequest,
    BuyItemResponse>(
        request,
        cancellationToken);
```

网络底层仍然可以采用 Socket 回调、双队列交换和主线程分发。

收到协议时：

- 如果属于某个等待中的 RequestId，则完成对应的 UniTask。
- 如果是服务器主动推送，则进入事件分发系统。

这样既保留网络层的高性能实现，也让业务层更容易维护。

## 四、UniTask 的 GC 和性能问题

这也是我不建议全项目无差别使用 UniTask 的主要原因。

| 对比 | Callback | UniTask |
|--------|--------|--------|
| 最简单的完成通知 | 可以零分配 | 可以零分配 |
| 捕获局部变量的 Lambda | 通常产生闭包分配 | 不依赖 Lambda |
| 异步状态管理 | 需要自行维护 | 编译器生成状态机 |
| 异常传播 | 需要显式设计 | 支持 async 异常传播 |
| 取消传播 | 需要自行设计 | 支持 CancellationToken |
| 高频调用 | 可优化到极低开销 | 需避免不必要的异步任务 |
| 多步骤流程 | 复杂度容易增加 | 更容易维护 |

需要纠正一个常见误区：

**UniTask 并不等于完全零 GC。**

UniTask 是值类型，通常能避免标准 `Task` 的部分堆分配，但以下情况仍可能产生 GC：

- 异步状态机需要额外的运行时对象或任务源。
- 使用捕获变量的 Lambda。
- 创建 `CancellationTokenSource`。
- 异常及堆栈处理。
- `WhenAll` 等组合操作的内部存储。
- 第三方 API 或业务代码本身分配内存。

另外，UniTask 默认也不是一个可以随意多次 `await` 的任务对象，某些操作必须使用 `UniTaskCompletionSource` 或其他专门机制管理。

所以我不会在每个角色的每帧逻辑、技能 Tick 或大量实体的高频状态更新中滥用 UniTask。

## 五、我会为 MMO 制定的架构规范

我建议把异步系统划分为三个层次。

**业务层 — UniTask**

登录、场景切换、UI、任务流程、网络请求

**异步基础设施层**

任务调度、取消、超时、生命周期、异常监控

**底层执行层 — Callback / Event / Native API**

Socket、资源加载、Unity AsyncOperation、SDK

团队层面我还会明确几条规则：

1. 业务异步 API 默认返回 `UniTask` 或 `UniTask<T>`。
2. `async void` 原则上禁止，必须使用即发即弃时，采用明确的异常处理策略。
3. 所有可能长时间运行的业务操作必须支持取消。
4. 禁止在不明确任务所有权的情况下随意 `.Forget()`。
5. 每个 UI、场景和业务模块都要明确自己的异步生命周期。
6. 资源加载任务的取消和资源释放必须分开设计。
7. 网络 Request 必须具备超时、断线失败处理和请求关联机制。
8. 高频路径必须经过 Profiler 验证，不能仅凭 UniTask 的低分配特性判断性能。

## 六、最终建议

如果这是一个要长期维护、多人协作、持续迭代三到五年的中大型 MMO，我会选择：

**业务异步流程** (UniTask 优先)

**底层异步通知** Callback / Event

**高频游戏逻辑** 同步 Tick / 自定义调度

但是在正式确定技术方案之前，我认为还有一个比 GC 更值得深入讨论的问题：

**UniTask 的取消、异常和生命周期管理，是否真的比 Callback 更容易做到正确？**

例如一个 MMO 场景正在异步加载，玩家突然断线并重新登录，旧的加载任务还没有完成，而新的加载任务已经开始。这时即便你使用 UniTask，也可能出现旧任务覆盖新场景、重复实例化角色、资源引用计数错误等问题。

这类问题涉及异步任务的所有权、竞态条件、版本号校验和取消语义，才是真正决定 MMO 异步框架设计质量的关键。

我建议下一步重点研究 **UniTask 在 MMO 中的异步生命周期架构**，尤其是场景切换、UI 关闭、网络断线和资源加载四种场景下，如何保证异步任务不会产生竞态、泄漏或错误回调。

