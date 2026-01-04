import os
import json
from paddleocr import PaddleOCR
from tqdm import tqdm

def process_all_bills(image_folder, output_json):
    """批量处理所有提单，生成 OCR 文本"""
    ocr = PaddleOCR(use_textline_orientation=True, lang='en')
    
    training_data = []
    
    # 获取所有 png 文件
    image_files = [f for f in os.listdir(image_folder) if f.endswith('.png')]
    
    print(f'📁 找到 {len(image_files)} 个提单文件')
    
    for img_file in tqdm(image_files, desc='处理中'):
        img_path = os.path.join(image_folder, img_file)
        
        # OCR 识别
        result = ocr.predict(img_path)
        
        if result and len(result) > 0:
            texts = result[0]['rec_texts']
            
            # 保存数据
            training_data.append({
                'file_name': img_file,
                'texts': texts,
                # 预留标注字段
                'labels': {
                    'shipper_name': '',
                    'shipper_address': [],
                    'consignee_name': '',
                    'consignee_address': [],
                    'bl_no': '',
                    'oti_no': '',
                    'ref_no': '',
                    'ein_no': '',
                    'tel': '',
                    'goods_description': []
                }
            })
    
    # 保存为 JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    print(f'\n✅ 已保存到: {output_json}')
    print(f'📊 共处理 {len(training_data)} 个文件')

if __name__ == '__main__':
    process_all_bills('test_images', 'bills_raw_data.json')