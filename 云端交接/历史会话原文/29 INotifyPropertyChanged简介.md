# INotifyPropertyChanged简介

会话 ID：`6a2b9fdd-0604-83ea-a4d0-602944428c21`

返回页：`{"order": "newest_first", "limit": 10, "nextCursor": null, "hasMore": false}`

## 轮次 73bb5c6c-f6d4-401f-a8f8-ffe3a2070b92

### 用户

C#的INotifyPropertyChanged接口

### 助手

`INotifyPropertyChanged` 是 C# 中用于**数据绑定（Data Binding）**的一个接口，它的作用是：

> **当对象的某个属性发生变化时，主动通知外部。**

最常见于：
- WPF
- WinUI
- MAUI
- Xamarin
- Unity（MVVM 框架如 Unity-Weld、MVVM Toolkit 等）

它定义在：

```csharp
using System.ComponentModel;
```

接口非常简单：

```csharp
public interface INotifyPropertyChanged
{
    event PropertyChangedEventHandler PropertyChanged;
}
```

只有一个事件。

---

# 为什么需要它？

假设有一个 Person：

```csharp
public class Person
{
    public string Name { get; set; }
}
```

UI绑定了：

```
TextBlock.Text ← Person.Name
```

如果：

```csharp
person.Name = "Tom";
```

UI 根本不知道 Name 已经变了。

因为：

> **普通属性不会通知别人自己发生了变化。**

于是就有了：

```
修改属性
      ↓
触发 PropertyChanged
      ↓
UI收到通知
      ↓
刷新界面
```

---

# 最简单示例

```csharp
using System.ComponentModel;

public class Person : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler PropertyChanged;

    private string _name;

    public string Name
    {
        get => _name;

        set
        {
            _name = value;

            PropertyChanged?.Invoke(
                this,
                new PropertyChangedEventArgs(nameof(Name))
            );
        }
    }
}
```

当：

```csharp
person.Name = "Alice";
```

实际上发生的是：

```
Name setter
      ↓
修改字段
      ↓
Invoke(PropertyChanged)
      ↓
所有监听者收到通知
```

---

# 谁在监听？

例如：

```csharp
person.PropertyChanged += OnPropertyChanged;
```

监听函数：

```csharp
private void OnPropertyChanged(
    object sender,
    PropertyChangedEventArgs e)
{
    Console.WriteLine(e.PropertyName);
}
```

运行：

```csharp
person.Name = "Bob";
```

输出：

```
Name
```

说明：

> Name 属性变了。

---

# PropertyChangedEventArgs

里面只有一个重要成员：

```csharp
e.PropertyName
```

例如：

```csharp
Console.WriteLine(e.PropertyName);
```

输出：

```
Name
```

所以监听者可以知道：

到底是哪一个属性改变了。

---

# 为什么要 nameof？

不要这样：

```csharp
PropertyChanged?.Invoke(
    this,
    new PropertyChangedEventArgs("Name")
);
```

应该：

```csharp
nameof(Name)
```

原因：

如果以后：

```csharp
Name
```

改成：

```csharp
UserName
```

字符串：

```
"Name"
```

不会自动修改。

但是：

```csharp
nameof(UserName)
```

编译器会自动更新。

---

# 更好的写法

很多人都会写一个统一的方法：

```csharp
protected void OnPropertyChanged(string propertyName)
{
    PropertyChanged?.Invoke(
        this,
        new PropertyChangedEventArgs(propertyName));
}
```

然后：

```csharp
public string Name
{
    get => _name;

    set
    {
        _name = value;
        OnPropertyChanged(nameof(Name));
    }
}
```

这样代码更简洁。

---

# 更进一步：避免重复通知

很多时候：

```csharp
person.Name = "Tom";
person.Name = "Tom";
person.Name = "Tom";
```

其实没有变化。

可以写：

```csharp
public string Name
{
    get => _name;

    set
    {
        if (_name == value)
            return;

        _name = value;

        OnPropertyChanged(nameof(Name));
    }
}
```

这样：

只有真正变化时才通知。

---

# 最常见的封装：SetProperty

很多 MVVM 框架都会提供：

```csharp
protected bool SetProperty<T>(
    ref T field,
    T value,
    [System.Runtime.CompilerServices.CallerMemberName]
    string propertyName = null)
{
    if (EqualityComparer<T>.Default.Equals(field, value))
        return false;

    field = value;

    OnPropertyChanged(propertyName);

    return true;
}
```

以后属性只需要：

```csharp
private string _name;

public string Name
{
    get => _name;
    set => SetProperty(ref _name, value);
}
```

这里利用了 `CallerMemberName` 特性，调用 `SetProperty` 时无需手写属性名，编译器会自动把当前属性名（如 `Name`）传入，因此更加简洁且不易出错。

---

# 在 Unity 中有没有用？

Unity 自带的：

```
Inspector
```

**不会监听** `INotifyPropertyChanged`。

所以：

```csharp
class Player : INotifyPropertyChanged
{
}
```

Unity 不会因为：

```csharp
HP = 100;
```

自动刷新 Inspector。

但是如果你做：

- MVVM
- 数据绑定
- UI框架
- 编辑器工具
- 配置系统

就非常有用。

例如：

```
Player
      │
      │ HP变化
      ▼
PropertyChanged
      │
      ▼
HealthBar
自动刷新
```

而不用：

```csharp
healthBar.Refresh();
```

每次都手动调用。

---

# 它的本质

从设计模式角度来看，`INotifyPropertyChanged` 实际上是**观察者模式（Observer Pattern）**在 .NET 中的一个标准实现：

```
        属性改变
            │
            ▼
     PropertyChanged 事件
            │
    ┌───────┴────────┐
    ▼                ▼
 UI监听器        其他业务监听器
    ▼                ▼
刷新界面      更新缓存/日志/计算
```

因此，`INotifyPropertyChanged` 的核心价值不是“刷新 UI”，而是**让对象在属性变化时主动向所有订阅者广播通知**。UI 数据绑定只是最常见的应用场景之一。

## 轮次 e8e033f9-0e99-4e9b-b415-dc13d0f42863

### 用户

这会不会产生Gc

### 助手

这是一个很好的问题。

**答案是：会，但通常非常少，而且很多情况下可以忽略。真正需要关注的是你触发通知的频率。**

下面我们具体分析。

---

## 1. `PropertyChanged?.Invoke()` 本身会不会产生 GC？

```csharp
PropertyChanged?.Invoke(
    this,
    new PropertyChangedEventArgs(nameof(Name))
);
```

这里有两部分：

### ① `Invoke`

```csharp
PropertyChanged?.Invoke(...)
```

**不会产生 GC。**

它只是调用事件委托（Delegate），不会创建新对象。

---

### ② `new PropertyChangedEventArgs(...)`

```csharp
new PropertyChangedEventArgs(nameof(Name))
```

**这里会分配一个新的对象。**

每次调用都会创建：

```text
PropertyChangedEventArgs
```

因此：

```csharp
person.Name = "A";
person.Name = "B";
person.Name = "C";
```

就会创建三个 `PropertyChangedEventArgs` 对象。

如果你的属性每帧修改很多次（例如 Unity 中每帧更新 HP、位置、速度等），这些小对象累计起来就可能增加 GC 压力。

---

## 2. `nameof(Name)` 会不会产生 GC？

不会。

```csharp
nameof(Name)
```

在编译时就会变成：

```csharp
"Name"
```

它是一个字符串字面量，不会每次重新创建字符串。

---

## 3. 事件（Delegate）会不会产生 GC？

正常触发不会。

例如：

```csharp
PropertyChanged += OnChanged;
```

这是订阅事件，只在订阅时创建委托对象。

之后：

```csharp
PropertyChanged?.Invoke(...)
```

只是调用已有的委托，不会再次分配内存。

---

## 4. 如何减少 `PropertyChangedEventArgs` 的分配？

很多框架会缓存 `PropertyChangedEventArgs`：

```csharp
private static readonly PropertyChangedEventArgs NameChangedArgs =
    new PropertyChangedEventArgs(nameof(Name));

public string Name
{
    get => _name;
    set
    {
        if (_name == value)
            return;

        _name = value;
        PropertyChanged?.Invoke(this, NameChangedArgs);
    }
}
```

这样：

- 不会每次 `new`
- 整个程序只创建一个 `PropertyChangedEventArgs`

---

## 5. 为什么很多 MVVM 框架几乎没有 GC？

例如：

- entity["software","CommunityToolkit.Mvvm","MVVM Toolkit"]
- entity["software","Prism","Prism Library"]
- entity["software","ReactiveUI","ReactiveUI"]

它们通常会：

- 使用 `SetProperty`
- 避免值未变化时通知
- 在一些实现中缓存 `PropertyChangedEventArgs`
- 减少重复通知

因此日常业务中，GC 开销很小。

---

## 6. Unity 中需要特别在意吗？

如果是：

- 玩家名字
- 等级
- 金币
- 装备
- 背包

这些变化频率低，**完全不用担心 GC**。

但如果你打算这样用：

```csharp
public float X
{
    set
    {
        _x = value;
        OnPropertyChanged(nameof(X));
    }
}
```

并且：

```csharp
void Update()
{
    X = transform.position.x;
}
```

或者每帧通知：

- Position
- Rotation
- Velocity
- HP（持续变化）
- Mana

那么每秒可能触发几百到几千次通知，这些 `PropertyChangedEventArgs` 的分配就值得优化，甚至可以考虑不用 `INotifyPropertyChanged`，而使用专门为高频场景设计的事件机制。

---

### 总结

| 操作 | 是否产生 GC |
|------|------------|
| `nameof(Name)` | ❌ 不会 |
| `PropertyChanged?.Invoke()` | ❌ 不会 |
| `new PropertyChangedEventArgs()` | ✅ 会（每次一个对象） |
| 事件订阅（`+=`） | ✅ 会（订阅时一次） |
| 事件触发 | ❌ 不会 |

**对于绝大多数应用（包括大多数 UI 数据绑定），`INotifyPropertyChanged` 的 GC 开销非常低。** 在 Unity 中，真正需要关注的是**高频（例如每帧）属性更新**，这时可以通过缓存 `PropertyChangedEventArgs` 或采用其他通知机制来避免不必要的内存分配。

## 轮次 47e96fd9-5ba8-4712-aa7d-cbb1abf06196

### 用户

4 这一点，如果有多个属性，PropertyChangedEventArgs 就需要创建多份吗

### 助手

是的，**如果采用缓存 `PropertyChangedEventArgs` 的方式，通常每个属性会缓存一份。**

例如：

```csharp
public class Player : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler PropertyChanged;

    // 每个属性对应一个静态缓存
    private static readonly PropertyChangedEventArgs HpArgs =
        new(nameof(HP));

    private static readonly PropertyChangedEventArgs MpArgs =
        new(nameof(MP));

    private static readonly PropertyChangedEventArgs LevelArgs =
        new(nameof(Level));

    private int _hp;
    public int HP
    {
        get => _hp;
        set
        {
            if (_hp == value) return;
            _hp = value;
            PropertyChanged?.Invoke(this, HpArgs);
        }
    }

    // ...
}
```

这里：

- `HP` 使用 `HpArgs`
- `MP` 使用 `MpArgs`
- `Level` 使用 `LevelArgs`

整个程序运行期间，每个属性只创建一次。

---

## 为什么不能共用一个？

因为 `PropertyChangedEventArgs` 内部保存了属性名：

```csharp
new PropertyChangedEventArgs(nameof(HP))
```

实际上等价于：

```text
PropertyName = "HP"
```

如果你拿它去通知 `MP`：

```csharp
PropertyChanged?.Invoke(this, HpArgs);
```

监听者收到的仍然是：

```text
PropertyName == "HP"
```

UI 就会认为 **HP 变了**，而不是 MP。

所以**不同属性必须对应不同的 `PropertyChangedEventArgs`**。

---

## 如果有 100 个属性怎么办？

很多人会觉得：

> 「那不是要写 100 个静态字段？」

其实有几种做法。

### 方案一：每个属性一个静态字段（性能最好）

```csharp
private static readonly PropertyChangedEventArgs NameArgs =
    new(nameof(Name));
```

优点：

- 零 GC
- 查找最快

缺点：

- 字段多一点

不过每个对象只有几十字节，100 个属性也不过几 KB，几乎可以忽略。

---

### 方案二：用字典缓存（很多框架采用）

```csharp
private static readonly Dictionary<string, PropertyChangedEventArgs> cache = new();

protected void OnPropertyChanged(string name)
{
    if (!cache.TryGetValue(name, out var args))
    {
        args = new PropertyChangedEventArgs(name);
        cache[name] = args;
    }

    PropertyChanged?.Invoke(this, args);
}
```

第一次：

```text
HP
 ↓
new PropertyChangedEventArgs("HP")
```

以后：

```text
HP
 ↓
直接从 Dictionary 取
```

这样：

- 不需要为每个属性写静态字段
- 每个属性也只创建一次

代价是每次通知需要一次字典查找。

---

## .NET 官方和社区一般怎么做？

实际上，很多现代 MVVM 框架（例如 entity["software","CommunityToolkit.Mvvm","MVVM Toolkit"]）**并没有专门缓存 `PropertyChangedEventArgs`**。

原因是：

- `PropertyChangedEventArgs` 对象非常小；
- 现代 .NET 的垃圾回收对这种短生命周期的小对象处理效率很高；
- 为了减少代码复杂度，很多框架更倾向于直接：

```csharp
PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
```

对于桌面应用（WPF、MAUI 等）来说，这已经足够高效。

---

## Unity 中我的建议

如果你的项目比较在意 GC（尤其是游戏运行时）：

- **低频属性**（金币、等级、昵称等）：直接 `new PropertyChangedEventArgs(...)`，简单即可。
- **高频属性**（血量、蓝量、能量条等）：可以缓存 `PropertyChangedEventArgs`，避免持续分配。
- **每帧都会变化的属性**（位置、旋转、速度等）：通常**不建议使用 `INotifyPropertyChanged`**，更适合使用专门的事件、观察者或响应式方案。

对于 Unity 来说，真正影响性能的往往不是创建几十个 `PropertyChangedEventArgs`，而是**每帧成千上万次通知**带来的累计开销。

