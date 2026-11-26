# Resources目录与启动时间

会话 ID：`6a30e8b5-b484-83ea-8299-e5c4801e0ec5`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 3a7e871f-aabc-4ec6-9bc5-416444b78bd6

### 用户

unity resource 目录会影响启动时间吗

### 助手

会，但**要分情况**。很多人认为 `Resources` 目录里的资源都会在游戏启动时加载，其实这是一个误解。

### 结论

- **不会直接把 Resources 里的所有资源都加载到内存。**
- **但是会增加启动时的初始化开销。**
- **Resources 越大，启动时间越容易变长。**

---

## 为什么会影响启动时间？

Unity 在打包时，会把所有 `Resources` 目录下的资源建立一张 **Resources 索引表（Resource Map）**。

游戏启动时，Unity 需要：

1. 扫描所有 Resources 中的资源信息
2. 构建路径 -> 资源的映射
3. 初始化 ResourcesManager

这里**不会加载 Texture、Prefab、Mesh 的内容**，但是会读取它们的元数据。

例如：

```
Assets/
    Resources/
        UI/
            A.prefab
            B.prefab
        Audio/
        Effect/
        Monster/
        Config/
```

假设这里有

```
30000 个资源
```

Unity 启动时都会建立索引。

资源越多：

- Resources 索引越大
- metadata 越多
- 启动时间增加
- 内存占用增加（索引）

---

## 什么情况下影响明显？

例如：

### 情况一：几十个资源

```
Resources
    Button.prefab
    Hero.prefab
```

几乎没有影响。

---

### 情况二：几千个资源

```
5000 Prefab
2000 Texture
1000 Audio
```

启动已经能测到几十毫秒甚至更多。

---

### 情况三：大型项目

很多老项目：

```
Resources

    UI
    Hero
    Effect
    Config
    Icon
    Audio
    Animation
```

里面

```
30000+
```

资源。

启动可能增加：

```
100ms
300ms
500ms
甚至更高
```

尤其手机上更明显。

---

## Resources 最大的问题其实不是启动时间

业内更讨厌 Resources，主要是因为它的打包方式。

### 1. 所有 Resources 都会打包

即使：

```
从来没有调用

Resources.Load(...)
```

只要放进

```
Assets/Resources/
```

都会进入最终包体。

例如：

```
Resources/
    Test.prefab
```

即使没人引用：

```
Resources.Load("Test");
```

它仍然会进入 APK / IPA。

---

### 2. 无法做资源裁剪

普通资源：

```
Prefab
 └── Texture
```

Unity Build Pipeline 会分析依赖：

```
没人引用

↓

不会打包
```

但是 Resources：

```
Resources/

↓

全部打包
```

---

### 3. 无法做按需下载

Resources 是整体索引。

不像

- Addressables
- AssetBundle

可以：

```
第一次下载

↓

后面再下载 DLC
```

Resources 做不到。

---

## Resources.Load 本身快吗？

如果资源已经在 Resources 中：

```csharp
var obj = Resources.Load<GameObject>("Hero");
```

Unity：

```
查索引
↓

找到资源
↓

加载
```

查找速度很快（接近 O(1)）。

真正耗时的是：

```
Prefab Deserialize
Texture Upload
Mesh Upload
Shader
Animation
```

而不是查找。

---

## 官方为什么不推荐 Resources？

Unity 官方现在基本建议：

> **不要在大型项目中依赖 Resources。**

原因包括：

- 启动初始化成本
- 包体膨胀
- 无法增量更新
- 无法精细管理依赖
- 不利于内存管理

推荐使用：

- **Addressables**（官方推荐）
- **AssetBundle**（底层方案）

---

## 面试中推荐的回答

如果面试官问：

> **Resources 会不会影响启动速度？**

可以这样回答：

> 会，但不是因为它会把所有资源加载到内存，而是因为 Unity 在启动时需要为 Resources 目录中的所有资源建立索引和路径映射。随着 Resources 中资源数量增加，启动初始化时间和索引占用的内存都会增加。另外，Resources 中的资源无论是否使用都会被打包，无法进行依赖裁剪，因此大型项目通常会避免大量使用 Resources，而改用 Addressables 或 AssetBundle 进行资源管理。

这也是目前 Unity 项目中比较主流的资源管理思路。

## 轮次 7c9304a7-a1a3-4d96-9c6a-1b1aaca96a8f

### 用户

资源的索引不是在构建打包的时候生成了吗 为啥启动时候还需要扫描

### 助手

这是一个非常好的问题，也是很多 Unity 开发者容易混淆的地方。

**答案是：索引确实是在打包时生成的，但运行时仍然需要把这张索引"加载"到内存，并建立运行时的数据结构。**

这里有两个阶段：

---

# 第一阶段：Build（打包时）

例如你的项目：

```
Resources/
    Hero.prefab
    UI/Login.prefab
    Audio/BGM.mp3
```

Build Pipeline 会做类似这样的事情：

```
Resources.asset

-----------------------------
Hero             -> FileID 101
UI/Login         -> FileID 245
Audio/BGM        -> FileID 387
-----------------------------
```

这一步就是**生成索引**。

它已经知道：

```
路径
↓

对应哪个 Asset
↓

在 PlayerData 的哪个位置
```

所以你说的没错：

> **索引是在 Build 时生成的。**

---

# 第二阶段：游戏启动

问题来了。

这个索引现在还在哪？

答案：

```
磁盘
```

例如：

```
resources.assets
sharedassets0.assets
globalgamemanagers
```

这些都是文件。

而

```csharp
Resources.Load("Hero");
```

需要的是：

```
内存里的 Dictionary
```

例如（概念上）：

```csharp
Dictionary<string, ResourceLocation>
```

里面可能是：

```
Hero
↓

offset = xxxx

type = Prefab

archive = sharedassets0
```

所以启动时 Unity 要做的是：

```
读取 Resources 索引

↓

解析

↓

建立运行时查找表
```

**不是重新生成索引，而是把已经生成好的索引加载到内存。**

---

# 为什么有人说"扫描 Resources"？

这里的"扫描"容易让人误解。

严格来说，不是：

```
遍历 Assets/Resources
```

因为运行时根本没有 `Assets` 目录。

真正发生的是：

```
读取 resources.assets

↓

遍历里面所有 Resource Entry

↓

建立 HashMap
```

所以很多文章把它简称成：

> 扫描 Resources。

实际上应该理解成：

> **扫描 Resources 的资源索引（manifest/index）。**

---

# 为什么资源越多启动越慢？

假设：

```
100 个资源
```

Unity 读取：

```
100 条记录
```

如果：

```
50000 个资源
```

Unity 就要读取：

```
50000 条记录
```

并且：

```
字符串
↓

Hash

↓

ResourceID

↓

Type

↓

Archive
```

都需要建立运行时结构。

所以资源越多：

```
索引文件越大

↓

读取时间增加

↓

解析增加

↓

内存增加
```

但这里增加的是**索引加载成本**，而不是把 5 万个 Prefab、Texture 全部实例化到内存。

---

# 为什么 `Resources.Load` 能这么快？

因为启动阶段已经建立好了查找表。

调用：

```csharp
Resources.Load("Hero")
```

流程更像是：

```
Dictionary

↓

找到 Entry

↓

知道 Hero 在 sharedassets2

↓

offset = xxx

↓

反序列化
```

如果没有这张运行时查找表，每次 `Load` 都去遍历整个索引文件，性能会差得多。

---

## 从引擎实现角度理解

可以把它类比成数据库：

- **Build 阶段**：创建数据库索引（写入磁盘）。
- **启动阶段**：打开数据库，把必要的索引页读入内存，准备查询。
- **`Resources.Load`**：利用内存中的索引快速定位数据。

因此，并不存在"启动时重新生成索引"，而是**加载并初始化已经生成好的索引**。

---

所以，你的理解需要修正一点：

> **打包阶段负责生成索引；启动阶段负责读取并初始化这份索引，使运行时能够快速执行 `Resources.Load`。**

这也是为什么 `Resources` 中资源数量非常多时，即使没有加载任何资源，也可能对启动时间和初始内存占用产生一定影响。

