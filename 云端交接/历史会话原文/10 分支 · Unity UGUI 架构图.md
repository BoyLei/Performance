# 分支 · Unity UGUI 架构图

会话 ID：`6a5dadfb-17e4-83ee-b047-74741ede7e2a`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 99b8773d-4323-41f4-a67b-8ebd5058543e

### 用户

拆开,不要合并成一张, 同时验证它的 正确性 和 完整性, 表现性最好好看一点

### 助手

下面按模块拆开给出 5 张独立架构图。每张图都按 uGUI 官方源码关系重新核对过，并把容易画错的点单独标出来。

### 模块 3：Layout 布局系统

校验要点：  
`ContentSizeFitter`、`AspectRatioFitter` 都属于 `ILayoutSelfController`，不是 `ILayoutElement`。`HorizontalLayoutGroup`、`VerticalLayoutGroup`、`GridLayoutGroup` 属于 `ILayoutGroup`。`GridLayoutGroup` 使用统一 `cellSize`，子节点尺寸不会反过来决定单元格大小。    

```mermaid
flowchart TB
    classDef core fill:#e8f0ff,stroke:#4a78d0,stroke-width:1.4px,color:#111;
    classDef impl fill:#eef9f0,stroke:#3f8f5a,stroke-width:1.2px,color:#111;
    classDef note fill:#fff7df,stroke:#c7a63a,stroke-width:1.1px,color:#111;
    classDef warn fill:#fff1f0,stroke:#d06a5f,stroke-width:1.1px,color:#111;

    A[RectTransform / 子节点 / 属性变化]:::core --> B[LayoutRebuilder.MarkLayoutForRebuild]:::core
    B --> C[沿父链寻找最高有效布局根]:::core
    C --> D[加入 CanvasUpdateRegistry 的 Layout 队列]:::core
    D --> E[CanvasUpdate.Layout 阶段执行重建]:::core

    E --> F1[1. CalculateLayoutInputHorizontal<br/>自底向上]:::core
    F1 --> F2[2. SetLayoutHorizontal<br/>自顶向下]:::core
    F2 --> F3[3. CalculateLayoutInputVertical<br/>自底向上]:::core
    F3 --> F4[4. SetLayoutVertical<br/>自顶向下]:::core
    F4 --> G[更新自身或子节点 RectTransform]:::core

    subgraph Provider[尺寸提供者：ILayoutElement]
        direction TB
        P0[ILayoutElement]:::impl
        P1[LayoutElement]:::impl
        P2[Image / Text]:::impl
        P3[InputField]:::impl
        P4[LayoutGroup]:::impl
        P5[ScrollRect]:::impl
        P0 --> P1
        P0 --> P2
        P0 --> P3
        P0 --> P4
        P0 --> P5
    end

    subgraph Controller[布局控制者：ILayoutController]
        direction TB
        C0[ILayoutController]:::impl
        C1[ILayoutSelfController]:::impl
        C2[ILayoutGroup]:::impl
        C0 --> C1
        C0 --> C2

        C11[ContentSizeFitter]:::impl
        C12[AspectRatioFitter]:::impl
        C21[HorizontalLayoutGroup]:::impl
        C22[VerticalLayoutGroup]:::impl
        C23[GridLayoutGroup]:::impl
        C24[ScrollRect]:::impl

        C1 --> C11
        C1 --> C12
        C2 --> C21
        C2 --> C22
        C2 --> C23
        C2 --> C24
    end

    F1 -.读取尺寸.-> Provider
    F3 -.读取尺寸.-> Provider
    F2 -.先调用 SelfController.-> C1
    F2 -.后调用其他 Controller.-> C2
    F4 -.先调用 SelfController.-> C1
    F4 -.后调用其他 Controller.-> C2

    H[LayoutGroup 先收集 rectChildren]:::note --> I{ignoreLayout = true?}:::note
    I -->|是| J[跳过该子节点]:::warn
    I -->|否| K[参与布局计算]:::note
    K --> C21
    K --> C22
    K --> C23

    N1[关键修正：<br/>ContentSizeFitter / AspectRatioFitter<br/>不是 ILayoutElement]:::warn
    N2[关键修正：<br/>GridLayoutGroup 的 cellSize 由自己决定]:::warn
```

---

### 模块 4：Graphic 网格与材质渲染

校验要点：  
`Graphic` 通过 `CanvasUpdateRegistry` 进入图形重建；顶点脏走 `UpdateGeometry`，材质脏走 `UpdateMaterial`。几何生成后会调用同对象上的 `IMeshModifier.ModifyMesh`，材质会通过 `IMaterialModifier.GetModifiedMaterial` 链式修改，然后交给 `CanvasRenderer`。  

```mermaid
flowchart TB
    classDef core fill:#e8f0ff,stroke:#4a78d0,stroke-width:1.4px,color:#111;
    classDef impl fill:#eef9f0,stroke:#3f8f5a,stroke-width:1.2px,color:#111;
    classDef note fill:#fff7df,stroke:#c7a63a,stroke-width:1.1px,color:#111;
    classDef warn fill:#fff1f0,stroke:#d06a5f,stroke-width:1.1px,color:#111;

    A[Graphic 属性 / 尺寸 / 纹理 / 状态变化]:::core --> B{Dirty 类型}:::core
    B -->|顶点| C1[SetVerticesDirty]:::core
    B -->|材质| C2[SetMaterialDirty]:::core
    B -->|布局| C3[SetLayoutDirty]:::core

    C1 --> D[CanvasUpdateRegistry 图形队列]:::core
    C2 --> D
    D --> E[CanvasUpdate.PreRender]:::core
    E --> F[Graphic.Rebuild]:::core

    F --> G1{m_VertsDirty?}:::core
    G1 -->|是| H1[UpdateGeometry]:::core
    H1 --> I1[OnPopulateMesh(VertexHelper)]:::core
    I1 --> J1[Graphic / Image / RawImage / Text<br/>各自生成顶点]:::impl
    J1 --> K1[依次调用 IMeshModifier.ModifyMesh]:::impl
    K1 --> L1[VertexHelper.FillMesh(workerMesh)]:::core
    L1 --> M1[CanvasRenderer.SetMesh]:::core

    F --> G2{m_MaterialDirty?}:::core
    G2 -->|是| H2[UpdateMaterial]:::core
    H2 --> I2[获得 base material]:::core
    I2 --> J2[materialForRendering<br/>遍历 IMaterialModifier 链]:::impl
    J2 --> K2[CanvasRenderer.SetMaterial]:::core
    K2 --> L2[CanvasRenderer.SetTexture(mainTexture)]:::core

    subgraph VisualTypes[主要显示组件]
        direction TB
        V1[Graphic]:::impl
        V2[MaskableGraphic]:::impl
        V3[Image]:::impl
        V4[RawImage]:::impl
        V5[Legacy Text]:::impl
        V1 --> V2
        V2 --> V3
        V2 --> V4
        V2 --> V5
    end

    J1 -.由具体类型实现.-> VisualTypes
    J2 -.常见修改者.-> N1[Mask / MaskableGraphic]:::note

    M1 --> R[CanvasRenderer]:::core
    L2 --> R
    R --> S[Unity 原生 UI 渲染层]:::core
    S --> T[最终提交到渲染管线 / GPU]:::core

    W1[GraphicRegistry 维护 Canvas 下 Graphic 集合<br/>主要给 GraphicRaycaster 用]:::note
    W2[注意：GraphicRegistry 不是重建队列]:::warn
```

---

### 模块 5：EventSystem 输入、射线与事件派发

校验要点：  
`StandaloneInputModule.Process` 的真实顺序是：先 `SendUpdateEventToSelectedObject`，再处理触摸或鼠标，最后才是导航的 `Move / Submit / Cancel`。命中对象来自 `EventSystem.RaycastAll`，而派发依赖 `ExecuteEvents.Execute / ExecuteHierarchy / GetEventHandler`。   

```mermaid
flowchart TB
    classDef core fill:#e8f0ff,stroke:#4a78d0,stroke-width:1.4px,color:#111;
    classDef impl fill:#eef9f0,stroke:#3f8f5a,stroke-width:1.2px,color:#111;
    classDef note fill:#fff7df,stroke:#c7a63a,stroke-width:1.1px,color:#111;
    classDef warn fill:#fff1f0,stroke:#d06a5f,stroke-width:1.1px,color:#111;

    A[EventSystem.Update]:::core --> B[UpdateModule 所有模块]:::core
    B --> C[选择当前活动 InputModule]:::core
    C --> D[BaseInputModule.Process]:::core
    D --> E[StandaloneInputModule.Process]:::core

    E --> E1[1. SendUpdateEventToSelectedObject]:::core
    E1 --> E2[2. ProcessTouchEvents<br/>没有触摸则 ProcessMouseEvent]:::core
    E2 --> E3[3. SendMoveEventToSelectedObject]:::core
    E3 --> E4[4. SendSubmitEventToSelectedObject]:::core

    E2 --> F[创建 / 复用 PointerEventData]:::core
    F --> G[EventSystem.RaycastAll]:::core
    G --> H[遍历所有活动 BaseRaycaster]:::core

    subgraph Raycasters[Raycaster 分支]
        direction TB
        R1[GraphicRaycaster]:::impl
        R2[PhysicsRaycaster]:::impl
        R3[Physics2DRaycaster]:::impl
    end

    H --> R1
    H --> R2
    H --> R3

    R1 --> I1[GraphicRegistry 取 Canvas 下 Graphics]:::core
    I1 --> I2[过滤 raycastTarget / cull / depth / Rect]:::core
    I2 --> I3[Graphic.Raycast]:::core
    I3 --> I4[父链检查 ICanvasRaycastFilter<br/>Image / Mask / RectMask2D / CanvasGroup]:::core
    I4 --> I5[按 depth 降序]:::core

    R2 --> J1[3D Physics Raycast]:::core
    R3 --> J2[2D Physics Raycast]:::core

    I5 --> K[RaycastResult 汇总并全局排序]:::core
    J1 --> K
    J2 --> K
    K --> L[FindFirstRaycast 得到首个命中对象]:::core

    L --> M{本帧输入状态}:::core
    M -->|移动| N1[HandlePointerExitAndEnter]:::core
    M -->|按下| N2[PointerDown<br/>找不到则回退到 ClickHandler]:::core
    M -->|拖拽| N3[BeginDrag → Drag]:::core
    M -->|释放| N4[PointerUp → Click 或 Drop → EndDrag]:::core

    N1 --> P[ExecuteEvents]:::core
    N2 --> P
    N3 --> P
    N4 --> P
    E1 --> P
    E3 --> P
    E4 --> P

    P --> Q1[Execute<br/>只发给目标对象上的所有匹配处理器]:::core
    P --> Q2[ExecuteHierarchy<br/>沿父链找到第一个能处理的对象]:::core
    P --> Q3[GetEventHandler<br/>沿父链找可处理对象]:::core
    Q1 --> Z[IEventSystemHandler 组件]:::impl
    Q2 --> Z
    Q3 --> Z

    W[关键修正：导航事件不是最先处理，<br/>而是在触摸 / 鼠标之后]:::warn
```

---

### 模块 6：Mask 与 RectMask2D 遮罩裁剪

校验要点：  
`Mask` 和 `RectMask2D` 是两条不同机制。`Mask` 走 `IMaterialModifier + StencilMaterial`，会生成 mask / unmask 材质并配置 `CanvasRenderer` 的 pop material。`RectMask2D` 走 `IClipper.PerformClipping`，计算矩形裁剪区域，向子级传播 `SetClipRect / Cull / SetClipSoftness`。  

```mermaid
flowchart TB
    classDef core fill:#e8f0ff,stroke:#4a78d0,stroke-width:1.4px,color:#111;
    classDef impl fill:#eef9f0,stroke:#3f8f5a,stroke-width:1.2px,color:#111;
    classDef note fill:#fff7df,stroke:#c7a63a,stroke-width:1.1px,color:#111;
    classDef warn fill:#fff1f0,stroke:#d06a5f,stroke-width:1.1px,color:#111;

    A{遮罩类型}:::core

    subgraph S1[路径 A：Mask（Stencil）]
        direction TB
        M1[Mask]:::impl --> M2[获取同对象 Graphic]:::core
        M2 --> M3[OnEnable：标记 isMaskingGraphic<br/>hasPopInstruction = true]:::core
        M3 --> M4[GetModifiedMaterial]:::core
        M4 --> M5[计算 StencilDepth]:::core
        M5 --> M6[StencilMaterial.Add<br/>生成 Mask Material]:::core
        M6 --> M7[StencilMaterial.Add<br/>生成 Unmask Material]:::core
        M7 --> M8[CanvasRenderer.SetPopMaterial]:::core

        MC1[子级 MaskableGraphic]:::impl --> MC2[GetModifiedMaterial]:::core
        MC2 --> MC3[读取父级 Stencil 深度]:::core
        MC3 --> MC4[生成 Compare Equal 的材质]:::core
    end

    subgraph S2[路径 B：RectMask2D（矩形裁剪）]
        direction TB
        R1[RectMask2D]:::impl --> R2[OnEnable 注册到 ClipperRegistry]:::core
        R2 --> R3[ClipperRegistry.Cull]:::core
        R3 --> R4[RectMask2D.PerformClipping]:::core
        R4 --> R5[收集父级 RectMask2D]:::core
        R5 --> R6[求交集 clipRect]:::core
        R6 --> R7[传播到子级目标]:::core
        R7 --> R8[SetClipRect]:::core
        R7 --> R9[Cull]:::core
        R7 --> R10[SetClipSoftness]:::core
        R8 --> R11[CanvasRenderer.EnableRectClipping]:::core
        R9 --> R12[CanvasRenderer.cull]:::core
        R10 --> R13[CanvasRenderer.clippingSoftness]:::core
    end

    A --> M1
    A --> R1

    B1[MaskableGraphic.UpdateClipParent]:::note --> B2[找到最近有效 RectMask2D]:::note
    B2 --> B3[AddClippable / RemoveClippable]:::note
    B3 --> R4

    C1[Graphic.Raycast 时<br/>Mask / RectMask2D 也作为 ICanvasRaycastFilter 参与过滤]:::note

    D1[关键修正：<br/>Mask ≠ RectMask2D，不能画成同一条处理链]:::warn
    D2[RectMask2D 不依赖 Stencil，<br/>而是矩形裁剪 + cull]:::warn
```

---

### 模块 7：控件、显示组件与接口体系

校验要点：  
`Button`、`Toggle`、`Slider`、`Scrollbar`、`Dropdown`、`InputField` 都继承 `Selectable`；但 `ScrollRect` 不是 `Selectable`，它直接继承 `UIBehaviour`，并实现拖拽、滚动、布局和 Canvas 接口。显示组件这边则是 `Graphic -> MaskableGraphic -> Image / RawImage / Text`。          

```mermaid
flowchart TB
    classDef core fill:#e8f0ff,stroke:#4a78d0,stroke-width:1.4px,color:#111;
    classDef impl fill:#eef9f0,stroke:#3f8f5a,stroke-width:1.2px,color:#111;
    classDef note fill:#fff7df,stroke:#c7a63a,stroke-width:1.1px,color:#111;
    classDef warn fill:#fff1f0,stroke:#d06a5f,stroke-width:1.1px,color:#111;

    A[MonoBehaviour]:::core --> B[UIBehaviour]:::core

    subgraph Visual[显示组件分支]
        direction TB
        B --> G1[Graphic<br/>+ ICanvasElement]:::impl
        G1 --> G2[MaskableGraphic<br/>+ IClippable / IMaskable / IMaterialModifier]:::impl
        G2 --> G3[Image<br/>+ ILayoutElement + ICanvasRaycastFilter]:::impl
        G2 --> G4[RawImage]:::impl
        G2 --> G5[Legacy Text<br/>+ ILayoutElement]:::impl
    end

    subgraph Controls[Selectable 控件分支]
        direction TB
        B --> S1[Selectable<br/>Move / PointerDown-Up / Enter-Exit / Select-Deselect]:::impl
        S1 --> S2[Button<br/>+ PointerClick + Submit]:::impl
        S1 --> S3[Toggle<br/>+ PointerClick + Submit + ICanvasElement]:::impl
        S1 --> S4[Slider<br/>+ Drag + InitializePotentialDrag + ICanvasElement]:::impl
        S1 --> S5[Scrollbar<br/>+ BeginDrag + Drag + InitializePotentialDrag + ICanvasElement]:::impl
        S1 --> S6[Legacy Dropdown<br/>+ PointerClick + Submit + Cancel]:::impl
        S1 --> S7[Legacy InputField<br/>+ UpdateSelected + Drag + Click + Submit<br/>+ ICanvasElement + ILayoutElement]:::impl
    end

    subgraph Other[其他重要独立分支]
        direction TB
        B --> O1[ScrollRect<br/>+ Drag + Scroll + ICanvasElement<br/>+ ILayoutElement + ILayoutGroup]:::impl
        B --> O2[LayoutGroup<br/>+ ILayoutElement + ILayoutGroup]:::impl
        O2 --> O3[HorizontalOrVerticalLayoutGroup]:::impl
        O3 --> O4[HorizontalLayoutGroup]:::impl
        O3 --> O5[VerticalLayoutGroup]:::impl
        O2 --> O6[GridLayoutGroup]:::impl
        B --> O7[ContentSizeFitter<br/>+ ILayoutSelfController]:::impl
        B --> O8[AspectRatioFitter<br/>+ ILayoutSelfController]:::impl
        B --> O9[LayoutElement<br/>+ ILayoutElement + ILayoutIgnorer]:::impl
    end

    subgraph Composition[常见组合关系]
        direction TB
        C1[Selectable.targetGraphic]:::note --> G1
        C2[Toggle 使用 Graphic / ToggleGroup]:::note --> S3
        C3[Slider 使用 FillRect / HandleRect]:::note --> S4
        C4[Scrollbar 使用 HandleRect]:::note --> S5
        C5[Dropdown 内部选项项常由 Toggle 承担]:::note --> S6
        C6[InputField 依赖 Text / Placeholder / Caret]:::note --> S7
        C7[ScrollRect 依赖 Content / Viewport / Scrollbar]:::note --> O1
    end

    W1[关键修正：ScrollRect 不是 Selectable 子类]:::warn
    W2[关键修正：控件既要看继承，也要看实现的事件 / 布局接口]:::warn
```

如果你要，我下一条可以继续把这 5 张图再升级成“适合面试讲解”的版本：每张图下再补一段“调用时序 + 常见易错点”。

## 轮次 24ec85bd-0440-4ab9-a4dc-85eb644f27bb

### 用户

上面有几个 显示不出来

### 助手

已重新生成 5 张独立交互图：Layout、Graphic 渲染、EventSystem、遮罩裁剪、控件与接口体系。

## 轮次 9ce226f7-6132-45fe-b893-9022f8106dd9

### 用户

上面 的 5张 图 分开 生成 给我,不要偷懒

### 助手

下面 5 张图完全分开给你。每张都是独立的 Mermaid 图。

### 图 1：Layout 布局系统

```mermaid
flowchart TB
    classDef core fill:#EAF2FF,stroke:#4A78D0,stroke-width:1.5px,color:#111;
    classDef impl fill:#EEF9F0,stroke:#3F8F5A,stroke-width:1.2px,color:#111;
    classDef note fill:#FFF7DF,stroke:#C7A63A,stroke-width:1.1px,color:#111;

    A[RectTransform、子节点或布局属性变化]:::core --> B[LayoutRebuilder.MarkLayoutForRebuild]:::core
    B --> C[沿父链查找最高有效布局根]:::core
    C --> D[加入 CanvasUpdateRegistry 布局队列]:::core
    D --> E[CanvasUpdate.Layout]:::core

    E --> F1[水平尺寸计算<br/>CalculateLayoutInputHorizontal]:::core
    F1 --> F2[自底向上<br/>子节点先于父节点]:::note
    F2 --> G1[水平布局控制<br/>SetLayoutHorizontal]:::core
    G1 --> G2[自顶向下<br/>父节点先于子节点]:::note
    G2 --> G3[同一节点先执行 ILayoutSelfController]:::note
    G3 --> G4[再执行其他 ILayoutController]:::note

    G4 --> H1[垂直尺寸计算<br/>CalculateLayoutInputVertical]:::core
    H1 --> H2[自底向上]:::note
    H2 --> I1[垂直布局控制<br/>SetLayoutVertical]:::core
    I1 --> I2[自顶向下]:::note
    I2 --> J[修改自身或子节点 RectTransform]:::core

    subgraph Elements[尺寸提供者 ILayoutElement]
        direction LR
        E1[LayoutElement]:::impl
        E2[Image / Text]:::impl
        E3[InputField]:::impl
        E4[LayoutGroup]:::impl
        E5[ScrollRect]:::impl
    end

    subgraph Controllers[布局控制者 ILayoutController]
        direction LR
        C1[ContentSizeFitter<br/>ILayoutSelfController]:::impl
        C2[AspectRatioFitter<br/>ILayoutSelfController]:::impl
        C3[HorizontalLayoutGroup]:::impl
        C4[VerticalLayoutGroup]:::impl
        C5[GridLayoutGroup]:::impl
        C6[ScrollRect<br/>ILayoutGroup]:::impl
    end

    F1 -.读取.-> Elements
    H1 -.读取.-> Elements
    G3 -.调用.-> C1
    G3 -.调用.-> C2
    G4 -.调用.-> C3
    G4 -.调用.-> C4
    G4 -.调用.-> C5
    G4 -.调用.-> C6

    K[LayoutGroup 收集有效 rectChildren]:::core --> L{ILayoutIgnorer.ignoreLayout?}:::core
    L -->|true| M[排除该子节点]:::note
    L -->|false| N[参与布局计算]:::note

    P[关键校验：ContentSizeFitter 与 AspectRatioFitter 不是 ILayoutElement]:::note
    Q[关键校验：GridLayoutGroup 使用统一 cellSize]:::note
```

---

### 图 2：Graphic 网格与材质渲染

```mermaid
flowchart TB
    classDef core fill:#EAF2FF,stroke:#4A78D0,stroke-width:1.5px,color:#111;
    classDef impl fill:#EEF9F0,stroke:#3F8F5A,stroke-width:1.2px,color:#111;
    classDef note fill:#FFF7DF,stroke:#C7A63A,stroke-width:1.1px,color:#111;

    A[Graphic 属性、纹理、尺寸或状态变化]:::core --> B{Dirty 类型}:::core
    B -->|顶点| C1[SetVerticesDirty<br/>m_VertsDirty = true]:::core
    B -->|材质| C2[SetMaterialDirty<br/>m_MaterialDirty = true]:::core
    B -->|布局| C3[SetLayoutDirty<br/>进入 Layout 系统]:::core

    C1 --> D[CanvasUpdateRegistry 图形队列]:::core
    C2 --> D
    D --> E[CanvasUpdate.PreRender]:::core
    E --> F[Graphic.Rebuild]:::core
    F --> G{CanvasRenderer 存在且未被 cull?}:::core
    G -->|否| H[跳过本次生成]:::note
    G -->|是| I{检查脏标记}:::core

    I -->|m_VertsDirty| J1[UpdateGeometry]:::core
    J1 --> J2[具体 Graphic.OnPopulateMesh]:::core
    J2 --> J3[写入共享 VertexHelper]:::core
    J3 --> J4[依次调用 IMeshModifier.ModifyMesh]:::impl
    J4 --> J5[VertexHelper.FillMesh(workerMesh)]:::core
    J5 --> J6[CanvasRenderer.SetMesh]:::core
    J6 --> J7[m_VertsDirty = false]:::note

    I -->|m_MaterialDirty| K1[UpdateMaterial]:::core
    K1 --> K2[取得 Graphic.material]:::core
    K2 --> K3[materialForRendering<br/>依次调用 IMaterialModifier]:::impl
    K3 --> K4[CanvasRenderer.SetMaterial]:::core
    K4 --> K5[CanvasRenderer.SetTexture(mainTexture)]:::core
    K5 --> K6[m_MaterialDirty = false]:::note

    subgraph Types[Graphic 类型]
        direction LR
        T1[Graphic]:::impl --> T2[MaskableGraphic]:::impl
        T2 --> T3[Image]:::impl
        T2 --> T4[RawImage]:::impl
        T2 --> T5[Legacy Text]:::impl
    end

    J2 -.由具体类型实现.-> Types
    J6 --> R[CanvasRenderer]:::core
    K5 --> R
    R --> S[Unity 原生 UI 渲染层]:::core
    S --> U[渲染管线 / GPU]:::core

    N1[GraphicRegistry 维护 Canvas 下 Graphic 集合]:::note
    N2[关键校验：GraphicRegistry 不是重建队列]:::note
```

---

### 图 3：EventSystem 输入、射线与事件派发

```mermaid
flowchart TB
    classDef core fill:#EAF2FF,stroke:#4A78D0,stroke-width:1.5px,color:#111;
    classDef impl fill:#EEF9F0,stroke:#3F8F5A,stroke-width:1.2px,color:#111;
    classDef note fill:#FFF7DF,stroke:#C7A63A,stroke-width:1.1px,color:#111;

    A[EventSystem.Update]:::core --> B[所有 InputModule.UpdateModule]:::core
    B --> C[选择受支持且应激活的模块]:::core
    C --> D{当前模块是否变化?}:::core
    D -->|是| E[Deactivate 旧模块<br/>Activate 新模块]:::core
    D -->|否| F[当前 BaseInputModule.Process]:::core

    F --> G[StandaloneInputModule.Process]:::core
    G --> G1[1. SendUpdateEventToSelectedObject]:::core
    G1 --> G2[2. 优先处理 Touch<br/>否则处理 Mouse]:::core
    G2 --> G3[3. Move 导航事件]:::core
    G3 --> G4[4. Submit / Cancel]:::core

    G2 --> H[创建或复用 PointerEventData]:::core
    H --> I[EventSystem.RaycastAll]:::core
    I --> J[遍历 RaycasterManager 中全部活动 BaseRaycaster]:::core

    subgraph Raycasters[射线检测分支]
        direction LR
        R1[GraphicRaycaster]:::impl
        R2[PhysicsRaycaster]:::impl
        R3[Physics2DRaycaster]:::impl
    end

    J --> R1
    J --> R2
    J --> R3

    R1 --> K1[GraphicRegistry 获取 Canvas 下可射线 Graphic]:::core
    K1 --> K2[过滤 raycastTarget、cull、depth、Rect]:::core
    K2 --> K3[Graphic.Raycast]:::core
    K3 --> K4[沿父链检查 ICanvasRaycastFilter]:::core
    K4 --> K5[Canvas 内按 Graphic.depth 降序]:::core

    R2 --> L1[Physics.Raycast]:::core
    R3 --> L2[Physics2D Raycast]:::core

    K5 --> M[汇总 RaycastResult]:::core
    L1 --> M
    L2 --> M
    M --> N[全局 RaycastResult 排序]:::core
    N --> O[FindFirstRaycast<br/>选择首个有效命中对象]:::core

    O --> P{输入状态}:::core
    P -->|移动| P1[PointerEnter / Exit / Move]:::impl
    P -->|按下| P2[PointerDown<br/>必要时回退到 Click Handler]:::impl
    P -->|拖拽| P3[BeginDrag → Drag]:::impl
    P -->|释放| P4[PointerUp → Click 或 Drop → EndDrag]:::impl

    P1 --> Q[ExecuteEvents]:::core
    P2 --> Q
    P3 --> Q
    P4 --> Q
    G1 --> Q
    G3 --> Q
    G4 --> Q

    Q --> Q1[Execute<br/>目标对象上的全部匹配处理器]:::core
    Q --> Q2[ExecuteHierarchy<br/>沿父链调用第一个可处理对象]:::core
    Q --> Q3[GetEventHandler<br/>沿父链查找处理器对象]:::core

    Q1 --> Z[IEventSystemHandler 组件]:::impl
    Q2 --> Z
    Q3 --> Z
    Z --> U[Button / Toggle / Slider / ScrollRect / 自定义组件]:::impl

    W[关键校验：触摸/鼠标处理早于 Move / Submit / Cancel]:::note
```

---

### 图 4：Mask 与 RectMask2D 遮罩裁剪

```mermaid
flowchart TB
    classDef core fill:#EAF2FF,stroke:#4A78D0,stroke-width:1.5px,color:#111;
    classDef impl fill:#EEF9F0,stroke:#3F8F5A,stroke-width:1.2px,color:#111;
    classDef note fill:#FFF7DF,stroke:#C7A63A,stroke-width:1.1px,color:#111;

    A{遮罩类型}:::core

    subgraph StencilPath[Mask：Stencil 材质路径]
        direction TB
        M1[Mask<br/>IMaterialModifier + ICanvasRaycastFilter]:::impl
        M1 --> M2[获取同对象上的 Graphic]:::core
        M2 --> M3[OnEnable<br/>hasPopInstruction = true<br/>标记 isMaskingGraphic]:::core
        M3 --> M4[Mask.GetModifiedMaterial]:::core
        M4 --> M5[计算 Stencil Depth]:::core
        M5 --> M6[StencilMaterial.Add<br/>生成 Mask Material]:::core
        M6 --> M7[生成 Unmask Material]:::core
        M7 --> M8[CanvasRenderer.SetPopMaterial]:::core

        MC1[子级 MaskableGraphic]:::impl --> MC2[GetModifiedMaterial]:::core
        MC2 --> MC3[计算父级 Mask 的 Stencil Depth]:::core
        MC3 --> MC4[生成 Compare Equal 材质]:::core
        MC4 --> MC5[子级仅在正确 Stencil 区域显示]:::note
    end

    subgraph RectPath[RectMask2D：矩形裁剪路径]
        direction TB
        R1[RectMask2D<br/>IClipper + ICanvasRaycastFilter]:::impl
        R1 --> R2[OnEnable 注册到 ClipperRegistry]:::core
        R2 --> R3[布局完成后 ClipperRegistry.Cull]:::core
        R3 --> R4[RectMask2D.PerformClipping]:::core
        R4 --> R5[收集当前与父级 RectMask2D]:::core
        R5 --> R6[Clipping.FindCullAndClipWorldRect<br/>求矩形交集]:::core
        R6 --> R7[检查与 Root Canvas 是否重叠]:::core
        R7 --> R8[向子级传播 clipRect / validRect]:::core
        R8 --> R9[SetClipRect]:::core
        R8 --> R10[Cull]:::core
        R8 --> R11[SetClipSoftness]:::core
        R9 --> R12[CanvasRenderer.EnableRectClipping]:::core
        R10 --> R13[CanvasRenderer.cull<br/>onCullStateChanged]:::core
        R11 --> R14[CanvasRenderer.clippingSoftness]:::core
    end

    A --> M1
    A --> R1

    U1[MaskableGraphic.UpdateClipParent]:::core --> U2[查找最近有效 RectMask2D]:::core
    U2 --> U3[AddClippable / RemoveClippable]:::core
    U3 --> R4

    F1[Mask 与 RectMask2D 都可作为 ICanvasRaycastFilter 参与 Graphic.Raycast]:::note
    F2[关键校验：Mask 与 RectMask2D 是两条独立机制]:::note
    F3[关键校验：RectMask2D 不使用 Stencil]:::note
```

---

### 图 5：控件、显示组件与接口体系

```mermaid
flowchart TB
    classDef base fill:#EAF2FF,stroke:#4A78D0,stroke-width:1.5px,color:#111;
    classDef visual fill:#EEF9F0,stroke:#3F8F5A,stroke-width:1.2px,color:#111;
    classDef control fill:#F4EEFF,stroke:#8059B2,stroke-width:1.2px,color:#111;
    classDef other fill:#FFF7DF,stroke:#C7A63A,stroke-width:1.1px,color:#111;
    classDef note fill:#FFF1F0,stroke:#D06A5F,stroke-width:1.1px,color:#111;

    A[MonoBehaviour]:::base --> B[UIBehaviour]:::base

    subgraph VisualBranch[显示组件分支]
        direction TB
        B --> V1[Graphic<br/>ICanvasElement]:::visual
        V1 --> V2[MaskableGraphic<br/>IClippable + IMaskable + IMaterialModifier]:::visual
        V2 --> V3[Image<br/>ILayoutElement + ICanvasRaycastFilter]:::visual
        V2 --> V4[RawImage]:::visual
        V2 --> V5[Legacy Text<br/>ILayoutElement]:::visual
    end

    subgraph SelectableBranch[Selectable 控件分支]
        direction TB
        B --> S1[Selectable<br/>Move / PointerDown-Up / Enter-Exit / Select-Deselect]:::control
        S1 --> S2[Button<br/>PointerClick + Submit]:::control
        S1 --> S3[Toggle<br/>PointerClick + Submit + ICanvasElement]:::control
        S1 --> S4[Slider<br/>Drag + InitializePotentialDrag + ICanvasElement]:::control
        S1 --> S5[Scrollbar<br/>BeginDrag + Drag + InitializePotentialDrag + ICanvasElement]:::control
        S1 --> S6[Legacy Dropdown<br/>PointerClick + Submit + Cancel]:::control
        S1 --> S7[Legacy InputField<br/>UpdateSelected + Drag + Click + Submit<br/>ICanvasElement + ILayoutElement]:::control
    end

    subgraph IndependentBranch[其他独立 UIBehaviour 分支]
        direction TB
        B --> O1[ScrollRect<br/>Drag + Scroll + ICanvasElement<br/>ILayoutElement + ILayoutGroup]:::other
        B --> O2[LayoutGroup<br/>ILayoutElement + ILayoutGroup]:::other
        O2 --> O3[HorizontalOrVerticalLayoutGroup]:::other
        O3 --> O4[HorizontalLayoutGroup]:::other
        O3 --> O5[VerticalLayoutGroup]:::other
        O2 --> O6[GridLayoutGroup]:::other
        B --> O7[ContentSizeFitter<br/>ILayoutSelfController]:::other
        B --> O8[AspectRatioFitter<br/>ILayoutSelfController]:::other
        B --> O9[LayoutElement<br/>ILayoutElement + ILayoutIgnorer]:::other
        B --> O10[EventSystem]:::other
        B --> O11[BaseInputModule]:::other
        B --> O12[BaseRaycaster]:::other
    end

    subgraph Composition[常见组合关系：不是继承]
        direction LR
        C1[Selectable.targetGraphic]:::visual --> V1
        C2[Toggle 状态 Graphic + ToggleGroup]:::visual --> S3
        C3[Slider FillRect + HandleRect]:::visual --> S4
        C4[Scrollbar HandleRect]:::visual --> S5
        C5[Dropdown Template + Item Toggle]:::visual --> S6
        C6[InputField Text + Placeholder + Caret]:::visual --> S7
        C7[ScrollRect Content + Viewport + Scrollbar]:::visual --> O1
    end

    N1[关键校验：ScrollRect 不继承 Selectable]:::note
    N2[关键校验：理解控件体系要同时看继承、接口、组合关系]:::note
```

如果你这次还看到有某一张渲染不出来，我下一条就只发那一张的“纯简化版 Mermaid”，把兼容性优先放到最高。

## 轮次 20f3b834-c76e-448b-ad49-98cca01cdaf8

### 用户

图 3：EventSystem 输入、射线与事件派发 没显示出来

### 助手

单独给你重发 **图 3**，这次我把结构压缩了，尽量保证能显示。

### 图 3：EventSystem 输入、射线与事件派发（简化兼容版）

```mermaid
flowchart TB
    A[EventSystem.Update] --> B[UpdateModule 所有输入模块]
    B --> C[选择当前活动 InputModule]
    C --> D[BaseInputModule.Process]
    D --> E[StandaloneInputModule.Process]

    E --> E1[1 UpdateSelected]
    E1 --> E2[2 Touch 或 Mouse]
    E2 --> E3[3 Move]
    E3 --> E4[4 Submit 或 Cancel]

    E2 --> F[创建或复用 PointerEventData]
    F --> G[EventSystem.RaycastAll]
    G --> H[遍历所有 BaseRaycaster]

    H --> R1[GraphicRaycaster]
    H --> R2[PhysicsRaycaster]
    H --> R3[Physics2DRaycaster]

    R1 --> I1[获取 Canvas 下可射线 Graphic]
    I1 --> I2[过滤不可命中对象]
    I2 --> I3[Graphic.Raycast]
    I3 --> I4[检查父链 ICanvasRaycastFilter]
    I4 --> I5[按 depth 排序]

    R2 --> J1[3D Physics Raycast]
    R3 --> J2[2D Physics Raycast]

    I5 --> K[汇总 RaycastResult]
    J1 --> K
    J2 --> K

    K --> L[全局排序]
    L --> M[FindFirstRaycast]

    M --> N{输入状态}
    N --> N1[移动 Enter Exit Move]
    N --> N2[按下 PointerDown]
    N --> N3[拖拽 BeginDrag Drag]
    N --> N4[释放 PointerUp Click Drop EndDrag]

    N1 --> P[ExecuteEvents]
    N2 --> P
    N3 --> P
    N4 --> P
    E1 --> P
    E3 --> P
    E4 --> P

    P --> Q1[Execute]
    P --> Q2[ExecuteHierarchy]
    P --> Q3[GetEventHandler]

    Q1 --> Z[目标组件处理事件]
    Q2 --> Z
    Q3 --> Z
```

这一张的核心含义是：

`EventSystem.Update → InputModule.Process → RaycastAll → 找到命中对象 → ExecuteEvents 派发给处理器`

你要是愿意，我下一条可以把这张再拆成两张：  
**3-1 输入与射线检测**，**3-2 ExecuteEvents 派发机制**。

## 轮次 d9561b14-6cde-473b-9e56-d2060b08b80a

### 用户

给我一个总的架构图, 画好看点

### 助手

已生成一张 UGUI 总体分层架构图，按“输入事件链、UI 组件层、布局/重建链、渲染生成链、遮罩裁剪链、UnityEngine 原生层”组织。

