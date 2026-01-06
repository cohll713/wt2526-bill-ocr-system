from flask import Flask, render_template, request, jsonify, send_file
from paddleocr import PaddleOCR
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import re

app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

# 初始化OCR引擎
print('正在初始化OCR引擎...')
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print('✅ OCR引擎初始化完成！')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件上传'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400
        
        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 执行OCR识别
        print(f'正在识别: {filepath}')
        print(f'文件大小: {os.path.getsize(filepath)} bytes')
        
        result = ocr.ocr(filepath)
        
        print(f'OCR原始结果类型: {type(result)}')
        
        # ✅ 处理新版本 PaddleOCR 返回的字典格式
        texts = []
        scores = []
        
        if result and isinstance(result, list) and len(result) > 0:
            first_result = result[0]
            
            # 新版本返回字典格式
            if isinstance(first_result, dict):
                print('检测到新版本 PaddleOCR 字典格式')
                
                rec_texts = first_result.get('rec_texts', [])
                rec_scores = first_result.get('rec_scores', [])
                
                print(f'识别到 {len(rec_texts)} 个文本块')
                
                for text, score in zip(rec_texts, rec_scores):
                    text = str(text).strip()
                    if text:
                        texts.append(text)
                        scores.append(float(score))
            
            # 旧版本返回列表格式
            elif isinstance(first_result, list):
                print('检测到旧版本 PaddleOCR 列表格式')
                
                for line in first_result:
                    try:
                        if line and len(line) >= 2:
                            if isinstance(line[1], tuple) and len(line[1]) >= 2:
                                text = str(line[1][0]).strip()
                                score = float(line[1][1])
                                
                                if text:
                                    texts.append(text)
                                    scores.append(score)
                    except Exception as e:
                        print(f'处理单行时出错: {e}')
                        continue
        
        print(f'✅ 最终识别到 {len(texts)} 行文字')
        
        if len(texts) == 0:
            return jsonify({
                'error': '未识别到文字内容',
                'detail': '图片可能质量不佳或不包含文字'
            }), 400
        
        # 打印前几行识别结果
        print('\n识别结果预览:')
        for i, (text, score) in enumerate(list(zip(texts, scores))[:10]):
            print(f'  {i+1}. {text[:60]:<60} (置信度: {score*100:.1f}%)')
        
        # 提取关键字段
        extracted_data = extract_bill_info(texts)
        
        # 构建返回结果
        ocr_data = {
            'filename': filename,
            'total_lines': len(texts),
            'average_confidence': sum(scores) / len(scores) if scores else 0,
            'texts': [
                {
                    'text': text,
                    'confidence': float(score)
                }
                for text, score in zip(texts, scores)
            ],
            'extracted': extracted_data
        }
        
        # 保存结果
        result_filename = f"{timestamp}_result.json"
        result_path = os.path.join(app.config['OUTPUT_FOLDER'], result_filename)
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_data, f, ensure_ascii=False, indent=2)
        
        # 保存纯文本结果
        txt_filename = f"{timestamp}_ocr.txt"
        txt_path = os.path.join(app.config['OUTPUT_FOLDER'], txt_filename)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"识别文件: {filename}\n")
            f.write(f"识别时间: {timestamp}\n")
            f.write(f"总行数: {len(texts)}\n")
            f.write(f"平均置信度: {ocr_data['average_confidence']*100:.2f}%\n")
            f.write("="*80 + "\n\n")
            for i, (text, score) in enumerate(zip(texts, scores), 1):
                f.write(f"{i:3d}. {text:<80} (置信度: {score*100:.1f}%)\n")
        
        print(f'\n✅ 识别完成！保存到: {result_filename}')
        print(f'   文本文件: {txt_filename}')
        
        return jsonify({
            'success': True,
            'data': ocr_data
        })
            
    except Exception as e:
        print(f'\n❌ 错误: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

def extract_bill_info(texts):
    """从识别的文字中提取关键信息"""
    
    info = {
        'shipper': {'name': '', 'address': []},
        'consignee': {'name': '', 'address': []},
        'bill_info': {},
        'cargo': []
    }
    
    # 标志变量
    in_shipper_section = False
    in_consignee_section = False
    shipper_lines = []
    consignee_lines = []
    
    for i, text in enumerate(texts):
        if not text or not isinstance(text, str):  # ✅ 添加安全检查
            continue
            
        text_upper = text.upper().strip()
        
        # ===== 识别发货人区域 =====
        if 'SHIPPER' in text_upper and 'EXPORTER' in text_upper:
            in_shipper_section = True
            in_consignee_section = False
            shipper_lines = []
            continue
        
        # ===== 识别收货人区域 =====
        if 'CONSIGNEE' in text_upper:
            in_consignee_section = True
            in_shipper_section = False
            consignee_lines = []
            continue
        
        # ===== 收集发货人信息 =====
        if in_shipper_section:
            if any(keyword in text_upper for keyword in ['B/L NO', 'CONSIGNEE', 'NOTIFY', 'VESSEL', 'PORT OF']):
                in_shipper_section = False
            else:
                if not any(skip in text_upper for skip in ['S/O NO', 'OTT NO', 'REF#', 'EIN#', 'TEL:', 'FAX:']):
                    shipper_lines.append(text.strip())
        
        # ===== 收集收货人信息 =====
        if in_consignee_section:
            if any(keyword in text_upper for keyword in ['NOTIFY', 'VESSEL', 'PORT OF', 'CONTAINER']):
                in_consignee_section = False
            else:
                if not any(skip in text_upper for skip in ['NOT NEGOTIABLE', 'UNLESS']):
                    consignee_lines.append(text.strip())
        
        # ===== 提取提单信息字段 =====
        
        # B/L NO
        if 'B/L NO' in text_upper:
            if i + 1 < len(texts) and texts[i + 1]:  # ✅ 添加安全检查
                next_text = texts[i + 1].strip()
                if re.match(r'^[A-Z]{2}[-\s]?\d+', next_text, re.IGNORECASE):
                    info['bill_info']['B/L NO'] = next_text
            elif ':' in text:
                parts = text.split(':', 1)
                if len(parts) > 1 and parts[1].strip():  # ✅ 添加安全检查
                    info['bill_info']['B/L NO'] = parts[1].strip()
        
        # 直接识别提单号
        if re.match(r'^OH[-\s]?\d+', text, re.IGNORECASE):
            info['bill_info']['B/L NO'] = text.strip()
        
        # 船名
        if 'VESSEL' in text_upper and 'VOY' not in text_upper:
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) > 1 and parts[1].strip():  # ✅ 添加安全检查
                    info['bill_info']['VESSEL'] = parts[1].strip()
        
        # 航次
        if 'VOYAGE' in text_upper or 'VOY' in text_upper:
            match = re.search(r'VOY[A-Z]*[:\s]+([A-Z0-9]+)', text_upper)
            if match:
                info['bill_info']['VOYAGE'] = match.group(1)
        
        # 装货港
        if 'PORT OF LOADING' in text_upper:
            if i + 1 < len(texts) and texts[i + 1]:  # ✅ 添加安全检查
                info['bill_info']['PORT OF LOADING'] = texts[i + 1].strip()
        
        # 卸货港
        if 'PORT OF DISCHARGE' in text_upper:
            if i + 1 < len(texts) and texts[i + 1]:  # ✅ 添加安全检查
                info['bill_info']['PORT OF DISCHARGE'] = texts[i + 1].strip()
        
        # 货物描述
        if any(keyword in text_upper for keyword in ['PALLETS', 'CASES', 'KGS', 'HS CODE']) or re.search(r'\d{6}', text):
            if text.strip() and text not in info['cargo']:  # ✅ 添加安全检查
                info['cargo'].append(text.strip())
    
    # 处理发货人和收货人信息
    if shipper_lines:
        info['shipper']['name'] = shipper_lines[0] if shipper_lines else ''
        info['shipper']['address'] = shipper_lines[1:] if len(shipper_lines) > 1 else []
    
    if consignee_lines:
        info['consignee']['name'] = consignee_lines[0] if consignee_lines else ''
        info['consignee']['address'] = consignee_lines[1:] if len(consignee_lines) > 1 else []
    
    return info

@app.route('/history')
def history():
    """查看历史记录"""
    results = []
    if os.path.exists(app.config['OUTPUT_FOLDER']):
        for filename in sorted(os.listdir(app.config['OUTPUT_FOLDER']), reverse=True):
            if filename.endswith('.json'):
                filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        results.append({
                            'filename': filename,
                            'timestamp': filename.split('_')[0] + '_' + filename.split('_')[1] if '_' in filename else filename,  # ✅ 添加安全检查
                            'data': data
                        })
                except Exception as e:
                    print(f'读取历史记录失败: {filename}, 错误: {e}')
    return jsonify({'success': True, 'results': results})

@app.route('/download/<filename>')
def download_file(filename):
    """下载结果文件"""
    try:
        return send_file(
            os.path.join(app.config['OUTPUT_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    # 确保文件夹存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    print('='*80)
    print('🚀 提单OCR识别系统启动中...')
    print('='*80)
    print('📍 访问地址: http://127.0.0.1:5000')
    print('📍 或者访问: http://localhost:5000')
    print('='*80)
    
    app.run(debug=True, host='0.0.0.0', port=5000)