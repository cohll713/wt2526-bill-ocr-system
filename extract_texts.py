import os
import json
import pytesseract
from PIL import Image
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

console = Console()

def load_existing_ocr(json_path):
    """加载已有的 OCR 数据"""
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_processed_files(existing_data):
    """获取已处理的文件名列表"""
    return set(entry['file_name'] for entry in existing_data)

def extract_text_from_image(image_path):
    """从图片提取文本"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='eng')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines
    except Exception as e:
        console.print(f"[red]❌ 提取失败 {image_path}: {e}[/red]")
        return []

def extract_all_texts(image_dir, output_json, incremental=True):
    """
    提取所有图片的 OCR 文本
    
    Args:
        image_dir: 图片文件夹路径
        output_json: 输出 JSON 文件路径
        incremental: 是否增量更新（只处理新图片）
    """
    image_dir = Path(image_dir)
    
    # 加载已有数据
    existing_data = load_existing_ocr(output_json) if incremental else []
    processed_files = get_processed_files(existing_data)
    
    # 获取所有图片文件
    image_files = list(image_dir.glob('*.png')) + \
                  list(image_dir.glob('*.jpg')) + \
                  list(image_dir.glob('*.jpeg'))
    
    # 过滤出未处理的图片
    if incremental:
        new_files = [f for f in image_files if f.name not in processed_files]
        console.print(f"\n[cyan]📊 统计信息：[/cyan]")
        console.print(f"  总图片数: {len(image_files)}")
        console.print(f"  已处理: {len(processed_files)}")
        console.print(f"  待处理: {len(new_files)}")
    else:
        new_files = image_files
        console.print(f"\n[cyan]📊 总共 {len(new_files)} 个图片待处理[/cyan]")
    
    if not new_files:
        console.print("\n[green]✅ 所有图片都已处理！[/green]")
        return
    
    # 处理新图片
    new_data = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task(
            "[cyan]🔍 提取 OCR 文本...",
            total=len(new_files)
        )
        
        for image_file in new_files:
            progress.update(task, description=f"[cyan]处理: {image_file.name}")
            
            texts = extract_text_from_image(image_file)
            
            new_data.append({
                'file_name': image_file.name,
                'texts': texts
            })
            
            progress.advance(task)
    
    # 合并数据
    all_data = existing_data + new_data
    
    # 保存
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[green]✅ 成功！[/green]")
    console.print(f"  新增: {len(new_data)} 个")
    console.print(f"  总计: {len(all_data)} 个")
    console.print(f"  保存到: {output_json}")

if __name__ == '__main__':
    # 增量模式（默认）
    extract_all_texts('test_image', 'bills_ocr_texts.json', incremental=True)
    
    # 如果需要全部重新处理，使用：
    # extract_all_texts('test_image', 'bills_ocr_texts.json', incremental=False)