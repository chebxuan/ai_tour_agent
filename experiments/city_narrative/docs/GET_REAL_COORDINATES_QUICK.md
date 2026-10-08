# 获取真实坐标 - 快速指南

## 🚀 三步完成（约5分钟）

### 步骤1：获取坐标（3分钟）

```bash
python scripts/add_coordinates_amap.py "你的高德API_Key"
```

**输出**：`city_narratives_amap_coords.csv`（GCJ-02坐标）

### 步骤2：坐标纠偏（30秒）

```bash
python scripts/convert_coordinates.py city_narratives_amap_coords.csv
```

**输出**：`city_narratives_wgs84_coords.csv`（WGS-84坐标）

### 步骤3：生成地图（10秒）

```bash
python scripts/visualize_map.py city_narratives_wgs84_coords.csv shanghai_landmarks_map.html
```

**输出**：`shanghai_landmarks_map.html`

## 📊 预期结果

| 项目 | 结果 |
|-----|------|
| 成功率 | >95% (180+/192) |
| 处理时间 | ~3分钟 |
| 坐标精度 | ~10米 |
| 地图质量 | 真实、精确 |

## 🗺️ 查看地图

```bash
# 浏览器中打开
python -c "import webbrowser; webbrowser.open('shanghai_landmarks_map.html')"
```

## ⚠️ 注意事项

### API配额
- 高德API免费版：2000次/天
- 本次调用：192次
- 剩余额度：1808次（每天重置）

### 处理时间
- 192个地标约3分钟
- 速率限制：1次/秒

### 坐标精度
- GCJ-02 → WGS-84纠偏后
- 精度约10米
- 适用于Google Maps、OpenStreetMap

## 🔧 常见问题

### Q: API调用失败？

**A**:
- 检查API Key是否正确
- 确认有"地理编码"权限
- 查看剩余配额

### Q: 部分地标未能获取坐标？

**A**:
- 检查地标名称和地址
- 使用Google Maps手动补充
- 在CSV中填入latitude和longitude

### Q: 坐标位置有偏移？

**A**:
- 已进行坐标纠偏
- 偏移量约几十米
- 纠偏后精度约10米

## 💡 下一步

✅ 路线流动可视化（方案D）

现在有了真实坐标，可以开始实现地标之间的连线功能！
