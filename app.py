from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from paddleocr import PaddleOCR
import os
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import re
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)


# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

# 初始化OCR引擎
print('正在初始化OCR引擎...')
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print('✅ OCR引擎初始化完成！')

# 加载验证数据
check_data = {}
try:
    with open('check_normalized.json', 'r', encoding='utf-8') as f:
        check_json = json.load(f)
        for bill in check_json.get('bills_of_lading', []):
            filename = bill.get('file_name', '')
            if filename:
                check_data[filename] = bill
    print(f'✅ 加载了 {len(check_data)} 条验证数据')
except Exception as e:
    print(f'⚠️ 加载check_normalized.json失败: {e}')
    check_data = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def calculate_accuracy(extracted_data, ground_truth):
    """计算提取数据的准确率"""
    if not ground_truth or not extracted_data:
        return {
            'overall': 0.0,
            'details': {},
            'message': '无验证数据'
        }
    
    # 从ground_truth中提取documents[0]的数据
    gt_doc = ground_truth.get('detail', {}).get('documents', [{}])[0]
    
    # 定义字段映射和比较规则
    field_comparisons = [
        # 基本信息字段
        ('bl_number', ['bill_info', 'B/L NO'], gt_doc.get('bill_of_lading__number', '')),
        ('vessel', ['bill_info', 'VESSEL'], gt_doc.get('vessel', '')),
        ('voyage', ['bill_info', 'VOYAGE'], gt_doc.get('voyage', '')),
        ('port_of_loading', ['bill_info', 'PORT OF LOADING'], gt_doc.get('place_of_loading', '')),
        ('port_of_discharge', ['bill_info', 'PORT OF DISCHARGE'], gt_doc.get('place_of_discharge', '')),
        ('place_of_delivery', ['bill_info', 'PLACE OF DELIVERY'], gt_doc.get('place_of_delivery', '')),
        ('gross_weight', ['bill_info', 'GROSS WEIGHT'], gt_doc.get('total_gross_weight_value', '')),
        ('measurement', ['bill_info', 'MEASUREMENT'], gt_doc.get('measurement', '')),
        # 发货人信息
        ('shipper_name', ['shipper', 'name'], gt_doc.get('shipper_company_name', '')),
        ('shipper_address', ['shipper', 'address'], gt_doc.get('shipper_address', '')),
        # 收货人信息
        ('consignee_name', ['consignee', 'name'], gt_doc.get('consignee_company_name', '')),
        ('consignee_address', ['consignee', 'address'], gt_doc.get('consignee_address', '')),
    ]
    
    correct = 0
    total = 0
    details = {}
    
    def normalize_text(text):
        """标准化文本用于比较"""
        if isinstance(text, list):
            text = ' '.join(str(t) for t in text)
        text = str(text).strip().upper()
        # 移除多余空格和特殊字符
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[,.:;\-_]', '', text)
        return text
    
    def get_nested_value(data, keys):
        """从嵌套字典中获取值"""
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, '')
            else:
                return ''
        return value
    
    for field_name, extracted_keys, gt_value in field_comparisons:
        total += 1
        
        # 获取提取的值
        extracted_value = get_nested_value(extracted_data, extracted_keys)
        
        # 标准化
        extracted_norm = normalize_text(extracted_value)
        gt_norm = normalize_text(gt_value)
        
        # 比较
        if extracted_norm and gt_norm:
            # 计算相似度（简单的包含关系）
            if extracted_norm == gt_norm:
                is_correct = True
                similarity = 1.0
            elif extracted_norm in gt_norm or gt_norm in extracted_norm:
                is_correct = True
                similarity = 0.8
            else:
                # 计算Jaccard相似度
                set1 = set(extracted_norm.split())
                set2 = set(gt_norm.split())
                if set1 and set2:
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    similarity = intersection / union if union > 0 else 0
                    is_correct = similarity >= 0.6
                else:
                    is_correct = False
                    similarity = 0
            
            if is_correct:
                correct += 1
            
            details[field_name] = {
                'extracted': str(extracted_value)[:100],
                'ground_truth': str(gt_value)[:100],
                'correct': is_correct,
                'similarity': similarity
            }
        elif not extracted_norm and not gt_norm:
            # 都为空也算正确
            correct += 1
            details[field_name] = {
                'extracted': '',
                'ground_truth': '',
                'correct': True,
                'similarity': 1.0
            }
        else:
            # 一个为空一个不为空
            details[field_name] = {
                'extracted': str(extracted_value)[:100],
                'ground_truth': str(gt_value)[:100],
                'correct': False,
                'similarity': 0
            }
    
    overall_accuracy = (correct / total * 100) if total > 0 else 0
    
    return {
        'overall': round(overall_accuracy, 2),
        'correct_fields': correct,
        'total_fields': total,
        'details': details
    }

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
        
        # 计算准确率（如果存在验证数据）
        accuracy = None
        original_filename = secure_filename(file.filename)  # 原始文件名（不带时间戳）
        if original_filename in check_data:
            print(f'📊 找到验证数据，正在计算准确率...')
            ground_truth = check_data[original_filename]
            accuracy = calculate_accuracy(extracted_data, ground_truth)
            print(f'✅ 准确率: {accuracy["overall"]}% ({accuracy["correct_fields"]}/{accuracy["total_fields"]} 字段正确)')
        else:
            print(f'⚠️ 未找到验证数据: {original_filename}')
        
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
            'extracted': extracted_data,
            'accuracy': accuracy
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
    """使用 HKBU GenAI (Gemini 2.5 Pro) 提取提单关键信息"""
    import requests
    import json
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    API_URL = os.getenv('API_URL', 'https://genai.hkbu.edu.hk/api/v0/rest/deployments/gemini-2.5-pro/chat/completions?api-version=v1')
    API_KEY = os.getenv('API_KEY', 'efd90a7f-da6b-4bc3-af47-52344b6ee95b')
    
    # 合并所有OCR文本
    full_text = "\n".join([str(t) for t in texts if t])
    
    # 构建提示词
    prompt = f"""你是一个专业的提单数据提取助手。请从以下OCR识别的海运提单文本中提取关键信息。

OCR文本：
{full_text}

请提取以下信息并以JSON格式返回（如果某字段未找到，请返回空字符串）：
{{
    "shipper_name": "发货人公司名称",
    "shipper_address": "发货人完整地址（保持原始格式，多行用\\n分隔）",
    "consignee_name": "收货人公司名称",
    "consignee_address": "收货人完整地址（保持原始格式，多行用\\n分隔）",
    "bl_number": "提单号（如OH-123456）",
    "vessel": "船名",
    "voyage": "航次",
    "port_of_loading": "装货港",
    "port_of_discharge": "卸货港",
    "place_of_delivery": "交货地点",
    "cargo_description": "货物描述（保持原始格式，多行用\\n分隔）",
    "container_info": "集装箱号和类型",
    "gross_weight": "毛重",
    "measurement": "体积"
}}

重要提示：
1. 只返回JSON格式的数据，不要有任何额外的解释或说明文字
2. 确保JSON格式正确，可以被直接解析
3. 如果某个字段在文本中没有找到，返回空字符串 ""
4. 保持地址和货物描述的原始换行格式"""

    try:
        # 构建请求
        headers = {
            'Content-Type': 'application/json',
            'api-key': API_KEY
        }
        
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的提单数据提取助手，只返回有效的JSON格式数据，不包含任何markdown标记或额外说明。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0,  # 降低随机性
            "max_tokens": 2000,
            "top_p": 1
        }
        
        print('📡 正在调用 HKBU GenAI API...')
        
        # 发送请求
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=30  # 30秒超时
        )
        
        # 检查响应状态
        if response.status_code != 200:
            print(f'❌ API 请求失败: {response.status_code}')
            print(f'错误信息: {response.text}')
            raise Exception(f'API返回错误: {response.status_code}')
        
        # 解析响应
        response_data = response.json()
        print('✅ API 调用成功')
        
        # 提取LLM返回的内容
        result_text = response_data['choices'][0]['message']['content'].strip()
        
        print(f'📝 LLM 原始返回:\n{result_text}\n')
        
        # 清理返回内容（移除可能的markdown代码块标记）
        if result_text.startswith('```'):
            # 移除markdown代码块
            lines = result_text.split('\n')
            result_text = '\n'.join(lines[1:-1])  # 去掉第一行和最后一行
            if result_text.startswith('json'):
                result_text = result_text[4:].strip()
        
        # 解析JSON
        result = json.loads(result_text)
        
        print('✅ JSON 解析成功')
        print(f'📊 提取到的数据:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n')
        
        # 转换为系统需要的格式
        info = {
            'shipper': {
                'name': result.get('shipper_name', ''),
                'address': [line.strip() for line in result.get('shipper_address', '').split('\n') if line.strip()]
            },
            'consignee': {
                'name': result.get('consignee_name', ''),
                'address': [line.strip() for line in result.get('consignee_address', '').split('\n') if line.strip()]
            },
            'bill_info': {
                'B/L NO': result.get('bl_number', ''),
                'VESSEL': result.get('vessel', ''),
                'VOYAGE': result.get('voyage', ''),
                'PORT OF LOADING': result.get('port_of_loading', ''),
                'PORT OF DISCHARGE': result.get('port_of_discharge', ''),
                'PLACE OF DELIVERY': result.get('place_of_delivery', ''),
                'GROSS WEIGHT': result.get('gross_weight', ''),
                'MEASUREMENT': result.get('measurement', ''),
            },
            'cargo': [line.strip() for line in result.get('cargo_description', '').split('\n') if line.strip()] if result.get('cargo_description') else [],
            'container_info': result.get('container_info', '')
        }
        
        return info
        
    except requests.exceptions.Timeout:
        print('❌ API 请求超时')
        return {
            'shipper': {'name': '', 'address': []},
            'consignee': {'name': '', 'address': []},
            'bill_info': {},
            'cargo': [],
            'error': 'API请求超时'
        }
        
    except requests.exceptions.RequestException as e:
        print(f'❌ 网络请求失败: {str(e)}')
        return {
            'shipper': {'name': '', 'address': []},
            'consignee': {'name': '', 'address': []},
            'bill_info': {},
            'cargo': [],
            'error': f'网络请求失败: {str(e)}'
        }
        
    except json.JSONDecodeError as e:
        print(f'❌ JSON 解析失败: {str(e)}')
        print(f'原始返回内容: {result_text}')
        return {
            'shipper': {'name': '', 'address': []},
            'consignee': {'name': '', 'address': []},
            'bill_info': {},
            'cargo': [],
            'error': f'JSON解析失败: {str(e)}'
        }
        
    except Exception as e:
        print(f'❌ LLM 提取失败: {str(e)}')
        import traceback
        traceback.print_exc()
        
        return {
            'shipper': {'name': '', 'address': []},
            'consignee': {'name': '', 'address': []},
            'bill_info': {},
            'cargo': [],
            'error': f'LLM提取失败: {str(e)}'
        }

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