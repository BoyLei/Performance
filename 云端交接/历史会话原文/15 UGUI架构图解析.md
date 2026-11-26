# UGUI架构图解析

会话 ID：`6a34e381-71a8-83ea-8c4d-6b07d98868e2`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 0804e3fe-f204-4d5a-a4f8-55361ccccf52

### 用户

帮我画出Ugui 的架构图

### 助手

我给你画一张**UGUI（Unity UI）核心架构图**，按“输入 → 射线 → UI系统 → 渲染 → 布局/重建”拆开看，会更清晰：

---

## 🧠 UGUI 架构图（核心链路）

```text
                         ┌────────────────────────┐
                         │      EventSystem        │
                         │ (事件系统入口)          │
                         └──────────┬─────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
     ┌──────────────────────────┐     ┌──────────────────────────┐
     │ InputModule              │     │ GraphicRaycaster         │
     │ (输入处理)              │     │ (UI射线检测)            │
     └──────────┬──────────────┘     └──────────┬──────────────┘
                │                                │
        鼠标/触摸输入                    屏幕Point → Raycast
                │                                │
                └──────────────┬─────────────────┘
                               │
                     ┌─────────▼──────────┐
                     │  Raycast Results   │
                     │ (UI命中列表排序)   │
                     └─────────┬──────────┘
                               │
                               ▼
                      ┌─────────────────┐
                      │ UI Element      │
                      │ (Button/Image…) │
                      └────────┬────────┘
                               │
                   ┌───────────▼───────────┐
                   │ Graphic (核心基类)    │
                   │ Image / Text / etc    │
                   └───────────┬───────────┘
                               │
                      ┌────────▼────────┐
                      │ CanvasRenderer   │
                      │ (网格提交层)    │
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │ Canvas Mesh     │
                      │ (UI顶点数据)    │
                      └────────┬────────┘
                               │
                               ▼
                        GPU 渲染输出

────────────────────────────────────────────────────────

            ┌──────────────────────────────────┐
            │           Canvas System          │
            │  - Screen Space Overlay         │
            │  - Screen Space Camera          │
            │  - World Space                 │
            └──────────────┬───────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
RectTransform      Layout System      Rebuild System
   (UI坐标)       (自动布局)        (脏标记重建)
        │              │                  │
        │      LayoutGroup / Fitter      │
        │              │                  │
        └──────────────┴──────────────────┘
                     驱动 UI 变化

────────────────────────────────────────────────────────
关键机制：
- SetDirty → 触发重建
- LayoutRebuilder → 重新计算UI布局
- CanvasBatching → 合批减少DrawCall
```

---

## ⚙️ 一句话理解UGUI

UGUI本质是三层：

- **输入层**：EventSystem + Raycaster（解决“点到谁”）
- **逻辑层**：RectTransform + Layout（解决“摆在哪”）
- **渲染层**：Graphic → CanvasRenderer → Mesh（解决“怎么画”）

---

如果你想，我可以再帮你画一版更“源码级”的，比如：

- EventSystem排序源码流程
- Graphic.UpdateGeometry / UpdateVertex
- Canvas rebuild dirty flag 全链路
- 或者 UI DrawCall 合批机制图

直接说你要哪一层深入就行。

