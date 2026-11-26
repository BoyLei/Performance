# CanvasGroup in Unity

会话 ID：`6a33b397-c5ec-83ea-a68a-d835b7aa4122`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 1175f515-c967-4902-bb1a-5df6dae1d45c

### 用户

CanvasGroup

### 助手

In **Unity**, a **CanvasGroup** is a component that lets you control a UI element and all of its child UI elements as a group.

It provides three main properties:

| Property | Description |
|----------|-------------|
| **Alpha** | Controls the transparency of the entire group (0 = invisible, 1 = fully visible). |
| **Interactable** | Determines whether UI controls (buttons, sliders, etc.) can be interacted with. |
| **Blocks Raycasts** | Determines whether the UI group receives mouse/touch input events. |

There's also:

| Property | Description |
|----------|-------------|
| **Ignore Parent Groups** | Allows this CanvasGroup to ignore CanvasGroup settings inherited from parent objects. |

### Common Uses

#### Fade UI In/Out
```csharp
CanvasGroup canvasGroup;

void Start()
{
    canvasGroup.alpha = 0f; // hidden
}

void Show()
{
    canvasGroup.alpha = 1f; // visible
}
```

#### Disable a Menu
```csharp
canvasGroup.interactable = false;
canvasGroup.blocksRaycasts = false;
```

#### Hide and Disable Simultaneously
```csharp
canvasGroup.alpha = 0f;
canvasGroup.interactable = false;
canvasGroup.blocksRaycasts = false;
```

This is often preferred over enabling/disabling multiple UI components individually because one CanvasGroup can control an entire UI hierarchy at once.

