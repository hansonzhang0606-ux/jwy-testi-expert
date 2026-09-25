# XMind 2.0 文件格式速查

`.xmind` 本质是 zip 包，标准结构：

```
xxx.xmind
├── content.xml      # 节点树（核心）
├── styles.xml       # 主题/样式
├── meta.xml         # 元数据（作者、时间）
├── META-INF/
│   └── manifest.xml # 文件清单
└── Thumbnails/
    └── thumbnail.png (可选，缩略图)
```

## content.xml 结构
```xml
<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" ... version="2.0">
  <sheet id="sheet1" theme="6bqonjeshs1b09a83dba89uaeq">
    <topic id="t0001" style-id="361fa45tvq7e250pmv9qh8urg5">
      <title svg:width="500">中心主题</title>
      <children>
        <topics type="attached">
          <topic id="t0002"><title>分支</title>...</topic>
        </topics>
      </children>
    </topic>
    <title>画布 1</title>
  </sheet>
</xmap-content>
```

要点：
- `topic` 可无限嵌套 `children > topics > topic`。
- 中心主题（depth=0）带 `style-id="361fa45tvq7e250pmv9qh8urg5"`（商业 II 的中心主题样式）。
- 普通子节点不带 style，沿用主题默认。

## 主题（商业 II）
`theme id = 6bqonjeshs1b09a83dba89uaeq`，样式在 `styles.xml` 的 master-styles 中定义。生成器已内置完整 styles.xml，无需手改。

## 校验方式
```python
import zipfile, xml.etree.ElementTree as ET
with zipfile.ZipFile("x.xmind") as z:
    root = ET.fromstring(z.read("content.xml"))
ns = {"x": "urn:xmind:xmap:xmlns:content:2.0"}
topics = root.findall(".//x:topic", ns)
print("节点数:", len(topics))
```

## 注意事项
- 中文/特殊字符需 XML 转义：`& < > "`。
- 用 `zipfile.ZIP_DEFLATED` 打包，XMind 可正常打开。
- 不含 `Thumbnails/thumbnail.png` 也能打开（仅缺预览图），生成器默认不生成以保证轻量。
