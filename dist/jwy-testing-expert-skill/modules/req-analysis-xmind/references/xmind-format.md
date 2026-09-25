# XMind 格式参考

## 新版 XMind 文件格式规范

XMind 8+ 使用 zip 包格式，内部包含以下文件：

### content.json

```json
[
  {
    "id": "sheet-uuid",
    "class": "sheet",
    "title": "画布标题",
    "rootTopic": {
      "id": "root-uuid",
      "class": "attached topic",      // 根节点必须用 "attached topic"
      "title": "根节点标题",
      "titleUnedited": false,
      "children": {
        "attached": [                   // 子节点列表
          {
            "id": "child-uuid",
            "class": "attached",        // 子节点用 "attached"（不是 "attached topic"）
            "title": "子节点标题",
            "titleUnedited": false,
            "children": {
              "attached": [...]         // 可继续嵌套
            }
          }
        ]
      }
    },
    "relationships": [],
    "extensions": [],
    "topicPositioning": "fixed",
    "topicOverlapping": "overlap"
  }
]
```

### metadata.json

```json
{
  "modifier": "WorkBuddy 1.0",
  "dataStructureVersion": "1",
  "layoutEngineVersion": "2",
  "activeSheetId": "sheet-uuid"         // 必须指向 content.json 中 sheet 的 id
}
```

### manifest.json

```json
{
  "file-entries": {
    "content.json": {},
    "metadata.json": {}
  }
}
```

## 关键规则

1. **ID 格式**：必须使用完整 UUID（`str(uuid.uuid4())`），不能用短格式如 hex[:20]
2. **根节点 class**：`"attached topic"`，子节点 class：`"attached"`
3. **必须包含 manifest.json**：否则新版 XMind 无法打开文件
4. **activeSheetId**：metadata.json 中必须指向有效的 sheet id
5. **编码**：`json.dumps` 设置 `ensure_ascii=False` 保证中文正常写入
6. **zip 压缩方式**：使用 `zipfile.ZIP_DEFLATED`

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| XMind 无法打开 | 缺少 manifest.json | 添加 manifest.json |
| 节点显示异常 | 根节点 class 写成 "attached" | 改为 "attached topic" |
| ID 冲突 | 使用短格式 ID | 使用完整 UUID |
| 中文乱码 | ensure_ascii=True | 设置 ensure_ascii=False |

## 不要使用旧版 Python xmind 库

`pip install xmind` 生成的格式不兼容 XMind 8+，应直接使用 json + zipfile + uuid 构建。
