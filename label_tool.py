import json
import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

def show_text_lines(texts, scores):
    """显示 OCR 识别的文本"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("行号", style="dim", width=6)
    table.add_column("文本内容", width=60)
    table.add_column("置信度", justify="right", width=10)
    
    # 修复：确保 scores 是列表
    if not isinstance(scores, list):
        scores = [0.95] * len(texts)  # 默认置信度
    
    for idx, text in enumerate(texts, 1):
        score = scores[idx-1] if idx-1 < len(scores) else 0.95
        table.add_row(str(idx), text[:60], f"{score:.1%}")
    
    console.print(table)

def label_single_bill(data_entry):
    """标注单个提单"""
    console.clear()
    console.print(f"\n[bold blue]正在标注: {data_entry['file_name']}[/bold blue]\n")
    
    # 显示所有文本
    texts = data_entry['texts']
    scores = data_entry.get('scores', [0.95] * len(texts))
    show_text_lines(texts, scores)
    
    labels = data_entry['labels']
    
    # 交互式标注
    console.print("\n[yellow]请根据上面的行号，输入对应字段的行号（多行用逗号分隔，如: 4,5,6）[/yellow]\n")
    console.print("[dim]提示：如果某个字段不存在，直接按 Enter 跳过[/dim]\n")
    
    try:
        # 发货人名称（单行）
        line = Prompt.ask("📦 发货人名称 (shipper_name) 在第几行", default="")
        if line.strip():
            idx = int(line.strip()) - 1
            labels['shipper_name'] = texts[idx]
        
        # 发货人地址（多行）
        lines = Prompt.ask("📦 发货人地址 (shipper_address) 在第几行", default="")
        if lines.strip():
            labels['shipper_address'] = [texts[int(l.strip())-1] for l in lines.split(',') if l.strip()]
        
        # 收货人名称
        line = Prompt.ask("📬 收货人名称 (consignee_name) 在第几行", default="")
        if line.strip():
            idx = int(line.strip()) - 1
            labels['consignee_name'] = texts[idx]
        
        # 收货人地址
        lines = Prompt.ask("📬 收货人地址 (consignee_address) 在第几行", default="")
        if lines.strip():
            labels['consignee_address'] = [texts[int(l.strip())-1] for l in lines.split(',') if l.strip()]
        
        # B/L NO
        line = Prompt.ask("📋 B/L NO 在第几行", default="")
        if line.strip():
            idx = int(line.strip()) - 1
            labels['bl_no'] = texts[idx]
        
        # OTI NO
        line = Prompt.ask("📋 OTI NO 在第几行", default="")
        if line.strip():
            text = texts[int(line.strip())-1]
            labels['oti_no'] = text.replace('OTT NO.', '').replace('OTI NO.', '').strip()
        
        # REF NO
        line = Prompt.ask("📋 REF# 在第几行", default="")
        if line.strip():
            text = texts[int(line.strip())-1]
            labels['ref_no'] = text.replace('REF#:', '').strip()
        
        # EIN NO
        line = Prompt.ask("📋 EIN# 在第几行", default="")
        if line.strip():
            text = texts[int(line.strip())-1]
            labels['ein_no'] = text.replace('EIN#:', '').strip()
        
        # TEL
        line = Prompt.ask("📋 TEL 在第几行", default="")
        if line.strip():
            text = texts[int(line.strip())-1]
            labels['tel'] = text.replace('TEL:', '').strip()
        
        # 货物描述
        lines = Prompt.ask("📊 货物描述 (goods) 在第几行", default="")
        if lines.strip():
            labels['goods_description'] = [texts[int(l.strip())-1] for l in lines.split(',') if l.strip()]
        
    except (ValueError, IndexError) as e:
        console.print(f"[red]输入错误: {e}[/red]")
        return labels
    
    # 显示标注结果
    console.print("\n[green]✅ 标注完成！[/green]")
    console.print(json.dumps(labels, indent=2, ensure_ascii=False))
    
    return labels

def label_all_bills(input_json, output_json):
    """批量标注所有提单"""
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    console.print(f"[bold]共有 {len(data)} 个提单需要标注[/bold]\n")
    
    for i, entry in enumerate(data, 1):
        console.print(f"[cyan]进度: {i}/{len(data)}[/cyan]")
        
        # 如果已经标注过，询问是否跳过
        if entry['labels'].get('bl_no'):
            if not Confirm.ask(f"该文件已标注，是否重新标注？", default=False):
                continue
        
        try:
            entry['labels'] = label_single_bill(entry)
        except KeyboardInterrupt:
            console.print("\n[yellow]用户中断，正在保存...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]跳过此文件: {e}[/red]")
            continue
        
        # 每标注一个就保存一次
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if i < len(data):
            if not Confirm.ask("\n继续下一个？", default=True):
                break
    
    console.print(f"\n[green]✅ 标注完成！已保存到 {output_json}[/green]")

if __name__ == '__main__':
    label_all_bills('bills_labeled_data.json', 'bills_labeled_data.json')