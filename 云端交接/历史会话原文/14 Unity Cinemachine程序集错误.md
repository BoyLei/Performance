# Unity Cinemachine程序集错误

会话 ID：`6a4e5e81-a61c-83ea-b775-5b2c18722f54`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 476ee374-b5aa-4b43-a139-9d8bc53d1fe8

### 用户

unity 2022 它的 版本是 14

[User attached 1 image; image contents were not included]

### 助手

对，**Unity 2022.3 官方推荐的 SRP / ShaderGraph 大版本确实是 14.x**。

但你现在的问题是：**你工程里 URP/Core 不是 14，而是本地包 12.1.9**。

你当前包组合之前是：

```json
"com.unity.render-pipelines.core": "file:../LocalPackages/com.unity.render-pipelines.core@12.1.9",
"com.unity.render-pipelines.universal": "file:../LocalPackages/com.unity.render-pipelines.universal@12.1.9",
"com.unity.shadergraph": "14.0.11"
```

这个就是不匹配的地方。fileciteturn0file1

---

## 关键点

### Unity 2022.3 官方正常组合是：

```text
URP 14.0.11
Core 14.0.11
ShaderGraph 14.0.11
```

所以你截图里看到 `Shader Graph 14.0.11` 是正常的。

---

### 但你的本地 URP 12.1.9 要求的是：

```text
URP 12.1.9
Core 12.1.9
ShaderGraph 12.1.9
```

你之前的 `packages-lock.json` 里也能看到，本地 URP 12.1.9 声明依赖：

```json
"com.unity.shadergraph": "12.1.9"
```

fileciteturn0file0

---

## 所以不是“Unity 2022 用 14 就一定对”

要看你选哪条路线。

## 路线 A：完全升级到 Unity 2022 官方 SRP 栈

那就用：

```json
"com.unity.render-pipelines.core": "14.0.11",
"com.unity.render-pipelines.universal": "14.0.11",
"com.unity.shadergraph": "14.0.11"
```

优点：符合 Unity 2022.3 官方版本。

缺点：你现在的本地 URP/Core 12.1.9 如果有项目修改，会丢，需要重新合并到 14.0.11。

---

## 路线 B：保留本地 URP/Core 12.1.9

那就应该用：

```json
"com.unity.render-pipelines.core": "file:../LocalPackages/com.unity.render-pipelines.core@12.1.9",
"com.unity.render-pipelines.universal": "file:../LocalPackages/com.unity.render-pipelines.universal@12.1.9",
"com.unity.shadergraph": "12.1.9"
```

优点：保留旧工程的本地修改。

缺点：这是 Unity 2021 系列 SRP 包拿到 Unity 2022 里用，可能需要 API Updater 修源码，也可能继续遇到兼容问题。

---

## 你现在不要混成这样

不要这样：

```json
"com.unity.render-pipelines.core": "file:../LocalPackages/com.unity.render-pipelines.core@12.1.9",
"com.unity.render-pipelines.universal": "file:../LocalPackages/com.unity.render-pipelines.universal@12.1.9",
"com.unity.shadergraph": "14.0.11"
```

这个组合最容易出现你之前那类错误：

```text
TimedScope does not exist
ShaderPreprocessor.cs 报错
SRP / ShaderGraph API 对不上
```

---

## 我的建议

如果你担心本地包有改动，先走 **路线 B**：

```json
"com.unity.shadergraph": "12.1.9"
```

等工程能打开、能编译之后，再决定要不要把本地 URP/Core 升级到 14.0.11 并合并修改。

一句话：**Unity 2022 推荐 ShaderGraph 14 没错；但你现在保留本地 URP 12，就要配 ShaderGraph 12。**

## 轮次 c9001fcb-7566-45d7-9f00-dd1288351cb6

### 用户

shadergraph 是什么

### 助手

**Shader Graph 是 Unity 的“可视化 Shader 编辑器”。**

它的作用是：不用手写 HLSL/ShaderLab 代码，通过节点连线的方式生成 Shader。

简单理解：

```text
Shader Graph = 用节点图做材质/Shader 的工具
```

---

## Shader 是什么

Shader 是控制物体怎么被渲染的程序，比如：

```text
颜色
透明
发光
溶解
扭曲
水面
描边
卡通渲染
法线效果
PBR 光照
```

传统写法是手写代码：

```hlsl
float4 color = tex2D(_MainTex, uv);
```

Shader Graph 则是用节点做：

```text
Texture2D 节点
→ Sample Texture 节点
→ Base Color
```

---

## Shader Graph 在 Unity 里负责什么

它主要用于 SRP 渲染管线：

```text
URP
HDRP
```

在 URP 里，一个 Shader Graph 可能生成：

```text
Lit Shader
Unlit Shader
Sprite Shader
FullScreen Shader
Decal Shader
```

然后你可以把它做成材质，用在模型、UI、特效、Sprite 上。

---

## 它和 URP/Core 的关系

Shader Graph 不是单独工作的，它依赖 SRP 的底层代码。

大概关系是：

```text
com.unity.render-pipelines.core
        ↑
        │
com.unity.shadergraph
        ↑
        │
com.unity.render-pipelines.universal
```

URP 里会有很多和 Shader Graph 对接的代码，比如：

```text
URP Lit Target
URP Unlit Target
Sprite Lit Target
Shader Preprocessor
Shader Variant 处理
```

所以版本必须匹配。

---

## 为什么你这里会报错

你的工程现在是旧工程迁移，之前出现过这种组合：

```text
URP/Core: 12.1.9 本地包
ShaderGraph: 14.0.11
Unity: 2022.3
```

这里的问题是：

```text
URP 12 的源码在调用 ShaderGraph 12 的 API
但工程里实际装的是 ShaderGraph 14
```

ShaderGraph 14 里面很多接口、类名、命名空间可能变了，所以 URP 12 的代码就会报类似：

```text
TimedScope does not exist
某个接口不存在
某个方法签名不匹配
```

这不是 Shader 写错了，而是 **渲染管线包版本不一致**。

---

## 举个例子

假设你有一个本地 URP 包：

```text
LocalPackages/com.unity.render-pipelines.universal@12.1.9
```

它内部可能写了：

```csharp
using UnityEditor.ShaderGraph;
```

并且调用的是 ShaderGraph 12 的某些类。

但你装的是：

```text
com.unity.shadergraph@14.0.11
```

那就可能找不到原来的 API。

---

## 结论

Shader Graph 是：

```text
Unity 用节点编辑 Shader 的工具包
```

在你的工程里，它同时也是：

```text
URP / HDRP 渲染管线的一部分依赖
```

所以要么整套用 Unity 2022 推荐版本：

```text
URP 14
Core 14
ShaderGraph 14
```

要么保留旧本地管线：

```text
URP 12.1.9
Core 12.1.9
ShaderGraph 12.1.9
```

不要混用：

```text
URP 12 + ShaderGraph 14
```

这个组合很容易炸。

## 轮次 db011bfc-26cf-4df5-914b-50b66b9112e2

### 用户

那怎么弄 , 我该润安下载 这个版本的 shadergraph

### 助手

你不要在 Package Manager 界面里找。Unity 2022 的 Package Manager 默认只给你显示推荐的 `14.0.11`，但你这个工程如果保留本地：

```json
"com.unity.render-pipelines.core": "file:../LocalPackages/com.unity.render-pipelines.core@12.1.9",
"com.unity.render-pipelines.universal": "file:../LocalPackages/com.unity.render-pipelines.universal@12.1.9"
```

那就应该手动在 `Packages/manifest.json` 里指定：

```json
"com.unity.shadergraph": "12.1.9"
```

你的本地 URP 12.1.9 依赖的就是 ShaderGraph 12.1.9，不是 14.0.11。fileciteturn0file0

---

## 具体怎么改

关闭 Unity，打开：

```text
Packages/manifest.json
```

找到：

```json
"com.unity.shadergraph": "14.0.11"
```

改成：

```json
"com.unity.shadergraph": "12.1.9"
```

最终这几项保持一致：

```json
"com.unity.render-pipelines.core": "file:../LocalPackages/com.unity.render-pipelines.core@12.1.9",
"com.unity.render-pipelines.universal": "file:../LocalPackages/com.unity.render-pipelines.universal@12.1.9",
"com.unity.shadergraph": "12.1.9"
```

注意逗号格式，JSON 最后一项不能多逗号。

---

## 改完后清缓存

关闭 Unity 后删除：

```text
Packages/packages-lock.json
Library/PackageCache
Library/ScriptAssemblies
Library/Bee
```

然后重新打开 Unity。

Unity 会自动从 Unity Registry 下载：

```text
com.unity.shadergraph@12.1.9
```

如果能解析成功，`Library/PackageCache` 里会出现类似：

```text
Library/PackageCache/com.unity.shadergraph@12.1.9
```

---

## 如果 Unity 下载不到 12.1.9

再用备用方案：建一个 Unity 2021.3 工程，安装 URP 12.1.9，然后从新工程复制：

```text
新工程/Library/PackageCache/com.unity.shadergraph@12.1.9
```

到你的旧工程：

```text
旧工程/LocalPackages/com.unity.shadergraph@12.1.9
```

然后 `manifest.json` 写成：

```json
"com.unity.shadergraph": "file:../LocalPackages/com.unity.shadergraph@12.1.9"
```

---

## 你现在推荐用哪种

先用最简单的 registry 方式：

```json
"com.unity.shadergraph": "12.1.9"
```

如果 Unity 拉不下来，再改成本地包：

```json
"com.unity.shadergraph": "file:../LocalPackages/com.unity.shadergraph@12.1.9"
```

不要继续用：

```json
"com.unity.shadergraph": "14.0.11"
```

否则会继续和本地 URP 12.1.9 冲突。

## 轮次 6847f201-5e56-4e40-ae83-dc0a4d050695

### 用户

这个 shadergraph 的安装目录 在哪

[User attached 1 image; image contents were not included]

### 助手

它现在是 **Registry 包**，不是本地包，所以安装目录通常在你工程的 `Library/PackageCache` 下面。

按你工程路径，大概率是：

```text
H:\Star\Stars_Project\StarsProject_Client\trunk\Stars\Library\PackageCache\com.unity.shadergraph@12.1.15
```

也就是：

```text
项目根目录\Library\PackageCache\com.unity.shadergraph@12.1.15
```

---

如果你想直接找，可以在工程根目录执行：

```powershell
Get-ChildItem .\Library\PackageCache -Directory | Where-Object { $_.Name -like "com.unity.shadergraph*" }
```

或者直接：

```powershell
explorer .\Library\PackageCache
```

然后找：

```text
com.unity.shadergraph@12.1.15
```

---

注意：`Library/PackageCache` 是 Unity 自动生成的缓存目录，**不建议直接在里面改代码**。  
如果你想把 ShaderGraph 固定成本地包，应该复制出来：

```text
Library/PackageCache/com.unity.shadergraph@12.1.15
```

复制到：

```text
LocalPackages/com.unity.shadergraph@12.1.15
```

然后把 `manifest.json` 改成：

```json
"com.unity.shadergraph": "file:../LocalPackages/com.unity.shadergraph@12.1.15"
```

这样以后 Unity 就会用本地 ShaderGraph 包，而不是 Registry 缓存包。

## 轮次 1b70a664-db41-4cba-ae9b-b2cbcd2c40cc

### 用户

"com.unity.shadergraph": {
      "version": "file:../LocalPackages/com.unity.shadergraph@12.1.9",
      "depth": 0,
      "source": "local",
      "dependencies": {
        "com.unity.render-pipelines.core": "12.1.15",
        "com.unity.searcher": "4.9.2"
      }
    }

但是  com.unity.render-pipelines.core 我本地是 1.9 版本, 会有问题吗

### 助手

会有风险，建议 **不要这样混**。

你现在这段表示：

```json
"com.unity.shadergraph": {
  "version": "file:../LocalPackages/com.unity.shadergraph@12.1.9",
  "dependencies": {
    "com.unity.render-pipelines.core": "12.1.15"
  }
}
```

意思是：你本地的 `ShaderGraph` 包，内部声明它依赖：

```text
com.unity.render-pipelines.core 12.1.15
```

但你工程里本地 `Core` 是：

```text
com.unity.render-pipelines.core 12.1.9
```

这就是版本不一致。

---

## 结论

最好保持这三个包完全一致：

```text
com.unity.render-pipelines.core       12.1.9
com.unity.render-pipelines.universal  12.1.9
com.unity.shadergraph                 12.1.9
```

或者统一升到：

```text
com.unity.render-pipelines.core       12.1.15
com.unity.render-pipelines.universal  12.1.15
com.unity.shadergraph                 12.1.15
```

不要变成：

```text
URP/Core       12.1.9
ShaderGraph    12.1.9 但内部依赖 Core 12.1.15
```

这种会有潜在问题。

---

## 你现在最可疑的点

你这个目录叫：

```text
LocalPackages/com.unity.shadergraph@12.1.9
```

但它内部依赖的是：

```text
com.unity.render-pipelines.core 12.1.15
```

这说明可能有两种情况：

### 情况 A：你复制错了包

你可能复制的是：

```text
com.unity.shadergraph@12.1.15
```

但目录改名成了：

```text
com.unity.shadergraph@12.1.9
```

这种不建议。Unity 真正认的是包里的 `package.json`，不是只看文件夹名。

---

### 情况 B：`package.json` 被改过

打开这个文件：

```text
LocalPackages/com.unity.shadergraph@12.1.9/package.json
```

看里面：

```json
"version": "?"
```

如果里面是：

```json
"version": "12.1.15"
```

那它其实不是 12.1.9，只是文件夹名叫 12.1.9。

如果里面是：

```json
"version": "12.1.9"
```

但依赖写着：

```json
"com.unity.render-pipelines.core": "12.1.15"
```

那也不太正常，建议换一个干净的 ShaderGraph 12.1.9 包。

---

## 推荐你现在这样处理

如果你要保留本地 URP/Core 12.1.9，就应该准备真正的 ShaderGraph 12.1.9。

`manifest.json` 写成：

```json
"com.unity.render-pipelines.core": "file:../LocalPackages/com.unity.render-pipelines.core@12.1.9",
"com.unity.render-pipelines.universal": "file:../LocalPackages/com.unity.render-pipelines.universal@12.1.9",
"com.unity.shadergraph": "file:../LocalPackages/com.unity.shadergraph@12.1.9"
```

然后确认：

```text
LocalPackages/com.unity.shadergraph@12.1.9/package.json
```

里面应该接近：

```json
{
  "name": "com.unity.shadergraph",
  "version": "12.1.9",
  "dependencies": {
    "com.unity.render-pipelines.core": "12.1.9",
    "com.unity.searcher": "4.9.2"
  }
}
```

如果它写的是 `12.1.15`，建议不要手改版本号凑合，最好重新拿一份干净的 `com.unity.shadergraph@12.1.9`。

---

## 改完后清理

关闭 Unity，删：

```text
Packages/packages-lock.json
Library/PackageCache
Library/ScriptAssemblies
Library/Bee
```

再重新打开 Unity。

一句话：**12.1.9 和 12.1.15 虽然都是补丁版本，但 SRP/Core/URP/ShaderGraph 这种包最好精确对齐，不要混。**

