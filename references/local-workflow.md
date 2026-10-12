# 最小本地工作流程

工具只负责草案、JSON快照、输入内容去重和角色包导出；语义提取由加载本 Skill 的 LLM 完成。适用于单玩家、串行操作，不支持并发写入或服务端认证。批准散列绑定草案内容，是防误提交措施，不是身份认证。不要以此工具声称角色无权访问共享磁盘。

正式状态只有 `world`、`objective`、`subjective` 三层。`meta` 只保存 `tracked`（玩家名单）、`through`（覆盖故事时间）与 `processed`（已归档原文散列）。不在 meta 添加故事事实。淡出人物的第二、第三层仍保留，但不导出角色包。

每条记录包含 `id`、`event_id`、`t`、`summary`、`status`、`origin`、`source`，第三层额外包含 `available`（当前可供角色读取）。同一事件可有多条时间记录或多个角色的记录，沿用 event_id；更新同一记录沿用 id。时间是带 T 或明确范围的字符串，不强制所有未知时间变成精确日期；工具不解析时间含义，也不独立判定事实正确性。

`status` 为 `open`、`closed`、`state`；`origin` 为 `text`、`player`、`inference`、`offscreen`。`source` 写原文路径与行范围，或玩家确认的消息定位；此字段由归档侧核查，工具不把填写了来源当成已经验证。推断及幕后草案只有得到玩家明确批准才可提交。

第三层 availability 由世界侧依据剧情及审核决定。涉及遗忘时须将包含旧秘密的既往主观条目标为 false，保留当前可用认知或残留倾向。工具只做字段筛选，不能识别自然语言中的隐含泄密；角色包必须由世界侧审读。

## 操作

运行前将 TEMP、TMP、TMPDIR 及 Python 缓存定向到 D 盘。本项目不需要新增依赖。以下使用可用的 Python 命令，并假设仓库位于 D 盘示例位置：

```powershell
$env:TEMP = 'D:\CodexProject\Storyline-Memory\.tmp'
$env:TMP = $env:TEMP
$env:TMPDIR = $env:TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$storyScript = 'D:\CodexProject\Storyline-Memory\scripts\storyline.py'
$storyData = 'D:\CodexProject\Storyline-Memory\storyline-data'
python $storyScript --root $storyData prepare 'D:\CodexProject\Storyline-Memory\request.json' --out 'D:\CodexProject\Storyline-Memory\proposal.json'
```

`request.json` 示例（由归档侧填写，不要求玩家手写 JSON）：

```json
{
  "tracked": ["A"],
  "through": {"A": "T=0"},
  "sources": [],
  "changes": [{
    "layer": "subjective",
    "character": "A",
    "record": {
      "id": "a-opening",
      "event_id": "opening",
      "t": "T=0",
      "summary": "性格冷淡，成因尚未设定。",
      "status": "state",
      "origin": "player",
      "source": "玩家首次填写的开场状态",
      "available": true
    }
  }]
}
```

准备草案不会更新 HEAD。归档侧比较 `draft.changes` 和当前版，向玩家用自然语言展示增量和待决定项。批准后，使用工具返回的 exact approval 散列调用 `commit proposal.json --approval 散列`；输出版本散列。修改过草案后重新 prepare，不复用旧批准。日常不要向玩家抛出散列或底层 JSON。

- `show`：查看当前完整状态，只在管理侧使用。
- `role A`：只导出 A 当前 availability=true 的第三层正文，不导出来源、真伪标记和客观层。
- `rollback 版本散列`：恢复整版及输入去重记录；版本文件仍保留。由玩家明确要求后执行。

世界侧批准的新感知可先作为第三层增量记录，再导出角色包，不传递用于生成感知的客观原因。角色包只覆盖最小文字输入边界；宿主工具权限需另行落实。

`scripts/test_storyline.py` 提供合成小样本机械验证。它不调用实际模型，不证明三十万字长篇摘要质量、Token优势或硬访问控制。
