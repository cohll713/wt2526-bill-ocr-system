from paddleocr import PaddleOCR
import os
import re
import json

# 初始化OCR
print('正在初始化OCR引擎...')
ocr = PaddleOCR(use_textline_orientation=True, lang='en')
print('✅ OCR引擎初始化成功！\n')

# 测试图片路径
test_image = 'test_images/acs-No. OH23040018.png'

def extract_bill_info(texts):
    """智能提取提单关键信息 - 最终修复版"""
    info = {
        'shipper': {'name': '', 'address': []},
        'consignee': {'name': '', 'address': []},
        'bill_info': {},
        'goods_info': []
    }
    
    # 第一步：先提取所有独立字段（不依赖状态机）
    for i, text in enumerate(texts):
        text_stripped = text.strip()
        text_upper = text_stripped.upper()
        
        # B/L NO - 找到标签行，跳过空行，取第一个非空行
        if text_stripped == 'B/L NO.':
            # 向后查找，跳过空行和其他标签
            for j in range(i + 1, min(i + 5, len(texts))):
                next_text = texts[j].strip()
                # 跳过空行和其他标签行
                if not next_text or any(skip in next_text for skip in ['EIN#', 'REF#', 'TEL:', 'S/O NO']):
                    continue
                # 找到 B/L 号（格式：XX-XXXXXXXX）
                if re.match(r'^[A-Z]{2}-\d+', next_text):
                    info['bill_info']['B/L NO'] = next_text
                    break
        
        # OTI/OTT NO
        elif text_stripped.startswith('OTT NO.') or text_stripped.startswith('OTI NO.'):
            oti_no = text_stripped.split('.', 1)[1].strip()
            if oti_no:  # 确保不是空的
                info['bill_info']['OTI NO'] = oti_no
        
        # REF#
        elif text_stripped.startswith('REF#:'):
            info['bill_info']['REF'] = text_stripped.replace('REF#:', '').strip()
        
        # EIN#
        elif text_stripped.startswith('EIN#:'):
            info['bill_info']['EIN'] = text_stripped.replace('EIN#:', '').strip()
        
        # TEL (只提取发货人的电话，排除收货人的 +84)
        elif text_stripped.startswith('TEL:') and '+84' not in text_stripped:
            info['bill_info']['TEL'] = text_stripped.replace('TEL:', '').strip()
        
        # 货物信息
        elif 'PALLETS' in text_upper and 'CASES' in text_upper:
            info['goods_info'].append(text_stripped)
        
        elif 'HS CODE' in text_upper or 'SYRUP' in text_upper or 'FLAVORING' in text_upper:
            if text_stripped not in info['goods_info']:
                info['goods_info'].append(text_stripped)
    
    # 第二步：提取发货人和收货人信息（使用状态机）
    i = 0
    current_section = None
    
    while i < len(texts):
        text = texts[i].strip()
        text_upper = text.upper()
        
        # ===== 发货人部分 =====
        if 'SHIPPER/EXPORTER' in text_upper:
            current_section = 'shipper'
            i += 1
            
            # 跳过所有标签行，找到公司名
            while i < len(texts):
                next_text = texts[i].strip()
                # 跳过标签行和空行
                if not next_text or any(skip in next_text for skip in ['S/O NO', 'OTT NO', 'IT NO', 'REF#', 'B/L NO', 'EIN#', 'TEL:']):
                    i += 1
                    continue
                # 找到公司名（全大写或标题格式，不以数字开头）
                if next_text and not re.match(r'^\d+', next_text):
                    info['shipper']['name'] = next_text
                    i += 1
                    break
                i += 1
            
            # 收集地址
            while i < len(texts):
                addr = texts[i].strip()
                if 'CONSIGNEE' in addr.upper():
                    current_section = None
                    break
                # 地址特征
                if any(kw in addr.upper() for kw in ['BOULEVARD', 'STREET', 'AVENUE', 'ROAD', 'CA ', 'UNITED STATES']) or re.search(r'\b\d{5}\b', addr):
                    if addr and 'TEL:' not in addr and 'EIN#' not in addr:
                        info['shipper']['address'].append(addr)
                i += 1
        
        # ===== 收货人部分 =====
        elif 'CONSIGNEE' in text_upper and 'NOT NEGOTIABLE' in text_upper:
            current_section = 'consignee'
            i += 1
            
            # 下一行是收货人名称
            if i < len(texts):
                info['consignee']['name'] = texts[i].strip()
                i += 1
            
            # 收集地址
            while i < len(texts):
                addr = texts[i].strip()
                if 'NOTIFY PARTY' in addr.upper() or 'Alliance' in addr:
                    current_section = None
                    break
                if addr and not addr.startswith('SAME'):
                    info['consignee']['address'].append(addr)
                i += 1
        
        else:
            i += 1
    
    # 清理发货人地址中的重复项
    if info['shipper']['address']:
        info['shipper']['address'] = list(dict.fromkeys(info['shipper']['address']))
    
    return info

if os.path.exists(test_image):
    print(f'正在识别图片: {test_image}')
    print('='*80)
    
    # 使用新的API方法
    result = ocr.predict(test_image)
    
    # 提取识别结果
    if result and len(result) > 0:
        ocr_result = result[0]
        texts = ocr_result['rec_texts']
        scores = ocr_result['rec_scores']
        
        print(f'\n📄 OCR识别结果（共 {len(texts)} 行文字）')
        print('='*80)
        
        # 显示前20行预览
        for idx, (text, score) in enumerate(zip(texts[:20], scores[:20]), 1):
            print(f'{idx:3d}. {text:60s} (置信度: {score:.1%})')
        print(f'... (还有 {len(texts) - 20} 行)')
        print('='*80)
        
        # 智能提取关键信息
        bill_info = extract_bill_info(texts)
        
        # 显示提取的关键信息
        print('\n🔍 提取的关键信息：')
        print('='*80)
        
        # 发货人信息
        print('\n📦 发货人信息 (SHIPPER):')
        print(f'  • 公司名称: {bill_info["shipper"]["name"]}')
        if bill_info["shipper"]["address"]:
            for addr in bill_info["shipper"]["address"]:
                print(f'  • 地址: {addr}')
        
        # 收货人信息
        print('\n📬 收货人信息 (CONSIGNEE):')
        print(f'  • 公司名称: {bill_info["consignee"]["name"]}')
        if bill_info["consignee"]["address"]:
            for addr in bill_info["consignee"]["address"]:
                print(f'  • 地址: {addr}')
        
        # 提单信息
        print('\n📋 提单信息:')
        if bill_info["bill_info"]:
            for key, value in bill_info["bill_info"].items():
                print(f'  • {key}: {value}')
        else:
            print('  • 未提取到提单信息')
        
        # 货物信息
        print('\n📊 货物信息:')
        if bill_info["goods_info"]:
            for goods in bill_info["goods_info"]:
                print(f'  • {goods}')
        else:
            print('  • 未提取到货物信息')
        
        print('='*80)
        
        # 保存完整文本
        full_text = '\n'.join(texts)
        with open('ocr_result.txt', 'w', encoding='utf-8') as f:
            f.write(full_text)
        
        # 保存结构化信息为JSON
        with open('bill_info.json', 'w', encoding='utf-8') as f:
            json.dump(bill_info, f, indent=2, ensure_ascii=False)
        
        print(f'\n✅ 识别完成！')
        print(f'✅ 原始文本已保存到: ocr_result.txt')
        print(f'✅ 结构化信息已保存到: bill_info.json')
        print(f'✅ 共识别出 {len(texts)} 行文字')
        
        # Debug: 显示 B/L NO 附近的行
        print('\n🐛 调试信息 - B/L NO 附近的行:')
        print('='*80)
        for idx, text in enumerate(texts):
            if 'B/L NO' in text.upper():
                # 显示前后5行
                start = max(0, idx - 2)
                end = min(len(texts), idx + 6)
                for i in range(start, end):
                    marker = ' ← B/L NO 标签' if i == idx else ''
                    marker += ' ← 应该是B/L号' if i == idx + 2 else ''
                    print(f'  {i:3d}. [{texts[i][:60]:60s}]{marker}')
                break
        print('='*80)
        
    else:
        print('❌ 未识别到文字')
    
else:
    print(f'❌ 测试图片不存在: {test_image}')