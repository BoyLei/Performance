---
title: "02 CPU与调度"
category: "CPU"
tags: ["Unity", "Performance"]
discussion_status: "mixed"
learning_status: "pending"
priority: "P0"
created: "2026-11-26"
unity_scope: "通用原理；示例以 Unity 2022.3 URP 为背景；实际版本待确认"
related: ["[[03 内存与GC]]", "[[06 异步与生命周期]]", "[[10 MMO架构与网络]]"]
---

# 02 CPU与调度

%% navigation-start %%
> [!abstract] 本页位置
> [[00 知识库首页|首页]] → [[运行时与内存]] → **02 CPU与调度**
> 理解 PlayerLoop、固定步进和计时器的阶段与延迟。
> [[02 CPU与调度 导图.canvas|打开图谱]] · [[知识体系脑图|完整层级]] · [[模块依赖与关联|关联说明]]

> [!tip]- 本页知识点索引
> - [[02 CPU与调度#PlayerLoop与Update|PlayerLoop与Update]]
> - [[02 CPU与调度#FixedUpdate与时间|FixedUpdate与时间]]
> - [[02 CPU与调度#Timer系统|Timer系统]]
> - [[02 CPU与调度#Jobs与Burst|Jobs与Burst]]
> - [[02 CPU与调度#固定步与 PlayerLoop 字段纠错（Q024–Q025、Q082）|固定步与 PlayerLoop 字段纠错（Q024–Q025、Q082）]]
> - [[02 CPU与调度#最小堆 Timer 的实现契约（Q079–Q081）|最小堆 Timer 的实现契约（Q079–Q081）]]
> - [[02 CPU与调度#InvokeRepeating 的生命周期边界（Q085）|InvokeRepeating 的生命周期边界（Q085）]]

%% navigation-end %%

本模块为归纳后的原理与实践建议。历史原问集中在 [[历史问题索引]]；无原文支持的扩展不视为用户问过。

## PlayerLoop与Update

Update、FixedUpdate、渲染和异步续体由 PlayerLoop 不同阶段驱动。优化大量 Update 可通过集中调度、分频和事件触发减少无效遍历，但管理器本身也有成本。

**验证与验收：** 采样主线程 Timeline，将脚本、动画、物理和渲染准备拆开统计。

## FixedUpdate与时间

固定步长用于物理模拟，不代表每个渲染帧正好执行一次。慢帧可能需要补多次固定步，放大 CPU 压力；修改 fixedDeltaTime 会改变精度和成本。

**验证与验收：** 记录一秒内固定步数量，验证不同帧率下移动与碰撞一致性。

## Timer系统

定时器可按触发时间组织最小堆、时间轮或简单列表；选择取决于数量和精度。必须明确缩放时间、暂停、取消、重复触发和回调中增删行为。

**验证与验收：** 比较 100、1000、10000 个计时器的调度成本与误差，检查取消后不再回调。

## Jobs与Burst

可并行的纯数据计算适合 Job System；Burst 优化兼容代码。收益取决于任务粒度、数据布局和调度同步开销。尽量让独立主线程工作与 Job 重叠，在读取结果前通过 JobHandle.Complete 确认完成；如果本帧立即需要结果，同帧 Complete 完全合法，只是可能减少重叠收益。不能把这条性能建议当作禁止同步的正确性规则。

**验证与验收：** 识别可独立计算的视野或距离数据，先测串行基线，再评估并行。

## 关联

- [[03 内存与GC]]
- [[06 异步与生命周期]]
- [[10 MMO架构与网络]]

任务入口：[[学习任务脑图]]；参考依据：[[参考资料与版本边界]]。

专项：[[架构线程与代码实践]]。

历史来源：[[历史问题索引#自定义Unity Timer系统]]。

历史来源：[[历史问题索引#FixedUpdate 时间执行]]。

## 固定步与 PlayerLoop 字段纠错（Q024–Q025、Q082）

`fixedDeltaTime` 固定模拟步长，实际回调可能在一帧中发生零次或多次。`maximumDeltaTime` 限制推进与追赶量，因此不能说卡顿后“模拟时间永不丢失”。桌面 VSync 与移动端 targetFrameRate 的平台规则不同，目标 FPS 不构成实时保证。

Unity 2022.3 的 `PlayerLoopSystem.updateDelegate` 是托管 `UpdateFunction` 委托，`updateFunction` 与 `loopConditionFunction` 是原生指针；旧回答给两个同名 updateFunction 字段是错误的。不要手工构造或改写原生指针；托管注入应从当前树复制并保留其他系统节点。UniTask、其他插件也可能注入调度器。

## 最小堆 Timer 的实现契约（Q079–Q081）

数组保存堆：父索引 `(i-1)/2`，子索引 `2*i+1`、`2*i+2`。按 `(expireAt, sequence)` 比较，后者给同一到期时间确定顺序。Push 上浮、Pop 以末项填根后下沉，均 O(log N)；Peek O(1)。任意取消需 ID→堆下标表，交换时同步更新表，再根据父子关系选择上浮或下沉；取消不是无条件 O(1)。

懒删除需修改权威表中的有效标记或 generation，不能只修改从 struct 堆中取出的副本；还应限制墓碑积累。回调前先移出到期项，回调后再次校验 generation 与取消标记，再决定重复入堆，避免回调取消自身却被重新加入。

重复计时有三种契约：`expireAt += interval` 保留节奏并补发；跳过过期次数保留相位；`expireAt = now + interval` 从当前时间重新计时。设置全局每帧时间/次数预算，拒绝非正或非有限 interval。暂停恢复应保存剩余时间并从堆中移除，恢复后重新入堆。

用统一时钟读取一次 now；游戏时间用缩放时钟，现实超时用单调时钟（如 realtimeSinceStartupAsDouble）。Time.deltaTime 受缩放和最大步长限制，不保证补回所有现实时间。“不要使用 Time.time”没有普适依据。字典预留容量、复用委托与缓冲后再测 GC.Alloc；最小堆不能免疫 GC 或线程阻塞。

System.Threading.Timer 的回调在线程池，可能重入或与 Dispose 竞态；应串行化共享状态、拒绝已过期回调，并把 Unity 操作投递主线程。不是所有 Unity 脚本工作都只能在主线程，纯数据工作可明确放到后台。

## InvokeRepeating 的生命周期边界（Q085）

旧回答把它等同协程，声称禁用组件或节点必然取消且不恢复，不能作为项目契约。它受 timeScale 影响；需要停止时明确 CancelInvoke，并在 OnDisable/回池入口统一取消，在 OnEnable/取出时防重复注册。销毁宿主、禁用组件、禁用 GameObject、timeScale=0 必须分别在项目版本验证；本轮无 Unity 运行环境，不声明这组运行测试已通过。

来源：[[历史问题索引#自定义Unity Timer系统]]、[[历史问题索引#FixedUpdate 时间执行]]；官方字段与时间 API 见 [[参考资料与版本边界#本轮技术核查依据]]。

本轮复核结论见 [[知识点逐项核验]]；文档/源码版本依据见 [[技术核验来源]]。
