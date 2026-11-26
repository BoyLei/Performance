# 处理AssetBundle循环引用

会话 ID：`6a30f19a-06bc-83ea-bd72-c8fe85bccf2e`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 a699555d-c12c-4218-aed4-6763e168c8f0

### 用户

会自动把未使用的资源比如 Texture destroy吗

### 助手

会，但是**有条件**，不是一调用就把所有 Texture 都 `Destroy`。

`Resources.UnloadUnusedAssets()` 的作用可以理解为：

> **扫描整个 Unity 对象系统，把已经没有任何有效引用的资源（Texture、Mesh、Material、AnimationClip 等）释放掉。**

---

## 什么叫"未使用"？

例如：

```csharp
Texture2D tex = bundle.LoadAsset<Texture2D>("HeroTex");

renderer.material.mainTexture = tex;
```

此时：

```text
Scene Object
    │
    ▼
Material
    │
    ▼
Texture
```

Texture 正在被 Material 引用，所以：

```csharp
Resources.UnloadUnusedAssets();
```

**不会释放。**

---

## 什么情况下会释放？

例如：

```csharp
Destroy(gameObject);

tex = null;

bundle.Unload(false);

yield return Resources.UnloadUnusedAssets();
```

现在：

```text
Texture

没人引用
```

Unity 在扫描时发现：

- 没有 GameObject 引用
- 没有 Material 引用
- 没有其他 Unity 对象引用
- 没有静态变量等托管引用（准确来说，Unity 会综合判断对象可达性）

于是：

```text
Texture

↓

Destroy Native Object
```

显存和原生内存就会被释放。

---

## 一个容易误解的地方

很多人写：

```csharp
Texture2D tex = bundle.LoadAsset<Texture2D>("A");

bundle.Unload(false);

Resources.UnloadUnusedAssets();
```

然后问：

> Texture 为什么没有释放？

因为：

```csharp
Texture2D tex
```

这个变量还在引用它。

虽然：

```text
Bundle

↓

没了
```

但是：

```text
C#变量

↓

Texture
```

资源依然是"正在使用"。

---

## 再举个例子

### 情况一：会释放

```csharp
Texture2D tex = bundle.LoadAsset<Texture2D>("A");

tex = null;

bundle.Unload(false);

yield return Resources.UnloadUnusedAssets();
```

结果：

```text
Texture

Destroy
```

---

### 情况二：不会释放

```csharp
Texture2D tex = bundle.LoadAsset<Texture2D>("A");

Image.sprite.texture = tex;

bundle.Unload(false);

yield return Resources.UnloadUnusedAssets();
```

因为：

```text
Image

↓

Sprite

↓

Texture
```

Texture 仍然被 UI 使用。

---

## 它内部会不会主动调用 Destroy？

**会，但不是调用你写的 `Destroy(texture)`。**

实际上 Unity 内部会释放对应的 **Native Object**（原生对象）。

对于开发者来说，效果相当于：

```text
Texture Native Memory

↓

释放

↓

GPU 显存释放
```

如果你之后再访问那个已经被释放的 Texture，就可能看到：

```text
MissingReferenceException
```

或者对象变成失效状态。

---

## 为什么要手动调用 `Resources.UnloadUnusedAssets()`？

Unity **不会在每次 `Destroy()` 后立即扫描所有资源**，因为扫描整个对象引用关系的成本比较高。

所以通常流程是：

```csharp
Destroy(sceneObjects);

bundle.Unload(false);

// 场景切换时
yield return Resources.UnloadUnusedAssets();
```

也就是说：

- **Destroy**：删除场景对象。
- **Unload(false)**：释放 Bundle 容器。
- **UnloadUnusedAssets**：统一回收已经无人使用的 Texture、Mesh、Material 等资源。
- **GC.Collect()**（可选）：回收 C# 托管对象。

---

## 大型项目通常怎么做？

在大型项目（例如使用 AssetBundle、Addressables 或 YooAsset）中，常见流程是：

```text
离开场景
    │
Destroy 所有场景对象
    │
AssetBundle 引用计数归零
    │
bundle.Unload(false)
    │
Resources.UnloadUnusedAssets()
    │
（必要时）GC.Collect()
```

这样既能释放纹理、网格、材质等原生资源，又避免频繁扫描带来的性能开销。

### 一句话总结

**会。`Resources.UnloadUnusedAssets()` 会自动释放（销毁底层原生对象）所有已经没有任何有效引用的资源，包括 Texture、Mesh、Material 等；只要资源仍被场景对象、其他 Unity 对象或代码引用，它就不会被释放。**

## 轮次 9e03425f-bdab-4e8e-b66a-a3946a016353

### 用户

有没有办法检测一下UnloadUnusedAssets 后残留的资源

### 助手

有，而且**大型项目基本都会做**。不过需要说明一点：

> **Unity 没有提供一个 API 能直接告诉你“哪些资源在 `UnloadUnusedAssets()` 后应该被释放却没有释放”。**

通常都是通过下面几种方法排查。

---

# 方法一：Memory Profiler（官方推荐）⭐⭐⭐⭐⭐

这是最准确的方法。

Unity 官方提供了 **Memory Profiler**。

流程：

```
进入场景

↓

Take Snapshot A

↓

Destroy对象

↓

UnloadUnusedAssets()

↓

GC.Collect()

↓

Take Snapshot B
```

然后比较：

```
Texture2D

Mesh

Material

GameObject

AssetBundle
```

例如：

```
Texture2D

Before：520

After ：41
```

如果：

```
Before：520

After ：518
```

说明：

还有大量 Texture 没释放。

---

更重要的是：

Memory Profiler 能看到：

```
Texture

↑

Material

↑

MeshRenderer

↑

Player(Clone)
```

它能告诉你：

**到底是谁引用着它。**

这是定位资源泄漏最有效的方法。

---

# 方法二：Resources.FindObjectsOfTypeAll()

例如：

```csharp
Texture2D[] textures =
    Resources.FindObjectsOfTypeAll<Texture2D>();

Debug.Log(textures.Length);
```

Mesh：

```csharp
Mesh[] meshes =
    Resources.FindObjectsOfTypeAll<Mesh>();
```

Material：

```csharp
Material[] mats =
    Resources.FindObjectsOfTypeAll<Material>();
```

Sprite：

```csharp
Sprite[] sprites =
    Resources.FindObjectsOfTypeAll<Sprite>();
```

例如：

```csharp
Debug.Log(Resources.FindObjectsOfTypeAll<Texture2D>().Length);
```

输出：

```
Unload前

Texture : 1023

Unload后

Texture : 35
```

可以快速判断：

有没有大量残留。

---

# 方法三：打印资源名字（很常用）

例如：

```csharp
foreach (var tex in Resources.FindObjectsOfTypeAll<Texture2D>())
{
    Debug.Log(tex.name);
}
```

输出：

```
HeroBody

Monster01

Tree

Grass

Sky
```

立刻知道：

到底哪些没释放。

---

# 方法四：统计 Bundle 的资源

如果：

```csharp
AssetBundle bundle;
```

可以：

```csharp
string[] names = bundle.GetAllAssetNames();
```

例如：

```
hero.prefab

hero.mat

hero.png

sword.prefab
```

然后：

```csharp
foreach(var name in names)
{
    var obj = Resources.FindObjectsOfTypeAll<Object>()
        .FirstOrDefault(o=>o.name==name);
}
```

看看：

哪些还活着。

很多资源管理框架都会这么做。

---

# 方法五：自己维护引用计数（业内最常见）

例如：

```text
Texture

RefCount=3
```

Instantiate：

```
++

Destroy：

--
```

变成：

```
Texture

RefCount=0
```

然后：

```
UnloadUnusedAssets()
```

如果：

Memory Profiler：

```
Texture

还在
```

说明：

有人偷偷引用。

---

很多公司的资源管理器都会打印：

```
===== Leak Report =====

Texture HeroBody

RefCount =0

Still Alive

Referenced by:

Material HeroMat
```

这就是资源泄漏报告。

---

# 方法六：Unity Profiler

Profiler：

```
Memory

↓

Texture Memory

Mesh Memory

Material Count

Object Count
```

例如：

```
Scene A

Texture

1024MB
```

退出：

```
UnloadUnusedAssets
```

结果：

```
Texture

980MB
```

说明：

没释放。

虽然它不知道是谁引用，

但是能看到：

**内存有没有降。**

---

# 方法七：Memory Profiler 查看引用链（最强）

例如：

```
HeroTexture
```

点击：

```
References

↓

Material

↓

Renderer

↓

Player(Clone)

↓

DontDestroyOnLoad
```

马上知道：

为什么释放不了。

这是官方推荐的方法。

---

# 我们项目一般怎么做？

很多公司的资源管理器都会写一个：

```csharp
ResourceManager.CheckLeak();
```

内部：

```csharp
Resources.FindObjectsOfTypeAll<Texture>();

Resources.FindObjectsOfTypeAll<Mesh>();

Resources.FindObjectsOfTypeAll<Material>();

Resources.FindObjectsOfTypeAll<AnimationClip>();

Resources.FindObjectsOfTypeAll<AudioClip>();
```

然后输出：

```
========= Leak =========

Texture : HeroBody

Material : HeroMat

Mesh : HeroMesh

Bundle : hero.ab
```

退出场景：

如果还有：

```
HeroTexture
```

说明：

资源泄漏。

---

# 我建议你学会这一套（面试也很喜欢问）

如果你以后要写一套自己的 **AssetBundle 管理器**，建议提供一个**资源泄漏检测工具**，包含下面几项：

```text
Scene Exit
    │
Destroy 所有 GameObject
    │
AssetBundle.Unload(false)
    │
Resources.UnloadUnusedAssets()
    │
GC.Collect()
    │
统计所有：
    ├── Texture2D
    ├── Mesh
    ├── Material
    ├── Sprite
    ├── AnimationClip
    ├── AudioClip
    └── AssetBundle
    │
输出剩余资源列表
```

这样可以快速发现哪些资源没有被释放。

---

## 一个需要注意的细节

`Resources.FindObjectsOfTypeAll<T>()` 返回的是**当前内存中的所有 Unity 对象**，其中包括很多 Unity 内置资源（默认 Shader、内置字体、编辑器资源等，在 Editor 下尤其多）。因此：

- **不要仅凭数量判断泄漏。**
- 更可靠的方法是：
  - 对比场景切换前后的快照；
  - 只统计自己加载的资源（例如记录 AssetBundle 中的资源路径或 GUID）；
  - 最终结合 **Memory Profiler** 查看引用链定位真正的持有者。

因此，**实际项目中最有效的组合是：自己的资源引用统计 + Memory Profiler 快照对比**。这也是排查 `UnloadUnusedAssets()` 后资源残留最常用的方式。

## 轮次 f2c6d4c1-4c4d-4762-ab8a-9a7eb1c2eb0a

### 用户

unity 多场景

### 助手

Unity 的**多场景（Multi-Scene）**，就是**同时加载多个 Scene，并让它们一起运行**，而不是一次只能有一个 Scene。

很多大型项目（开放世界、MMORPG、大地图、编辑器工具）都会大量使用。

---

# 一、普通场景 vs 多场景

普通加载：

```csharp
SceneManager.LoadScene("Main");
```

流程：

```text
Menu Scene

↓

Load Main

↓

Menu 被卸载
```

内存中始终只有一个 Scene。

---

多场景加载：

```csharp
SceneManager.LoadScene("UI", LoadSceneMode.Additive);
```

结果：

```text
Main Scene

+

UI Scene
```

两个 Scene 同时存在。

继续：

```csharp
SceneManager.LoadScene("Effect", LoadSceneMode.Additive);
```

变成：

```text
Main

+

UI

+

Effect
```

此时 Hierarchy：

```text
Main
    Player
    Monster

UI
    Canvas
    Button

Effect
    Rain
    Snow
```

三个 Scene 同时运行。

---

# 二、Additive 的原理

关键就是：

```csharp
LoadSceneMode.Additive
```

例如：

```csharp
SceneManager.LoadSceneAsync(
    "UI",
    LoadSceneMode.Additive);
```

Unity 不会：

```text
Unload 当前 Scene
```

而是：

```text
创建一个新的 Scene

↓

反序列化里面所有对象

↓

加入 SceneManager
```

所以：

```text
SceneManager

↓

Scene0

↓

Scene1

↓

Scene2
```

可以认为：

Unity 内部维护：

```text
List<Scene>
```

所有 Scene 都在这里。

---

# 三、Scene 和 GameObject 的关系

例如：

```text
SceneA

Player

Enemy
```

还有：

```text
SceneB

Canvas

Button
```

Player 属于：

```text
SceneA
```

Canvas 属于：

```text
SceneB
```

可以：

```csharp
Scene scene = player.scene;
```

得到：

```text
SceneA
```

说明：

**每个 GameObject 都属于某一个 Scene。**

---

# 四、Active Scene

同时：

```text
Main

UI

Effect
```

Unity 还有：

```text
Active Scene
```

例如：

```csharp
SceneManager.SetActiveScene(scene);
```

为什么？

因为：

```csharp
Instantiate(prefab);
```

没有指定 Scene。

Unity：

默认：

```text
放到 Active Scene
```

例如：

Active：

```text
Main
```

那么：

```csharp
Instantiate(enemy);
```

Enemy：

```text
属于 Main
```

如果：

```text
UI
```

成为 Active：

Instantiate：

```text
放到 UI
```

---

# 五、移动对象到其他 Scene

例如：

```csharp
Scene effectScene =
    SceneManager.GetSceneByName("Effect");
```

然后：

```csharp
SceneManager.MoveGameObjectToScene(
    player,
    effectScene);
```

Player：

从：

```text
Main
```

移动到：

```text
Effect
```

Hierarchy：

```text
Main

Enemy
```

```text
Effect

Rain

Player
```

---

# 六、多场景卸载

例如：

```csharp
SceneManager.UnloadSceneAsync("UI");
```

Unity：

```text
Destroy

Canvas

Button

Text

Image
```

整个 Scene：

```text
消失
```

但是：

```text
Main
```

继续运行。

---

# 七、多场景和 AssetBundle

很多项目：

```text
MainScene

↓

Terrain.bundle
```

再：

```text
UIScene

↓

UI.bundle
```

例如：

```text
Login

Battle

CommonUI

Weather

Audio
```

全部：

```text
Additive
```

组合。

切换：

```text
Battle

↓

Unload Weather

↓

Load Desert Weather
```

而：

```text
Battle Scene
```

完全不用重新加载。

---

# 八、大型项目常见架构

很多公司：

```text
Boot Scene
```

负责：

```text
ResourceManager

AudioManager

NetworkManager
```

然后：

```text
Game Scene
```

负责：

```text
地图
```

还有：

```text
UI Scene
```

负责：

```text
Canvas
```

还有：

```text
Effect Scene
```

负责：

```text
天气

光照

后处理
```

Hierarchy：

```text
Boot
    Managers

Game
    Terrain
    NPC

UI
    Canvas

Effect
    Rain
```

这种结构比一个 Scene 放几万个对象更容易维护。

---

# 九、开放世界（Streaming）

例如：

```text
地图

A

B

C

D
```

玩家：

```text
当前位置：

A
```

加载：

```text
A
```

走近：

```text
B
```

变成：

```text
A

+

B
```

离开：

```text
A
```

变成：

```text
Unload A

↓

只剩

B
```

继续：

```text
B

+

C
```

这种就是：

**Scene Streaming（场景流式加载）**

基本所有开放世界：

```text
原神

塞尔达

GTA

巫师
```

都类似。

---

# 十、多场景的优点

✅ **职责清晰**

- UI 一个 Scene
- 地图一个 Scene
- 光照一个 Scene
- 特效一个 Scene

---

✅ **支持多人协作**

如果所有内容都在一个 Scene：

```text
Main.unity
```

Git：

天天冲突。

拆：

```text
Terrain

Lighting

NPC

UI
```

每个人改自己的。

---

✅ **方便热更新**

例如：

```text
Battle Scene
```

不用改。

更新：

```text
Weather Scene
```

即可。

---

# 十一、需要注意的坑

### 1. `DontDestroyOnLoad`

它并不属于任何普通 Scene，而是会进入 Unity 的一个特殊场景（常称为 **DontDestroyOnLoad Scene**）。

所以：

```csharp
DontDestroyOnLoad(gameObject);
```

即使：

```text
Unload Scene
```

对象：

不会销毁。

---

### 2. Lighting（光照）

每个 Scene：

可以有：

```text
Lightmap

Reflection Probe

Skybox
```

多个 Scene：

需要处理：

```text
Lighting Settings
```

否则：

容易：

```text
光照错乱
```

---

### 3. NavMesh

多个 Scene：

可能：

```text
多个 NavMesh
```

需要：

```text
NavMeshSurface
```

统一管理。

---

## 十二、面试怎么回答？

可以这样总结：

> **Unity 多场景（Multi-Scene）是通过 `LoadSceneMode.Additive` 同时加载多个 Scene，每个 GameObject 都属于一个 Scene，SceneManager 统一管理这些 Scene。实际项目中通常会将地图、UI、特效、光照、管理器拆分到不同 Scene，既方便团队协作，也支持按需加载和卸载，减少内存占用。对于开放世界，还会结合 Additive 实现流式加载（Scene Streaming），根据玩家位置动态加载和卸载相邻场景。**

## 轮次 28b403aa-cf87-43db-8c7c-f3b75d05a33f

### 用户

如果一个mono脚本代码引用了一个texture，当这个脚本挂载的节点被destroy后，这个纹理会被释放吗

### 助手

这个问题的答案是：

> **不一定。** 是否会释放，取决于 **Texture 是否还有其他引用**，以及 **是否执行了资源回收**。

我们分几种情况来看。

---

# 情况一：最常见——会最终释放

例如：

```csharp
public class Test : MonoBehaviour
{
    public Texture2D tex;
}
```

Inspector：

```text
GameObject
    └── Test
            └── Hero.png
```

现在：

```csharp
Destroy(gameObject);
```

发生了什么？

```
GameObject
    ↓
Destroy
```

MonoBehaviour：

```
Destroy
```

成员变量：

```csharp
tex
```

自然也没有了。

如果：

整个项目再也没人引用这个 Texture：

```
Texture

没人引用
```

然后：

```csharp
yield return Resources.UnloadUnusedAssets();
```

Unity 就会把：

```
Texture Native Object

↓

Destroy
```

显存也释放。

---

# 情况二：不会释放

例如：

```csharp
public class Test : MonoBehaviour
{
    public Texture2D tex;

    void Start()
    {
        Global.Texture = tex;
    }
}
```

这里：

```text
Global

↓

Texture
```

Destroy：

```csharp
Destroy(gameObject);
```

虽然：

```
Test

没了
```

但是：

```
Global

↓

Texture
```

仍然引用。

所以：

```csharp
Resources.UnloadUnusedAssets();
```

不会释放。

---

# 情况三：Material 正在使用

例如：

```csharp
renderer.material.mainTexture = tex;
```

Destroy：

```csharp
Destroy(test);
```

但是：

```
Renderer

↓

Material

↓

Texture
```

Texture：

依然被引用。

所以：

不会释放。

---

# 情况四：Sprite 正在引用

例如：

```
Sprite

↓

Texture
```

Image：

```
Image

↓

Sprite

↓

Texture
```

Destroy：

```csharp
Destroy(test);
```

没有意义。

因为：

```
UI

↓

Sprite

↓

Texture
```

Texture：

还活着。

---

# 情况五：AssetBundle

例如：

```csharp
Texture2D tex =
    bundle.LoadAsset<Texture2D>("Hero");
```

然后：

```csharp
Destroy(gameObject);

bundle.Unload(false);
```

如果：

没有任何地方：

```
Texture
```

被引用。

那么：

```csharp
Resources.UnloadUnusedAssets();
```

Texture：

会释放。

---

# Unity 判断"是否使用"不是看变量，而是看引用图

可以理解为：

```
Scene

↓

GameObject

↓

MonoBehaviour

↓

Texture
```

Destroy：

```
GameObject

↓

×

MonoBehaviour

↓

×

Texture
```

如果：

没有其他箭头：

```
Texture

↓

Destroy
```

如果还有：

```
Material

↓

Texture
```

那：

```
Texture

继续活着
```

---

# 一个容易误解的点

很多人觉得：

```csharp
Destroy(gameObject);
```

是不是就立刻释放 Texture？

**不是。**

`Destroy` 只是：

```
GameObject

↓

标记销毁
```

真正资源回收：

通常发生在：

```csharp
Resources.UnloadUnusedAssets();
```

或者：

场景切换时 Unity 自动执行一次。

所以：

```text
Destroy

↓

引用断开

↓

UnloadUnusedAssets

↓

Texture Destroy
```

---

# 大型项目的流程

例如：

```
退出副本

↓

Destroy 所有怪物

↓

Destroy 所有UI

↓

Unload Bundle(false)

↓

Resources.UnloadUnusedAssets()

↓

GC.Collect()
```

这时候：

没有引用的：

- Texture
- Mesh
- Material
- AnimationClip

都会被释放。

---

## 一句话总结

**如果 MonoBehaviour 挂载的 GameObject 被 `Destroy`，那么它对 Texture 的引用也会消失。但 Texture 不会立即释放，只有当整个项目中没有任何对象再引用它，并执行 `Resources.UnloadUnusedAssets()`（或 Unity 在合适时机自动回收）后，它才会真正从内存和显存中释放。**

## 轮次 a4f25229-c670-4180-bdf1-7a7d80916549

### 用户

如果这个脚本是异步加载的方式加载的纹理，且这个纹理未被其它引用

### 助手

这个场景需要区分**C# 引用**和 **Unity 资源生命周期**。

如果你的情况是：

- ✅ 异步加载了一个 `Texture2D`
- ✅ 只保存在这个 MonoBehaviour 的成员变量里
- ✅ 没有赋值给 Material、UI、Renderer 等任何 Unity 对象
- ✅ 没有缓存到全局、静态变量或资源管理器
- ✅ GameObject 被 `Destroy`

那么答案是：

> **这个 Texture 会变成"未使用资源"，在之后执行 `Resources.UnloadUnusedAssets()` 时可以被释放。**

例如：

```csharp
public class Test : MonoBehaviour
{
    Texture2D tex;

    async void Start()
    {
        tex = await LoadTextureAsync();
    }
}
```

然后：

```csharp
Destroy(gameObject);
```

引用关系变成：

```text
GameObject      ×
    │
MonoBehaviour   ×
    │
Texture2D
```

因为 MonoBehaviour 被销毁，它持有的 `tex` 引用也不存在了。

如果没有其他地方引用：

```text
Texture2D

没人引用
```

执行：

```csharp
yield return Resources.UnloadUnusedAssets();
```

Texture 就可以被回收。

---

## 但是，有一个工程上最容易踩的坑

真正的异步加载通常不是这样简单。

例如：

```csharp
tex = await assetHandle.LoadAsync<Texture2D>();
```

或者：

```csharp
tex = await Addressables.LoadAssetAsync<Texture2D>(key);
```

或者：

```csharp
tex = await YooAssets.LoadAssetAsync<Texture2D>(path);
```

这里往往还有一个 **Handle（加载句柄）**：

```text
MonoBehaviour
      │
      ▼
Texture

AssetManager
      │
      ▼
Handle
      │
      ▼
Texture
```

即使：

```csharp
Destroy(gameObject);
```

MonoBehaviour 的引用没了，

但是：

```text
AssetManager

↓

Handle

↓

Texture
```

仍然存在。

因此：

```csharp
Resources.UnloadUnusedAssets();
```

**也不会释放。**

你必须：

```csharp
handle.Release();
```

或者：

```csharp
Addressables.Release(handle);
```

或者：

```csharp
assetHandle.Release();
```

让资源管理器取消对它的引用。

---

## 再举两个例子

### 示例一：原生 AssetBundle

```csharp
Texture2D tex = bundle.LoadAsset<Texture2D>("A");

Destroy(gameObject);

bundle.Unload(false);

Resources.UnloadUnusedAssets();
```

如果：

- `tex` 没有赋给任何对象；
- 没有其他 C# 引用；

那么：

> Texture 可以被释放。

---

### 示例二：Addressables

```csharp
var handle = Addressables.LoadAssetAsync<Texture2D>("A");

Texture2D tex = await handle.Task;

Destroy(gameObject);
```

这时候：

```text
Addressables

↓

Handle

↓

Texture
```

Texture 仍然被 Addressables 管理。

即使：

```csharp
Resources.UnloadUnusedAssets();
```

也不会释放。

必须：

```csharp
Addressables.Release(handle);
```

之后，在没有其他引用的情况下，资源才有机会被回收。

---

## 最后回答你的问题

**如果你说的是自己异步加载（例如 `await File.ReadAllBytesAsync()` 后创建 Texture，或者 `AssetBundle.LoadAssetAsync()` 得到 Texture），并且这个 Texture 既没有赋给任何 Unity 对象，也没有被任何资源管理器或其他代码持有，那么当 MonoBehaviour 所在的 GameObject 被 `Destroy` 后，它会失去最后一个引用，在执行 `Resources.UnloadUnusedAssets()` 时可以被释放。**

**但如果你使用的是 Addressables、YooAsset 等资源管理框架，通常还需要释放对应的加载句柄（Handle），否则资源管理器本身仍然持有引用，资源不会因为 MonoBehaviour 被销毁而释放。**

