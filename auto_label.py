import json
import re
from test_ocr import extract_bill_info  # 复用你的提取逻辑

def auto_label_from_rules(input_json, output_json):
    """使用现有规则自动标注，然后人工校验"""
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for entry in data:
        texts = entry['texts']
        
        # 使用你的提取函数
        extracted = extract_bill_info(texts)
        
        # 转换为标注格式
        entry['labels'] = {
            'shipper_name': extracted['shipper']['name'],
            'shipper_address': extracted['shipper']['address'],
            'consignee_name': extracted['consignee']['name'],
            'consignee_address': extracted['consignee']['address'],
            'bl_no': extracted['bill_info'].get('B/L NO', ''),
            'oti_no': extracted['bill_info'].get('OTI NO', ''),
            'ref_no': extracted['bill_info'].get('REF', ''),
            'ein_no': extracted['bill_info'].get('EIN', ''),
            'tel': extracted['bill_info'].get('TEL', ''),
            'goods_description': extracted['goods_info']
        }
    
    # 保存
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f'✅ 自动标注完成！请检查 {output_json}')
    print(f'💡 建议：使用 label_tool.py 手动校验和修正')

if __name__ == '__main__':
    auto_label_from_rules('bills_raw_data.json', 'bills_labeled_data.json')