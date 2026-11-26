# LOD切换优化方案

会话 ID：`6a2bf2c0-09b8-83ea-8d0b-298312d8ce58`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 bdb963e2-4cdf-43c2-8a4d-c6d02d18067a

### 用户

频繁切换LOD会导致大量Vertex Buffer和IndexBuffer的上传，可以考虑把多个LOD级别打包到一个Buffer里，用offset 切换而不是重新绑定。

### 助手

你说的这句话，本质上是在描述**现代游戏引擎处理 LOD 的一种优化方案**，但里面有一点需要澄清。

> **频繁切换LOD会导致大量Vertex Buffer和Index Buffer上传，可以考虑把多个LOD级别打包到一个Buffer里，用offset切换而不是重新绑定。**

严格来说，这句话**前半句不完全准确，后半句是业内常见优化。**

---

## 先说什么是真正昂贵的

GPU绘制时，一个Mesh通常对应：

```
VertexBuffer(VB)
IndexBuffer(IB)

LOD0
    VertexBuffer
    IndexBuffer

LOD1
    VertexBuffer
    IndexBuffer

LOD2
    VertexBuffer
    IndexBuffer
```

假设一个角色：

```
LOD0
10000 vertices

LOD1
4000 vertices

LOD2
1000 vertices
```

如果每次LOD切换：

```
Bind VB0
Bind IB0

↓

Bind VB1
Bind IB1

↓

Bind VB2
Bind IB2
```

GPU Command Buffer里面会不断出现

```
BindVertexBuffer
BindIndexBuffer
DrawIndexed
```

这里**真正的问题一般不是"上传(upload)"。**

因为：

> **Vertex Buffer一般早就在GPU显存里。**

LOD切换通常不会：

```
CPU → GPU
重新上传整个VB
```

而只是：

```
GPU切换绑定对象
```

所以更准确应该说：

> **频繁切换LOD导致频繁Buffer Bind，而不是频繁Buffer Upload。**

---

## 什么情况下真的会Upload？

只有下面几种情况：

### ① Streaming Mesh

例如：

```
AssetBundle
↓

LOD0没加载

↓

需要加载

↓

CPU读磁盘

↓

上传GPU
```

这里才发生

```
Upload VB
Upload IB
```

Unity里就是：

```
Mesh.UploadMeshData()
```

或者驱动自动创建GPU Buffer。

---

### ② Dynamic Mesh

例如：

```
Cloth

Skinned Mesh

Runtime Mesh
```

每帧：

```
CPU修改Vertex

↓

Upload到GPU
```

这也是Upload。

---

### ③ Buffer Eviction

显存不足：

```
GPU把VB踢出去

↓

再次使用

↓

重新上传
```

这种比较少见。

---

## 为什么业内喜欢把LOD放到一个Buffer？

这是现在很多AAA引擎都会做的。

例如：

```
一个Vertex Buffer

----------------------------------
LOD0 Vertex
LOD1 Vertex
LOD2 Vertex
----------------------------------
```

Index Buffer：

```
----------------------------------
LOD0 Index
LOD1 Index
LOD2 Index
----------------------------------
```

GPU里其实只有：

```
VB

IB
```

永远绑定一次。

---

## Draw的时候只改Offset

例如：

LOD0：

```
VB Offset = 0

IB Offset = 0

IndexCount = 18000
```

LOD1：

```
VB Offset = 10000 vertices

IB Offset = 18000 indices

IndexCount = 7000
```

LOD2：

```
VB Offset = 14000 vertices

IB Offset = 25000 indices

IndexCount = 1500
```

GPU Draw：

```
DrawIndexed(
    IndexCount,
    StartIndexLocation,
    BaseVertexLocation
)
```

实际上：

```
StartIndexLocation

BaseVertexLocation
```

就是Offset。

所以：

不用

```
Bind VB

Bind IB
```

只需要

```
DrawIndexed(...)
```

参数不同。

---

## 为什么这样更快？

因为GPU最讨厌：

```
State Change
```

例如：

```
Bind Texture

Bind Shader

Bind VB

Bind IB
```

这些都会：

```
Driver Validation

Pipeline Flush

Command生成
```

如果：

```
Bind一次

↓

Draw100次
```

远比：

```
Bind100次

↓

Draw100次
```

效率高。

---

## Unity里有没有类似？

Unity底层（尤其是基于现代图形 API）也会尽量减少状态切换，但普通导入的 Mesh 通常还是各自拥有自己的 Vertex Buffer 和 Index Buffer。

例如：

```
Mesh

LOD0

Mesh

LOD1

Mesh

LOD2
```

每个都是独立Mesh。

LODGroup切换时：

```
Renderer

↓

换Mesh
```

底层通常需要重新绑定Buffer。

---

而像：

- Unreal Engine（尤其是新版本）
- Frostbite
- id Tech
- RE Engine
- Decima

都会大量使用：

```
Mesh Cluster

Meshlet

Unified Buffer

GPU Scene
```

把很多Mesh甚至很多LOD：

```
放一个大Buffer
```

GPU只改：

```
Offset

Count
```

基本不重新Bind。

---

## 面试中可以怎么回答？

可以概括为：

> LOD切换本身通常不会导致 Vertex Buffer 或 Index Buffer 重新上传到 GPU，因为这些数据一般已经驻留在显存中。真正的开销更多来自频繁的资源绑定（Bind）和状态切换。如果 LOD 数据分别存放在多个 Buffer 中，每次切换都需要重新绑定 VB/IB。业内常见优化是将多个 LOD 打包到同一个 Vertex Buffer 和 Index Buffer 中，绘制时仅调整 BaseVertexLocation、StartIndexLocation 和 IndexCount 等偏移参数，从而减少 Buffer Bind 和 Driver State Change，提高渲染效率。对于现代渲染架构，还会进一步结合 GPU Scene、Mesh Cluster、Meshlet 或 Indirect Draw 等技术，将大量对象的绘制合并到统一的大 Buffer 中，以进一步降低 CPU 提交开销。

