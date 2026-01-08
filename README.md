# 📦 提单OCR识别系统

基于 PaddleOCR 和大语言模型的智能海运提单信息提取系统。

## ✨ 功能特点

- **🔍 高精度OCR**: 使用 PaddleOCR 引擎，支持英文识别
- **🤖 AI智能提取**: 采用 HKBU GenAI (Gemini 2.5 Pro) 进行智能字段提取
- **📊 准确率验证**: 自动计算提取准确率并与标准数据对比
- **🌐 Web界面**: 基于 Flask 的友好用户界面
- **📁 多格式支持**: 支持 PNG、JPG、JPEG 和 PDF 文件
- **📈 历史记录**: 查看和下载历史识别结果
- **💾 结构化输出**: JSON 和文本格式输出，便于集成

## 📋 系统要求

- Python 3.8+
- Windows/Linux/macOS
- 推荐 4GB+ 内存用于 PaddleOCR

## 🚀 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/cohll713/wt2526-bill-ocr-system.git
cd wt2526-bill-ocr-system
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install flask flask-cors paddleocr paddlepaddle python-dotenv requests werkzeug
```

### 4. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
API_URL=https://genai.hkbu.edu.hk/api/v0/rest/deployments/gemini-2.5-pro/chat/completions?api-version=v1
API_KEY=your-api-key-here
```

> **注意**: 请将 `your-api-key-here` 替换为你的 HKBU GenAI API 密钥。

## 📖 使用方法

### 启动服务器

```bash
python app.py
```

服务器将在 `http://localhost:5000` 启动

### Web 界面使用

1. 打开浏览器访问 `http://localhost:5000`
2. 点击"选择文件"上传提单图片
3. 点击"上传并处理"
4. 查看提取的信息和准确率指标
5. 根据需要下载结果

### API 接口

#### `POST /upload`
上传并处理提单图片。

**请求:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (图片文件)

**响应:**
```json
{
  "success": true,
  "data": {
    "filename": "20260108_142146_bill.jpg",
    "total_lines": 45,
    "average_confidence": 0.95,
    "texts": [...],
    "extracted": {
      "shipper": {...},
      "consignee": {...},
      "bill_info": {...}
    },
    "accuracy": {
      "overall": 85.5,
      "correct_fields": 10,
      "total_fields": 12
    }
  }
}
```

#### `GET /history`
获取处理历史记录。

**响应:**
```json
{
  "success": true,
  "results": [...]
}
```

#### `GET /download/<filename>`
下载指定的结果文件。

## 📁 项目结构

```
wt2526-bill-ocr-system/
├── app.py                      # Flask 主应用
├── extract_texts.py            # 文本提取工具
├── image_processor.py          # 图片预处理
├── label_tool.py               # 手动标注工具
├── smart_label.py              # AI 辅助标注
├── auto_label.py               # 自动批量标注
├── prepare_training_data.py    # 训练数据准备
├── train_model.py              # 模型训练脚本
├── normalise_check.py          # 数据标准化
├── test_ocr.py                 # OCR 测试工具
├── requirements.txt            # Python 依赖
├── .env                        # 环境配置
├── check_normalized.json       # 验证标准数据
├── templates/
│   └── index.html             # Web 界面
├── uploads/                    # 上传文件目录
├── outputs/                    # OCR 结果 (JSON + TXT)
├── models/                     # 训练模型
└── test_images/               # 测试图片
```

## 🔧 提取字段

系统从提单中提取以下信息：

### 发货人信息
- 公司名称
- 完整地址

### 收货人信息
- 公司名称
- 完整地址

### 提单信息
- 提单号 (B/L Number)
- 船名 (Vessel)
- 航次 (Voyage)
- 装货港 (Port of Loading)
- 卸货港 (Port of Discharge)
- 交货地点 (Place of Delivery)
- 毛重 (Gross Weight)
- 体积 (Measurement)

### 其他字段
- 货物描述
- 集装箱信息

## 📊 准确率验证

当 `check_normalized.json` 中存在标准数据时，系统会自动计算提取准确率，提供：

- **总体准确率百分比**
- **逐字段对比**
- **部分匹配的相似度评分**
- **详细的差异报告**

## 🛠️ 辅助工具

### 标注工具
手动标注界面，用于创建训练数据：
```bash
python label_tool.py
```

### 智能标注
使用大语言模型辅助标注：
```bash
python smart_label.py
```

### 自动标注
批量自动标注：
```bash
python auto_label.py
```

### OCR 测试
测试特定图片的 OCR 效果：
```bash
python test_ocr.py
```

## 📝 输出格式

### JSON 输出
结构化数据保存在 `outputs/` 文件夹：
```json
{
  "filename": "...",
  "total_lines": 45,
  "average_confidence": 0.95,
  "texts": [...],
  "extracted": {...},
  "accuracy": {...}
}
```


## 👥 作者

- Coco Li (香港浸会大学)

## 🙏 致谢

- PaddleOCR 提供的 OCR 引擎
- HKBU GenAI 提供的大语言模型 API
- Flask 框架提供的 Web 支持


