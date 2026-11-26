# Unity Shader Variants

会话 ID：`6a2fa0ca-5284-83ea-a783-95d29aa9fa08`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 d3352e47-ac9e-4273-8e8b-2dd3f3b74522

### 用户

unity的变体以及使用方法

### 助手

Unity 中的 **Shader Variant（Shader 变体）** 是 Unity 渲染性能优化里最重要，也是最容易踩坑的内容之一。很多项目启动慢、打包大、切换场景卡顿，都和 Shader Variant 有关。

下面我从**原理 → 使用 → 优化 → 实战**几个方面讲清楚。

---

# 什么是 Shader Variant（变体）

一个 Shader 并不是只编译出一个 GPU Program。

例如：

```shader
#pragma multi_compile _ USE_FOG
#pragma multi_compile _ USE_SHADOW
#pragma multi_compile _ USE_LIGHTMAP
```

Unity 会生成：

```
Fog Shadow Lightmap
---------------------
0    0      0
1    0      0
0    1      0
0    0      1
1    1      0
1    0      1
0    1      1
1    1      1
```

也就是：

```
2 × 2 × 2 = 8 个 Variant
```

Unity 会分别编译成 8 个 GPU Program。

运行时：

```
材质开启阴影
↓

Shader.EnableKeyword("USE_SHADOW")

↓

Unity 自动切换到对应 Variant
```

所以：

> **Variant 本质就是 Shader 的不同编译结果。**

---

# 为什么需要 Variant？

例如：

一个角色：

有时：

```
没有法线
```

有时：

```
有法线
```

有时：

```
有Emission
```

有时：

```
有Lightmap
```

如果全部写：

```hlsl
if(enableNormal)
```

GPU 每个像素都要判断。

而 Variant：

```
Normal版本
```

里面直接：

```hlsl
计算Normal
```

没有：

```hlsl
if
```

另一个 Variant：

直接没有 Normal 代码。

GPU 更快。

---

# Variant 是怎么生成的？

例如：

```shader
#pragma multi_compile _ USE_FOG
```

Unity 会：

生成：

```
Variant1

没有 USE_FOG
```

再生成：

```
Variant2

#define USE_FOG
```

Shader：

```hlsl
#ifdef USE_FOG
    color = ApplyFog(color);
#endif
```

编译后：

Variant A：

```hlsl
color = color;
```

Variant B：

```hlsl
color = ApplyFog(color);
```

已经不是运行时判断了。

---

# 常见 Variant 指令

## ① multi_compile

最常见。

例如：

```shader
#pragma multi_compile _ USE_NORMALMAP
```

生成：

```
没有Keyword

有Keyword
```

特点：

**永远编译。**

即使没人用：

也编译。

---

例如：

```shader
#pragma multi_compile _ A B C
```

生成：

```
_

A

B

C
```

四个 Variant。

---

## ② shader_feature

最推荐。

例如：

```shader
#pragma shader_feature _ USE_EMISSION
```

特点：

**只有使用到才编译。**

如果：

项目所有 Material：

都没有开启：

```
USE_EMISSION
```

打包：

不会编译。

所以：

移动端推荐：

```
shader_feature
```

而不是：

```
multi_compile
```

---

## ③ shader_feature_local

Unity 后期加入。

作用：

Keyword 不会污染全局。

例如：

```
角色Shader

USE_NORMAL
```

UI Shader

```
USE_NORMAL
```

不会冲突。

推荐：

```
shader_feature_local
```

---

## ④ multi_compile_local

和上面一样。

只是：

一定编译。

---

# Variant 数量如何计算？

例如：

```shader
#pragma shader_feature _ A
#pragma shader_feature _ B
#pragma shader_feature _ C
```

每个：

```
2
```

所以：

```
2 × 2 × 2 = 8
```

再来：

```shader
#pragma shader_feature _ D
```

变成：

```
16
```

再：

```
#pragma multi_compile _ E
```

变：

```
32
```

Variant 是指数增长。

公式：

```
总Variant

=

所有Keyword数量相乘
```

例如：

```
2
×

3
×

4
×

2
=

48
```

---

# Variant Explosion（变体爆炸）

很多项目：

Shader：

```
20 个Keyword
```

那么：

```
2^20

≈100万
```

Unity：

可能要编译：

几十万 Variant。

表现：

- 导入 Shader 十几分钟
- 打包几十分钟
- Build 几 GB
- 首次进入卡顿
- Shader Warmup 卡

---

# 如何控制 Variant 数量？

## 方法一：优先使用 shader_feature

不要：

```shader
#pragma multi_compile
```

改：

```shader
#pragma shader_feature
```

能少很多。

---

## 方法二：删除不用 Keyword

例如：

```
USE_DETAIL

USE_FOG

USE_SNOW

USE_RAIN

USE_PARALLAX
```

如果：

项目不用：

直接删。

---

## 方法三：使用 Local Keyword

```shader
shader_feature_local
```

减少全局 Keyword。

---

## 方法四：Variant Stripping

Unity Build：

会删除：

```
没有使用的 Variant
```

例如：

关闭：

```
Fog
```

所有 Fog Variant：

全部 Strip。

URP/HDRP 都支持配置变体裁剪（Stripping）。

---

## 方法五：Shader Variant Collection（SVC）

如果：

游戏运行：

第一次：

```
切武器
```

突然：

卡一下。

原因：

首次加载：

Variant。

可以提前收集。

Unity：

```
Assets

Create

Shader Variant Collection
```

然后：

```
WarmUp()
```

运行：

```csharp
variantCollection.WarmUp();
```

第一次：

全部编译。

之后：

不卡。

---

# Shader Keyword 怎么切换？

例如：

```csharp
material.EnableKeyword("USE_EMISSION");
```

关闭：

```csharp
material.DisableKeyword("USE_EMISSION");
```

Unity：

自动：

```
查找对应 Variant
```

切换 GPU Program。

---

也可以：

全局：

```csharp
Shader.EnableKeyword("FOG_LINEAR");
```

所有 Shader：

都会变化。

不过现在更推荐使用 **Local Keywords（材质局部关键字）**，避免全局关键字带来的状态污染和维护成本。

---

# 面试最常问的问题

### Q1：`multi_compile` 和 `shader_feature` 有什么区别？

| 特性 | multi_compile | shader_feature |
|------|---------------|----------------|
| 是否全部编译 | ✅ 是 | ❌ 否，仅编译实际使用的变体 |
| 是否适合运行时动态切换 | ✅ 是 | ⚠️ 仅能切换已编译进包的变体 |
| 打包体积 | 大 | 小 |
| 推荐场景 | 引擎功能、平台相关、运行时必须支持所有组合 | 游戏业务功能、材质功能开关 |

---

### Q2：为什么第一次切换材质会卡顿？

因为对应 Variant 第一次加载/创建 GPU Pipeline 或驱动程序缓存时，需要一定时间，容易造成首帧卡顿。可以通过 **Shader Variant Collection**、预热（WarmUp）或在加载阶段提前使用这些变体来降低影响。

---

### Q3：为什么项目里的 Shader Variant 数量会爆炸？

主要原因有：

- 大量 `multi_compile`
- 多个关键字相互组合，数量呈指数增长
- 引擎内置关键字（阴影、光照、雾、光照贴图等）与自定义关键字叠加
- 使用了包含大量可选功能的通用 Shader

---

## 一个实际项目的建议

对于绝大多数 Unity 项目，可以遵循这套原则：

- **游戏功能开关**（如描边、溶解、发光）：使用 `shader_feature_local`
- **必须支持所有组合的运行时功能**：使用 `multi_compile` 或 `multi_compile_local`
- **尽量减少 Keyword 数量**，避免指数级增长
- **构建时启用 Variant Stripping**，删除不会使用的变体
- **对首帧会用到的重要 Shader 建立 Shader Variant Collection 并预热**，减少运行时首次切换造成的卡顿

掌握这些内容后，你基本就覆盖了 Unity Shader Variant 在项目开发和技术面试中的核心知识点。

## 轮次 fc38155a-ecfb-4c5e-89b6-076048a93008

### 用户

什么是prefab变体

### 助手

Prefab Variant（**Prefab 变体**）和 Shader Variant 完全不是一个概念。

Prefab Variant 是 Unity 为了解决**大量相似 Prefab 的复用问题**而设计的，类似于**面向对象里的继承（Inheritance）**。

---

## 什么是 Prefab Variant？

假设你有一个敌人：

```
Enemy.prefab
```

它包含：

```
Enemy
├── Animator
├── Rigidbody
├── Collider
├── EnemyAI
├── HP = 100
├── Speed = 5
```

现在需要制作：

```
普通敌人
精英敌人
Boss
```

如果直接复制：

```
Ctrl + C

Ctrl + V

Enemy_Copy.prefab
```

以后修改：

例如：

```
EnemyAI
```

需要：

```
修改普通

修改精英

修改Boss
```

非常麻烦。

所以就有了 **Prefab Variant**。

---

# Prefab Variant 的关系

```
Enemy.prefab
        │
        ├────────────┐
        │            │
EliteEnemy.variant   Boss.variant
```

它们共享：

```
Enemy.prefab
```

只有不同的地方单独保存。

例如：

父 Prefab：

```
HP = 100
Speed = 5
```

Elite：

```
HP = 300
```

Boss：

```
HP = 5000
Speed = 2
```

真正保存的是：

```
Boss

修改：
HP
Speed
```

其它全部来自父 Prefab。

---

# 修改父 Prefab

例如：

Enemy：

增加：

```
AudioSource
```

保存。

所有 Variant：

```
Elite

Boss

Monster

Zombie
```

全部自动拥有：

```
AudioSource
```

不用一个一个修改。

这就是最大的价值。

---

# 可以修改哪些内容？

Variant 可以覆盖（Override）父 Prefab 的很多内容，例如：

### 1. 修改 Inspector 参数

例如：

```
Enemy

HP =100
```

Variant：

```
HP =500
```

即可。

---

### 2. 修改材质

父：

```
Red Material
```

Variant：

```
Blue Material
```

允许。

---

### 3. 修改组件参数

例如：

```
NavMeshAgent

Speed=3
```

Variant：

```
Speed=10
```

允许。

---

### 4. 添加新的组件

例如：

父：

```
Animator
```

Variant：

增加：

```
AudioSource
```

允许。

---

### 5. 添加子节点

例如：

父：

```
Enemy
├── Body
```

Variant：

```
Enemy
├── Body
└── FireEffect
```

允许。

---

# 哪些不能修改？

例如：

父：

```
Enemy
├── Body
```

不能直接：

```
删除 Body
```

因为：

```
Body
```

属于父 Prefab。

Variant 不能真正删除父对象。

如果确实不需要，可以：

```
SetActive(false)
```

或者修改父 Prefab。

---

# Override（覆盖）

Unity Inspector 会显示：

```
Overrides
```

例如：

父：

```
Speed=5
```

Variant：

```
Speed=10
```

Unity 会记录：

```
Override

Speed
```

如果：

```
Revert
```

立即恢复：

```
5
```

因为：

数据来自父 Prefab。

---

# 创建 Variant

方法一：

右键：

```
Create

Prefab Variant
```

---

方法二：

Project：

```
右键Prefab

Create

Prefab Variant
```

---

方法三：

Hierarchy：

```
拖已有Prefab

右键

Create Variant
```

（不同 Unity 版本菜单位置可能略有差异。）

---

# Variant 与复制 Prefab 的区别

| 功能 | Prefab Copy | Prefab Variant |
|------|-------------|----------------|
| 与原 Prefab 保持关联 | ❌ | ✅ |
| 父 Prefab 修改会同步 | ❌ | ✅ |
| 仅保存差异 | ❌（完整拷贝） | ✅ |
| 后期维护成本 | 高 | 低 |

---

# 实际项目中的使用场景

### 场景一：不同类型敌人

```
Enemy.prefab
    │
    ├── Soldier
    ├── Archer
    ├── Mage
    ├── Boss
```

共同：

```
AI
动画
受击
死亡
```

不同：

```
HP
技能
速度
模型
```

---

### 场景二：UI 按钮

```
Button.prefab
        │
        ├── RedButton
        ├── BlueButton
        ├── GoldButton
```

共同：

```
Button
Text
Animation
```

不同：

```
Sprite
字体颜色
```

---

### 场景三：武器

```
Weapon.prefab
      │
      ├── Sword
      ├── Axe
      ├── Spear
```

共同：

```
Pickup
Collider
WeaponLogic
```

不同：

```
Mesh
Damage
Icon
```

---

# 面试常见问题

**Q：Prefab Variant 和 Prefab 有什么区别？**

- **Prefab** 是模板，定义对象的默认结构和属性。
- **Prefab Variant** 是基于某个 Prefab 创建的派生版本，只保存与父 Prefab 的差异（Override），并继承父 Prefab 的后续修改。

**Q：什么时候使用 Prefab Variant？**

当多个对象拥有**相同的基础结构和逻辑**，但只有少量配置不同（例如数值、材质、模型、特效）时，使用 Prefab Variant 可以显著降低维护成本，避免复制大量重复 Prefab。

**Q：Prefab Variant 的本质是什么？**

可以把它理解为一种**配置层面的继承机制**：

- 父 Prefab 提供公共内容。
- Variant 记录覆盖项（Overrides）。
- 加载时 Unity 将父 Prefab 与 Variant 的覆盖数据合并，生成最终实例。

对于大型 Unity 项目（尤其是角色、UI、武器、NPC 等资源），Prefab Variant 是管理资源复用和降低维护成本的重要工具。

## 轮次 d74d28a7-96a7-4666-81a5-e45c99463998

### 用户

父预制体没被使用，会被打包进去吗

### 助手

答案是：**一般情况下，会。** 但要分情况来看。

---

## 情况一：父 Prefab 只有 Variant 在使用（最常见）

例如：

```
Enemy.prefab          （父）
      │
      ├── Elite.variant
      ├── Boss.variant
```

场景里只有：

```
Boss.variant
```

没有：

```
Enemy.prefab
```

**最终打包：**

```
✔ Enemy.prefab
✔ Boss.variant
```

原因：

Prefab Variant **不是完整的数据**，它只保存 Override（差异）。

例如：

父 Prefab：

```
Mesh
Animator
Collider
EnemyAI
HP=100
```

Variant 只保存：

```
HP=500
```

运行时 Unity 需要：

```
加载 Enemy.prefab
        ↓
应用 Override
        ↓
得到 Boss
```

所以：

> **父 Prefab 是 Variant 的依赖（Dependency），只要 Variant 被打包，父 Prefab 也必须一起打包。**

---

## 情况二：父 Prefab 和 Variant 都没引用

例如：

```
Enemy.prefab
Boss.variant
```

既没有：

- 场景引用
- Resources 引用
- Addressables 引用
- AssetBundle 引用

那么：

```
不会打包
```

Unity 不会把没人引用的资源打进去。

---

## 情况三：使用 Addressables 或 AssetBundle

这是很多项目容易踩坑的地方。

例如：

```
Enemy.prefab

Boss.variant
```

你把：

```
Boss.variant
```

放进一个 AssetBundle。

Unity 会分析依赖：

```
Boss.variant
      │
      └── Enemy.prefab
```

通常会把父 Prefab 当作依赖一起打包，或者放入共享依赖 Bundle（具体取决于你的打包配置）。

如果没有正确处理依赖，就可能出现运行时报错：

```
Missing Prefab Source
```

或者：

```
The Prefab Variant cannot find its base Prefab.
```

---

## 情况四：Build Pipeline 自动分析依赖

Unity 在 Build 时会做依赖分析。

例如：

```
Scene
    ↓
Boss Variant
    ↓
Enemy Prefab
    ↓
Mesh
    ↓
Material
    ↓
Texture
```

最终会把整条依赖链都打包进去：

```
Scene
Boss Variant
Enemy Prefab
Mesh
Material
Texture
```

---

# 面试经常会问

**问：父 Prefab 没有直接放进场景，还会被打包吗？**

回答：

> **如果有 Prefab Variant 引用了它，就会。因为 Variant 只保存差异数据，运行时必须依赖父 Prefab 才能还原完整对象。Unity 在构建时会自动分析资源依赖，把父 Prefab 一起打包。**

---

## 一个简单的理解

可以把 Prefab Variant 想象成一个"补丁文件"：

```
Enemy.prefab
```

保存了完整内容：

```
100KB
```

Boss Variant：

```
只保存：

HP=5000
颜色=红色

只有几 KB
```

运行时：

```
Enemy.prefab
      +
Boss 的 Override
      ↓
完整 Boss
```

因此，**只要 Variant 存在且被打包，父 Prefab 就不能缺失，否则 Variant 无法正常实例化。**

