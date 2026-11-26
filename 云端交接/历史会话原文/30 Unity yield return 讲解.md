# Unity yield return 讲解

会话 ID：`6a2aa307-99b8-83ea-8e82-60d46e6be499`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 ac386c52-75ae-4c7b-b4a1-437d0ee8372e

### 用户

unity  yield return

### 助手

在 Unity 里，`yield return` 主要是**配合协程（Coroutine）**使用的，用来让函数“暂停执行，等到某个时机再继续”。

它最常见的写法是：

```csharp
IEnumerator Start()
{
    Debug.Log("A");
    yield return new WaitForSeconds(2f);
    Debug.Log("B");
}
```

这段代码的意思是：

- 先打印 `A`
- 等 2 秒
- 再打印 `B`

---

### 它的本质
`yield return` 不会像普通函数那样一次执行完，而是告诉 Unity：

“这个协程先停在这里，下一帧/下次条件满足时再继续。”

所以它常用于：

- 等待时间
- 等待下一帧
- 等待异步加载
- 分步执行逻辑，避免卡顿

---

### 常见写法

```csharp
yield return null;
```
表示**等一帧再继续**。

```csharp
yield return new WaitForSeconds(1f);
```
表示**等待 1 秒**。

```csharp
yield return new WaitUntil(() => isReady);
```
表示**等条件成立后继续**。

```csharp
yield return new WaitWhile(() => isLoading);
```
表示**等条件不成立后继续**。

```csharp
yield return StartCoroutine(OtherCoroutine());
```
表示**等待另一个协程执行完**。

---

### 示例：逐步执行
```csharp
using UnityEngine;
using System.Collections;

public class Test : MonoBehaviour
{
    void Start()
    {
        StartCoroutine(MyRoutine());
    }

    IEnumerator MyRoutine()
    {
        Debug.Log("开始");
        yield return new WaitForSeconds(1f);
        Debug.Log("1秒后");
        yield return null;
        Debug.Log("下一帧");
    }
}
```

---

### 一个容易混淆的点
`yield return` **只能出现在 `IEnumerator` 方法里**，不能直接写在普通 `void` 方法中。

---

### 你可以把它理解成
`yield return` 就像一个“暂停点”：

- 到这里先停一下
- 把控制权还给 Unity
- 之后再从这里继续

如果你愿意，我可以继续给你讲：

1. `yield return null`、`WaitForSeconds`、`WaitForFixedUpdate` 的区别  
2. 协程和 `async/await` 的区别  
3. `yield return` 在加载场景、进度条里怎么用

## 轮次 d20c58d8-2512-490b-916f-3ff928a15921

### 用户

foreach (string dep in dependencies) { if (!loadedBundles.ContainsKey(dep)) { var request = AssetBundle.LoadFromFileAsync(GetBundlePath(dep)); yield return request; loadedBundles[dep] = request.assetBundle; AddReference(dep); } } //

### 助手

你这段代码：

```csharp
foreach (string dep in dependencies)
{
    if (!loadedBundles.ContainsKey(dep))
    {
        var request = AssetBundle.LoadFromFileAsync(GetBundlePath(dep));

        yield return request;

        loadedBundles[dep] = request.assetBundle;

        AddReference(dep);
    }
}
```

这里的：

```csharp
yield return request;
```

实际上是在告诉 Unity：

> "当前协程暂停，等这个 `AssetBundleCreateRequest` 完成后再继续执行。"

---

### 执行流程

假设：

```csharp
dependencies =
{
    "common",
    "shader",
    "effect"
};
```

执行过程：

```text
开始加载 common
↓
yield return request
↓
等待磁盘IO完成
↓
common加载完成

开始加载 shader
↓
yield return request
↓
等待磁盘IO完成
↓
shader加载完成

开始加载 effect
↓
yield return request
↓
等待磁盘IO完成
↓
effect加载完成
```

所以这是：

### 串行加载（Sequential）

```text
common
   ↓
shader
   ↓
effect
```

总耗时：

```text
T = common + shader + effect
```

---

### 为什么 `yield return request` 能等待？

因为：

```csharp
AssetBundle.LoadFromFileAsync()
```

返回的是：

```csharp
AssetBundleCreateRequest
```

继承自：

```csharp
AsyncOperation
```

而 Unity 协程有特殊处理：

```csharp
yield return AsyncOperation;
```

等价于：

```csharp
while(!request.isDone)
{
    yield return null;
}
```

Unity内部帮你写好了循环。

---

### 如果改成这样

```csharp
var request = AssetBundle.LoadFromFileAsync(path);

while(!request.isDone)
{
    yield return null;
}
```

效果完全一样。

---

### 一个很多人不知道的点

你的代码虽然用了：

```csharp
LoadFromFileAsync
```

但实际上：

```csharp
foreach
{
    yield return request;
}
```

仍然是串行加载。

很多人误以为：

```csharp
LoadFromFileAsync
```

就是并行。

其实不是。

因为你立刻：

```csharp
yield return request;
```

把协程卡在这里了。

---

### 真正并行加载

```csharp
List<AssetBundleCreateRequest> requests = new();

foreach (var dep in dependencies)
{
    requests.Add(
        AssetBundle.LoadFromFileAsync(GetBundlePath(dep))
    );
}

foreach (var request in requests)
{
    yield return request;
}
```

或者：

```csharp
while(requests.Any(r => !r.isDone))
{
    yield return null;
}
```

流程：

```text
common  ─────┐
shader  ─────┼─ 同时加载
effect  ─────┘
```

总耗时：

```text
T = max(common, shader, effect)
```

而不是：

```text
T = common + shader + effect
```

---

### AssetBundle 项目里的常见写法

业内通常不会简单地：

```csharp
yield return request;
```

而是封装成：

```csharp
BundleLoadOperation
```

例如 Unity 早期官方 AssetBundleManager：

```csharp
AssetBundleLoadAssetOperation
AssetBundleLoadLevelOperation
AssetBundleLoadManifestOperation
```

统一放到：

```csharp
AssetBundleManager.Update()
```

里轮询：

```csharp
operation.Update();
```

这样可以：

- 控制依赖加载
- 控制引用计数
- 控制优先级
- 支持取消加载
- 支持重试
- 支持进度统计

这也是大型项目（MMO、开放世界）常见的 AssetBundle 加载架构。

## 轮次 46508409-8cd4-42d0-adc5-2ffd9eded6e0

### 用户

yield return request;  这段代码会卡住主线程吗

### 助手

**不会。**

这是很多 Unity 开发者刚接触协程时最容易误解的地方。

你的代码：

```csharp
var request = AssetBundle.LoadFromFileAsync(path);

yield return request;
```

看起来像：

```csharp
request.Wait();
```

但实际上完全不是一回事。

---

### 实际发生了什么

执行到：

```csharp
yield return request;
```

时，Unity 会：

```text
当前协程暂停
↓
主线程继续跑
↓
渲染继续
↓
Update继续
↓
LateUpdate继续
↓
UI继续刷新
↓
等待request完成
↓
下一帧恢复协程
```

所以：

```text
主线程：没有被阻塞
协程：被挂起
```

---

### 类比一下

#### 会卡主线程

```csharp
while (!request.isDone)
{
}
```

这是死循环。

```text
主线程
↓
while
↓
while
↓
while
↓
while
```

这一帧永远出不去。

表现：

- 游戏卡死
- 界面不刷新
- FPS=0

---

#### 不会卡主线程

```csharp
while (!request.isDone)
{
    yield return null;
}
```

或者：

```csharp
yield return request;
```

效果：

```text
Frame1
检查一次
↓
让出主线程

Frame2
检查一次
↓
让出主线程

Frame3
检查一次
↓
让出主线程
```

每帧只检查一次。

所以不卡。

---

### 那为什么有时候加载 AB 还是会掉帧？

因为：

```csharp
AssetBundle.LoadFromFileAsync()
```

并不代表所有工作都在后台线程完成。

内部通常是：

```text
磁盘读取
↓
解压
↓
Bundle Header解析
↓
对象反序列化
↓
创建Unity Object
```

其中：

- 磁盘IO可能异步
- 部分解析可能异步
- Unity Object创建必须主线程

因此你可能看到：

```text
yield return request
```

没阻塞主线程，

但完成那一帧：

```text
Main Thread Spike
```

突然出现：

```text
10ms
20ms
50ms
```

的尖峰。

---

### 真正会卡的是这些

#### 1. LoadFromFile（同步）

```csharp
var ab = AssetBundle.LoadFromFile(path);
```

这是同步加载。

调用时：

```text
主线程等待IO
主线程等待解析
```

直接卡住。

---

#### 2. LoadAsset（同步）

```csharp
var prefab = bundle.LoadAsset<GameObject>("Role");
```

也是同步。

如果资源很大：

```text
贴图反序列化
Mesh创建
Material创建
```

都会卡。

---

#### 3. Instantiate

很多人以为：

```csharp
yield return request;
```

卡。

实际上是：

```csharp
var obj = Instantiate(prefab);
```

卡。

因为：

```text
Awake
OnEnable
Animator初始化
粒子系统初始化
Canvas重建
```

全在主线程。

---

### 最佳实践

AB加载：

```csharp
yield return bundleRequest;
yield return assetRequest;
```

都用异步：

```csharp
AssetBundle.LoadFromFileAsync
AssetBundleRequest
```

例如：

```csharp
var bundleReq = AssetBundle.LoadFromFileAsync(path);
yield return bundleReq;

var assetReq = bundleReq.assetBundle.LoadAssetAsync<GameObject>("Hero");
yield return assetReq;
```

这样主线程压力最小。

---

一句话总结：

```csharp
yield return request;
```

**不会阻塞主线程，它只是暂停当前协程。**

真正可能导致卡顿的是 `request` 完成时的资源解析、反序列化和后续的 `Instantiate()`，而不是 `yield return` 本身。

