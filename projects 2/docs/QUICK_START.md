# 快速使用指南

## 🚀 5步完成地标提取和可视化

### 步骤1：准备数据

创建 `assets/shanghai_regions.json`：

```json
{
  "regions": [
    {
      "id": 1,
      "name": "区域名称",
      "notes": [
        {
          "id": 1,
          "title": "笔记1",
          "content": "粘贴小红书游记内容"
        }
      ]
    }
  ]
}
```

### 步骤2：提取地标

```bash
python scripts/process_city.py assets/shanghai_regions.json
```

**输出**：`city_narratives.csv`（192个地标）

### 步骤3：获取真实坐标

```bash
# 高德API获取坐标
python scripts/add_coordinates_amap.py "你的API_Key"

# 坐标纠偏
python scripts/convert_coordinates.py city_narratives_amap_coords.csv
```

**输出**：`city_narratives_wgs84_coords.csv`（143个有效坐标）

### 步骤4：生成地图

```bash
python scripts/visualize_map.py city_narratives_wgs84_coords.csv shanghai_landmarks_map.html
```

**输出**：`shanghai_landmarks_map.html`（交互式地图）

### 步骤5：查看地图

```bash
# 浏览器中打开
python -c "import webbrowser; webbrowser.open('shanghai_landmarks_map.html')"
```

## 📊 输出文件

| 文件 | 内容 | 数量 |
|-----|------|------|
| `city_narratives.csv` | 标准化数据库 | 192个地标 |
| `shanghai_landmarks.json` | 完整数据 | 192个地标 |
| `shanghai_landmarks_map.html` | 交互式地图 | 143个标记 |

## 🗺️ 地图功能

- ✅ 143个真实坐标地标
- ✅ 7种类型颜色区分
- ✅ 点击查看详情
- ✅ 热力图层
- ✅ 缩放拖动

## 📈 数据分布

| 类型 | 数量 | 占比 | 颜色 |
|-----|------|------|------|
| 历史 | 60 | 31.2% | 蓝色 |
| 购物 | 51 | 26.6% | 绿色 |
| 视觉 | 35 | 18.2% | 橙色 |
| 味觉 | 31 | 16.1% | 红色 |
| 放空 | 11 | 5.7% | 紫色 |
| 其他 | 4 | 2.1% | 灰色 |

## ⚠️ 注意事项

### API配额
- 高德API：2000次/天
- 本次使用：192次
- 剩余配额：1808次

### 坐标覆盖率
- 总地标：192个
- 有效坐标：143个（74.5%）
- 缺失坐标：49个（25.5%）

### 坐标精度
- 纠偏后精度：约10米
- 适用范围：Google Maps、OpenStreetMap

## 🔧 常见问题

### Q: 地图打开后是空白？

**A**: 刷新页面（Ctrl+F5），检查网络连接

### Q: 如何补充缺失坐标？

**A**:
1. 使用Google Maps搜索地标
2. 右键点击"此处是什么"
3. 复制坐标填入CSV
4. 重新生成地图

### Q: API调用失败？

**A**: 检查API Key权限，确保有"地理编码"权限

## 💡 下一步

- 补充49个缺失坐标
- 实现路线流动可视化
- 开发路线规划功能
