# 取消Unity场景加载

会话 ID：`6a2a812a-7680-83ea-9a1b-b50f926c2e90`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 90fb500b-9089-4b10-a738-7ae3f96c73b8

### 用户

unity 如何取消一个正在加载的场景

### 助手

Unity 里，`SceneManager.LoadSceneAsync` 返回的是 `AsyncOperation`，官方文档给出的控制点是 `allowSceneActivation`：把它设为 `false` 可以把加载卡在 `0.9`，并阻止场景真正激活；文档里没有提供“Cancel/Abort”这类直接取消接口，所以通常**不能真正中断一个已经开始的场景加载**，只能做到“延迟激活”或“忽略这次加载结果”。 :chatgpt-content-reference{index="0"}

常见写法是自己加一个取消标记：

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

public class SceneLoader : MonoBehaviour
{
    private AsyncOperation _op;
    private bool _cancelRequested;

    public void Load(string sceneName)
    {
        _cancelRequested = false;
        StartCoroutine(LoadRoutine(sceneName));
    }

    public void CancelLoad()
    {
        _cancelRequested = true;

        // 这只能阻止“激活”，不能把已经开始的异步加载真正掐断
        if (_op != null)
            _op.allowSceneActivation = false;
    }

    private IEnumerator LoadRoutine(string sceneName)
    {
        _op = SceneManager.LoadSceneAsync(sceneName);
        _op.allowSceneActivation = false;

        while (!_op.isDone)
        {
            if (_cancelRequested)
            {
                // 取消逻辑：不激活这次加载结果，改由你自己切回别的流程
                yield break;
            }

            if (_op.progress >= 0.9f)
            {
                // 到了可激活阶段，但这里先不放行
            }

            yield return null;
        }
    }
}
```

更实用的理解是：  
你能控制的是“**要不要让它完成激活**”，不是“**把已经开始的加载立即停止**”。如果你现在的需求是“点了返回键，正在加载时立刻回到上一个界面”，:chatgpt-content-reference{index="2"}。

## 轮次 f38f479e-f90a-42a7-9ac1-ad5743802579

### 用户

给我一套加载界面、取消按钮和防重复进入的完整脚本

### 助手

这是游戏项目里比较常见的一套架构：

```text
MainMenu
    ↓
LoadingScene（常驻）
    ↓
GameScene
```

不要在 MainMenu 里直接加载 GameScene，而是先进入一个专门的 LoadingScene，由它负责：

- 显示进度条
- 显示 Loading 动画
- 支持取消
- 防止重复点击
- 控制场景激活

---

## 1. LoadingManager

单例负责整个加载流程。

```csharp
using UnityEngine;
using UnityEngine.SceneManagement;
using System.Collections;

public class LoadingManager : MonoBehaviour
{
    public static LoadingManager Instance;

    private AsyncOperation _loadingOp;
    private bool _isLoading;
    private bool _cancelRequested;

    public bool IsLoading => _isLoading;
    public float Progress => _loadingOp == null ? 0 : _loadingOp.progress;

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
    }

    public void LoadScene(string sceneName)
    {
        if (_isLoading)
        {
            Debug.Log("已经在加载中");
            return;
        }

        StartCoroutine(LoadRoutine(sceneName));
    }

    public void CancelLoad()
    {
        if (!_isLoading)
            return;

        _cancelRequested = true;

        if (_loadingOp != null)
            _loadingOp.allowSceneActivation = false;
    }

    private IEnumerator LoadRoutine(string sceneName)
    {
        _isLoading = true;
        _cancelRequested = false;

        yield return SceneManager.LoadSceneAsync("LoadingScene");

        yield return null;

        _loadingOp = SceneManager.LoadSceneAsync(sceneName);
        _loadingOp.allowSceneActivation = false;

        while (_loadingOp.progress < 0.9f)
        {
            if (_cancelRequested)
            {
                yield return SceneManager.LoadSceneAsync("MainMenu");
                _isLoading = false;
                yield break;
            }

            yield return null;
        }

        if (_cancelRequested)
        {
            yield return SceneManager.LoadSceneAsync("MainMenu");
            _isLoading = false;
            yield break;
        }

        _loadingOp.allowSceneActivation = true;

        while (!_loadingOp.isDone)
            yield return null;

        _isLoading = false;
    }
}
```

---

# 2. 主菜单按钮

防止疯狂连点。

```csharp
using UnityEngine;
using UnityEngine.UI;

public class StartButton : MonoBehaviour
{
    public Button startBtn;

    public void OnClickStart()
    {
        if (LoadingManager.Instance.IsLoading)
            return;

        startBtn.interactable = false;

        LoadingManager.Instance.LoadScene("GameScene");
    }
}
```

---

# 3. Loading界面

```csharp
using UnityEngine;
using UnityEngine.UI;

public class LoadingUI : MonoBehaviour
{
    public Slider progressBar;
    public Text progressText;

    void Update()
    {
        if (LoadingManager.Instance == null)
            return;

        float progress =
            LoadingManager.Instance.Progress / 0.9f;

        progress = Mathf.Clamp01(progress);

        progressBar.value = progress;
        progressText.text =
            $"{(int)(progress * 100)}%";
    }
}
```

---

# 4. 取消按钮

```csharp
using UnityEngine;

public class CancelButton : MonoBehaviour
{
    public void OnClickCancel()
    {
        LoadingManager.Instance.CancelLoad();
    }
}
```

---

# 5. 更成熟的项目写法

实际商业项目一般不会：

```csharp
LoadSceneAsync("GameScene");
```

而是：

```text
进入 LoadingScene
    ↓
加载配置表
    ↓
加载 Addressables
    ↓
加载 Shader Variant
    ↓
加载 UI Atlas
    ↓
加载 GameScene
    ↓
激活场景
```

因此通常会有一个加载任务队列：

```csharp
LoadingTask
{
    LoadConfig
    LoadAtlas
    LoadAudio
    LoadScene
}
```

统一汇报进度：

```csharp
总进度 = 已完成任务权重 / 总权重
```

例如：

```text
配置 10%
图集 20%
音频 20%
场景 50%
```

最终显示：

```text
73%
```

而不是 Unity 原生的：

```text
0 -> 90%
突然跳100%
```

---

需要注意的一点：

```csharp
SceneManager.LoadSceneAsync()
```

**本质上无法真正取消。**

即使你：

```csharp
CancelLoad();
```

Unity 后台已经读取到内存的数据不会立刻释放。

大型项目（原神、王者、PUBG 等）的做法通常是：

```text
记录取消标志
↓
加载完成后不激活
↓
释放资源
↓
回到上一个界面
```

也就是说：

```text
逻辑取消
≠
真正中断IO加载
```

这是 Unity 场景加载机制本身的限制。

