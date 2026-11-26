# FixedUpdate 时间执行

会话 ID：`6a313a24-4428-83ea-ac37-aa355d88007c`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 37412719-bded-4f4d-8ecd-3180fa4e5b76

### 用户

unity FixedUpdate 就一定是固定时间执行吗。？  如果gc 卡顿了

### 助手

不是。**`FixedUpdate` 的设计目标是固定时间步长（Fixed Timestep），但实际执行时间并不一定固定。** 如果发生 GC、主线程卡顿、加载资源等情况，`FixedUpdate` 的执行会受到影响。

具体分几种情况来看。

---

## 正常情况下

假设：

```text
Time.fixedDeltaTime = 0.02f; // 50 FPS Physics
```

Unity 希望每 **20ms** 模拟一次物理。

例如：

```
0ms
20ms
40ms
60ms
80ms
...
```

如果游戏一直稳定运行，那么：

```
Update
FixedUpdate
Update
FixedUpdate
...
```

看起来就是固定时间执行。

---

## 如果发生 GC 卡顿

例如：

```
0ms     FixedUpdate
20ms    FixedUpdate

40ms ---------------------- GC 停顿 -------------------- 140ms

恢复运行
```

GC 卡了 **100ms**。

Unity 会发现：

```
本来应该执行：

60ms
80ms
100ms
120ms
140ms
```

这些物理步都没有执行。

于是恢复之后，它会尝试**补执行（Catch Up）**。

可能变成：

```
FixedUpdate
FixedUpdate
FixedUpdate
FixedUpdate
FixedUpdate

Update
```

也就是说：

**这一帧里面连续执行很多次 `FixedUpdate`。**

所以：

- **FixedUpdate 不是每隔20ms真实时间执行一次**
- **而是保证模拟时间不会丢。**

---

## 举个例子

假设：

```
fixedDeltaTime = 0.02
```

GC 卡了：

```
120ms
```

恢复以后：

```
120 / 20 = 6
```

Unity 可能这一帧连续执行：

```
FixedUpdate()
FixedUpdate()
FixedUpdate()
FixedUpdate()
FixedUpdate()
FixedUpdate()

Update()
Render()
```

所以你有时候会看到：

```
FixedUpdate
FixedUpdate
FixedUpdate
Update
```

这种情况是正常的。

---

## 有没有可能不补？

有。

Unity 有一个参数：

```text
Time.maximumDeltaTime
```

默认大约：

```
0.333 秒
```

意思是：

> 一帧最多补这么长时间的物理。

例如：

```
GC 卡了 2 秒
```

理论上：

```
2 / 0.02 = 100 次 FixedUpdate
```

Unity不会执行100次。

它会限制：

```
最多补
0.333 / 0.02 ≈ 16 次
```

剩下的时间直接丢弃。

否则游戏可能一直在补物理，画面几秒都刷新不了。

---

## FixedUpdate 里的 deltaTime 是多少？

注意：

```csharp
void FixedUpdate()
{
    Debug.Log(Time.deltaTime);
}
```

这里打印的：

```
0.02
```

即使：

现实世界已经过去：

```
100ms
```

它依然是：

```
0.02
```

因为：

```
Time.deltaTime
==
Time.fixedDeltaTime
```

在 `FixedUpdate` 中表示的是**一次物理模拟的时间步长**，而不是现实经过的时间。

---

## GC 会影响物理吗？

会。

GC 停顿期间：

- Update 不执行
- FixedUpdate 不执行
- Physics 不模拟
- Render 不刷新

整个主线程都会暂停。

恢复以后：

```
连续多个 FixedUpdate
↓

Physics 连续模拟

↓

Update

↓

Render
```

因此玩家看到的效果往往是：

```
人物突然跳了一截
```

并不是物体瞬移，而是中间几次物理模拟都在同一帧完成了。

---

## 面试中常见的一句话总结

可以这样回答：

> **`FixedUpdate` 并不是按真实时间绝对固定触发，而是按固定时间步长进行逻辑模拟。若主线程因 GC、资源加载等原因发生卡顿，Unity 会在恢复后尽可能补执行多个 `FixedUpdate` 来追赶模拟时间；如果累计时间超过 `Time.maximumDeltaTime` 的限制，则会放弃部分补偿，以避免“死亡螺旋”（Spiral of Death），保证游戏仍能继续运行。**

这是理解 Unity 时间系统和物理更新机制的关键点。

## 轮次 388c6450-1736-4926-8523-0d2f27cfb14b

### 用户

如果节点 destroy 的时候没有StopCoroutine或StopAllCoroutines，会有什么后果

### 助手

这是一个很容易误解的点。**对于挂在 `MonoBehaviour` 上的协程，`GameObject` 或组件被销毁时，Unity 会自动停止这些协程。** 一般来说，不需要在 `OnDestroy()` 里手动调用 `StopCoroutine()` 或 `StopAllCoroutines()`。

## 情况一：GameObject 被 Destroy（最常见）

例如：

```csharp
public class Test : MonoBehaviour
{
    IEnumerator Start()
    {
        while (true)
        {
            Debug.Log("Running");
            yield return new WaitForSeconds(1);
        }
    }
}
```

执行：

```csharp
Destroy(gameObject);
```

结果：

- 当前 `MonoBehaviour` 被销毁
- 所有由这个 `MonoBehaviour` 启动的协程自动停止
- 不会继续打印 `"Running"`
- 不会因为没调用 `StopCoroutine()` 而内存泄漏

---

## 情况二：只 Destroy Component

例如：

```csharp
Destroy(this);
```

也一样。

这个 `MonoBehaviour` 被销毁后：

- 它启动的协程全部停止。

---

## 情况三：GameObject SetActive(false)

例如：

```csharp
gameObject.SetActive(false);
```

这里很多人容易记错。

对于挂在该对象上的 `MonoBehaviour`：

- `Update()` 不再执行
- `FixedUpdate()` 不再执行
- **协程也会停止继续执行**（不会再恢复，除非重新启动新的协程）

也就是说：

```csharp
StartCoroutine(Test());
gameObject.SetActive(false);
```

之后：

```text
Test() 不会继续往下执行。
```

重新：

```csharp
gameObject.SetActive(true);
```

**之前的协程不会自动恢复**，需要重新 `StartCoroutine()`。

---

## 情况四：MonoBehaviour.enabled = false

例如：

```csharp
enabled = false;
```

这个行为和 `SetActive(false)` 不一样。

组件禁用后：

- `Update()` 停止
- `FixedUpdate()` 停止
- **已经启动的协程仍然会继续运行**

例如：

```csharp
IEnumerator Foo()
{
    while (true)
    {
        Debug.Log("Coroutine");
        yield return null;
    }
}
```

```csharp
enabled = false;
```

输出仍然会继续：

```text
Coroutine
Coroutine
Coroutine
```

所以：

> **禁用脚本不会自动停止协程。**

---

## 那什么时候需要 StopCoroutine？

主要有以下几种情况。

### 1. 对象池

例如：

```csharp
gameObject.SetActive(false);
```

如果你的项目或 Unity 版本下协程不会按你的预期结束，或者为了明确控制生命周期，通常会在回收对象时主动停止：

```csharp
StopAllCoroutines();
```

这样对象重新取出时，不会有旧协程遗留逻辑。

---

### 2. 切换技能

例如：

```csharp
AttackCoroutine();
```

玩家切换武器：

```csharp
StopCoroutine(attackRoutine);
```

否则旧攻击逻辑还会继续执行。

---

### 3. UI 动画

例如：

```csharp
FadeIn();
```

玩家关闭窗口：

```csharp
StopAllCoroutines();
```

避免动画继续修改已经关闭的 UI。

---

## 有没有资源泄漏？

如果对象已经 `Destroy()`：

```csharp
Destroy(gameObject);
```

Unity 会自动停止该对象上的协程，因此**通常不会因为没有调用 `StopCoroutine()` 而导致协程本身泄漏**。

真正需要注意的是协程内部引用的资源。例如：

```csharp
IEnumerator Load()
{
    var request = UnityWebRequest.Get(url);
    yield return request.SendWebRequest();
}
```

如果希望在对象销毁时取消下载，仅仅停止协程并不一定会终止底层请求，可能还需要根据具体 API 主动取消或释放相关资源。

---

## 总结

| 情况 | 协程是否继续运行 |
|------|----------------|
| `Destroy(gameObject)` | ❌ 自动停止 |
| `Destroy(this)` | ❌ 自动停止 |
| `gameObject.SetActive(false)` | ❌ 停止，不会自动恢复 |
| `enabled = false` | ✅ **继续运行** |
| 场景卸载导致对象销毁 | ❌ 自动停止 |

因此，如果对象会被 **`Destroy()`**，通常不需要专门调用 `StopCoroutine()` 或 `StopAllCoroutines()`；而在对象池、状态切换、UI 动画等需要提前结束异步流程的场景，主动停止协程会让生命周期更明确，也更容易避免逻辑错误。

## 轮次 0c92a39b-efc5-4b2d-9d5f-993eb524c223

### 用户

上面的网络请求如何在协程停止的情况终止

### 助手

这是协程取消里一个比较重要的点：

> **`StopCoroutine()` 只是停止协程的执行流程，并不会自动取消协程里面启动的异步操作。**

例如：

```csharp
IEnumerator Download()
{
    UnityWebRequest request =
        UnityWebRequest.Get(url);

    yield return request.SendWebRequest();

    Debug.Log("Done");
}
```

如果执行：

```csharp
StopCoroutine(downloadCoroutine);
```

发生的是：

- ✅ 协程结束
- ❌ `UnityWebRequest` **不会自动取消**
- 网络请求仍然会继续下载
- 下载完成后资源才会释放

所以很多人以为 StopCoroutine 就取消下载，其实不是。

---

## 正确做法一：主动 Abort()

需要保留 request 的引用。

```csharp
private UnityWebRequest request;
private Coroutine downloadCoroutine;

IEnumerator Download()
{
    request = UnityWebRequest.Get(url);

    yield return request.SendWebRequest();

    if (request.result == UnityWebRequest.Result.Success)
    {
        Debug.Log(request.downloadHandler.text);
    }

    request.Dispose();
    request = null;
}
```

对象销毁时：

```csharp
void OnDestroy()
{
    if (request != null)
    {
        request.Abort();   // 终止请求
        request.Dispose(); // 释放资源
        request = null;
    }

    StopAllCoroutines();
}
```

这样网络连接会立即关闭。

---

## 正确做法二：using

更推荐写成：

```csharp
IEnumerator Download()
{
    using (var request = UnityWebRequest.Get(url))
    {
        currentRequest = request;

        yield return request.SendWebRequest();

        currentRequest = null;

        if (request.result == UnityWebRequest.Result.Success)
        {
            Debug.Log(request.downloadHandler.text);
        }
    }
}
```

然后：

```csharp
void OnDestroy()
{
    currentRequest?.Abort();
}
```

即使协程正常结束，`using` 也会自动调用 `Dispose()`。

---

## Addressables / AssetBundle 也是一样

例如：

```csharp
var handle = Addressables.LoadAssetAsync<GameObject>(key);

yield return handle;
```

如果：

```csharp
StopCoroutine();
```

并不会停止：

```text
LoadAssetAsync
```

仍然会继续加载。

需要：

```csharp
Addressables.Release(handle);
```

或者对应的取消 API（如果支持）。

---

## AsyncOperation 呢？

例如：

```csharp
AsyncOperation op = SceneManager.LoadSceneAsync(...);

yield return op;
```

调用：

```csharp
StopCoroutine();
```

也不会取消：

```text
LoadSceneAsync
```

Unity 目前没有取消场景加载的 API（除了某些 Addressables 场景加载或自定义加载流程）。

---

## 一个比较通用的取消模式

实际项目里，可以把所有可取消的异步对象统一管理：

```csharp
private UnityWebRequest currentRequest;

void OnDestroy()
{
    currentRequest?.Abort();
    StopAllCoroutines();
}
```

如果以后换成：

- UnityWebRequest
- Addressables
- AssetBundle
- 自己的 TCP 下载
- WebSocket

都可以在 `OnDestroy()` 或对象回收时统一取消底层任务，而不是仅仅停止协程。

---

### 一句话总结

**协程只是"等待者"，不是"执行者"。**

- `StopCoroutine()`：停止等待，不会停止底层异步操作。
- `UnityWebRequest`：调用 `Abort()` 取消请求，再 `Dispose()` 释放资源。
- `Addressables`、`AssetBundle`、场景加载等也需要调用各自提供的取消或释放接口，不能依赖 `StopCoroutine()`。

## 轮次 7ad10bc9-a463-49ab-937c-a413d936b409

### 用户

InvokeRepeating

### 助手

`InvokeRepeating` 是 Unity 提供的一个**定时重复调用方法**，适合做简单的定时任务，但功能比较有限。

## 基本用法

```csharp
void Start()
{
    InvokeRepeating(nameof(PrintLog), 1f, 0.5f);
}

void PrintLog()
{
    Debug.Log("Hello");
}
```

参数含义：

```csharp
InvokeRepeating(
    "PrintLog", // 方法名
    1f,         // 延迟1秒开始
    0.5f        // 每0.5秒执行一次
);
```

执行时间类似：

```text
0s   Start

1.0s PrintLog

1.5s PrintLog

2.0s PrintLog

2.5s PrintLog
...
```

---

## 停止调用

停止某一个：

```csharp
CancelInvoke(nameof(PrintLog));
```

停止当前 `MonoBehaviour` 上所有 `Invoke`：

```csharp
CancelInvoke();
```

---

## Destroy 时会怎样？

如果：

```csharp
Destroy(gameObject);
```

或者

```csharp
Destroy(this);
```

Unity 会自动取消所有 `Invoke` 和 `InvokeRepeating`。

一般不用：

```csharp
OnDestroy()
{
    CancelInvoke();
}
```

虽然写了也没有问题。

---

## SetActive(false) 呢？

```csharp
gameObject.SetActive(false);
```

不会继续触发 `InvokeRepeating`。

重新：

```csharp
gameObject.SetActive(true);
```

**之前的 `InvokeRepeating` 不会自动恢复。**

如果需要继续：

```csharp
InvokeRepeating(...);
```

需要重新调用。

---

## enabled = false 呢？

这一点和协程不同。

```csharp
enabled = false;
```

**`InvokeRepeating` 也不会继续执行。**

例如：

```csharp
InvokeRepeating(nameof(Test), 0, 1);

enabled = false;
```

之后：

```text
Test()
```

不会再调用。

重新：

```csharp
enabled = true;
```

也不会恢复，需要再次调用：

```csharp
InvokeRepeating(...);
```

---

## 会受到 GC 影响吗？

会。

例如：

```text
每1秒执行一次
```

如果：

```text
GC 卡顿200ms
```

那么：

```text
0s

1.0s

(卡200ms)

2.2s
```

并不会像 `FixedUpdate` 那样补执行。

也就是说：

```text
不会：

2.0
2.1
```

只会下一次正常调度。

因此它更像：

> **基于游戏时间的定时器，而不是严格的固定时间执行器。**

---

## InvokeRepeating 与协程的区别

| 特性 | InvokeRepeating | 协程 (`Coroutine`) |
|------|-----------------|-------------------|
| 重复调用 | ✅ | ✅ |
| 延迟执行 | ✅ | ✅ (`WaitForSeconds`) |
| 参数 | ❌ 不支持 | ✅ 可以传参数 |
| 返回值 | ❌ | ✅ |
| 中途等待多个阶段 | ❌ | ✅ |
| 可读性 | 简单 | 更灵活 |
| 停止方式 | `CancelInvoke()` | `StopCoroutine()` |
| 自动结束 | 对象销毁时自动取消 | 对象销毁时自动停止 |

---

## 实际开发建议

`InvokeRepeating` 适合非常简单、固定频率的任务，例如：

- 每秒刷新一次 FPS
- 每隔几秒检测网络状态
- 每分钟自动保存
- 周期性刷新 UI

而对于以下场景，更推荐使用协程或自己实现的 Timer：

- 需要传参数
- 有多个等待阶段
- 需要取消、暂停、恢复
- 需要复杂逻辑（如网络请求、动画流程、技能冷却等）

因此，在大多数中大型 Unity 项目中，**`InvokeRepeating` 的使用频率通常低于协程或自定义 Timer 系统**，因为后两者更灵活、也更容易维护。

