import json
import re
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

console = Console()

def load_or_create_labeled_data(json_path):
    """加载或创建标注数据"""
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        console.print(f"[yellow]📄 {json_path} 不存在，将创建新文件[/yellow]")
        return []

def save_labeled_data(data, json_path):
    """保存标注数据"""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"[green]💾 已保存到 {json_path}[/green]")

def show_all_texts(texts, highlight_lines=None):
    """显示所有OCR文本，高亮显示预测行"""
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("行号", style="cyan", width=6, justify="right")
    table.add_column("文本内容", width=80)
    
    if not highlight_lines:
        highlight_lines = []
    
    for idx, text in enumerate(texts, 1):
        # 高亮预测的行
        if idx in [i+1 for i in highlight_lines]:
            table.add_row(
                f"[bold yellow]{idx}[/bold yellow]",
                f"[bold yellow]👉 {text[:80]}[/bold yellow]"
            )
        else:
            table.add_row(str(idx), text[:80])
    
    console.print(table)

def smart_guess_field(texts, field_type):
    """智能猜测字段位置"""
    patterns = {
        'shipper_name': [
            (r'SHIPPER.*EXPORTER', 1),
            (r'SHIPPER', 1),
            (r'EXPORTER', 1),
        ],
        'shipper_address': [
            (r'SHIPPER.*EXPORTER', [2, 3]),
            (r'SHIPPER', [2, 3]),
        ],
        'consignee_name': [
            (r'CONSIGNEE', 1),
            (r'TO THE ORDER', 1),
        ],
        'consignee_address': [
            (r'CONSIGNEE', [2, 3, 4]),
        ],
        'bl_no': [
            (r'B/L\s*NO\.?\s*$', 1),
            (r'BILL OF LADING NO', 1),
            (r'BL\s*NO\.?\s*:', 0),
            (r'B\.L\.\s*NO', 1),
        ],
        'oti_no': [
            (r'OTI\s*NO\.?\s*:', 0),
            (r'OTT\s*NO\.?\s*:', 0),
        ],
        'ref_no': [
            (r'REF\s*#?\s*:', 0),
            (r'REFERENCE', 0),
        ],
        'ein_no': [
            (r'EIN\s*#?\s*:', 0),
        ],
        'tel': [
            (r'TEL\s*:', 0),
            (r'PHONE', 0),
        ],
        'goods_description': [
            (r'DESCRIPTION\s+OF.*GOODS', [1, 2]),
            (r'SAID TO CONTAIN', [1, 2]),
            (r'HS\s*CODE', 0),
        ],
    }
    
    if field_type not in patterns:
        return None
    
    for pattern, offset in patterns[field_type]:
        for idx, text in enumerate(texts):
            if re.search(pattern, text, re.IGNORECASE):
                if isinstance(offset, int):
                    target_idx = idx + offset
                    if 0 <= target_idx < len(texts):
                        return [target_idx]
                else:
                    result = []
                    for off in offset:
                        target_idx = idx + off
                        if 0 <= target_idx < len(texts):
                            result.append(target_idx)
                    if result:
                        return result
    
    return None

def extract_value_from_lines(texts, line_indices, clean_patterns=None):
    """从行号提取值"""
    if not line_indices:
        return None
    
    if len(line_indices) == 1:
        text = texts[line_indices[0]]
        if clean_patterns:
            for pattern in clean_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return text
    else:
        return [texts[i] for i in line_indices]

def parse_line_input(user_input):
    """解析用户输入的行号"""
    line_nums = []
    for part in user_input.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            line_nums.extend(range(start-1, end))
        else:
            line_nums.append(int(part) - 1)
    return line_nums

def label_single_field(texts, field_name, field_config, existing_value=None):
    """标注单个字段"""
    clean_patterns, field_type, display_name = field_config
    
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print(f"[bold cyan]{display_name}[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")
    
    # 如果有现有值，显示它
    if existing_value is not None:
        console.print(f"[bold green]📌 现有标注：[/bold green]")
        if isinstance(existing_value, list):
            for line in existing_value:
                console.print(f"  [green]{line}[/green]")
        else:
            console.print(f"  [green]{existing_value}[/green]")
        
        # 询问是否保留
        if Confirm.ask("\n[green]保留这个标注？[/green]", default=True):
            return existing_value
        else:
            console.print("[yellow]将重新标注...[/yellow]\n")
    
    # 智能猜测
    predicted_lines = smart_guess_field(texts, field_name)
    
    # 显示所有文本，高亮预测行
    show_all_texts(texts, predicted_lines)
    
    if predicted_lines:
        # 显示预测内容
        console.print(f"\n[bold green]🤖 AI预测：[/bold green]")
        for idx in predicted_lines:
            console.print(f"  [yellow]第 {idx+1} 行:[/yellow] {texts[idx]}")
        
        # 询问确认
        confirmed = Confirm.ask("\n[green]✓[/green] 预测正确吗？", default=True)
        
        if confirmed:
            return extract_value_from_lines(texts, predicted_lines, clean_patterns)
    else:
        console.print(f"\n[yellow]⚠️  未能自动识别[/yellow]")
    
    # 手动输入
    console.print("\n[yellow]请输入正确的行号：[/yellow]")
    console.print("[dim]  提示: 单行直接输入数字，如 4[/dim]")
    console.print("[dim]       多行用逗号分隔，如 4,5,6[/dim]")
    console.print("[dim]       范围用连字符，如 4-6[/dim]")
    console.print("[dim]       不存在则直接按 Enter[/dim]")
    
    user_input = Prompt.ask("\n  行号", default="")
    if user_input.strip():
        try:
            line_nums = parse_line_input(user_input)
            return extract_value_from_lines(texts, line_nums, clean_patterns)
        except ValueError as e:
            console.print(f"  [red]❌ 输入错误: {e}[/red]")
            return None
    
    return None

def show_labels_summary(labels, field_configs):
    """显示标注结果摘要"""
    console.print("\n" + "="*70)
    console.print("[bold green]📋 标注结果预览[/bold green]")
    console.print("="*70 + "\n")
    
    result_table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    result_table.add_column("编号", style="cyan", width=6, justify="center")
    result_table.add_column("字段", style="cyan", width=20)
    result_table.add_column("内容", width=60)
    
    field_list = list(field_configs.keys())
    
    for i, field_name in enumerate(field_list, 1):
        value = labels.get(field_name)
        display_name = field_configs[field_name][2]
        
        if value:
            if isinstance(value, list):
                result_table.add_row(str(i), display_name, "\n".join(value))
            else:
                result_table.add_row(str(i), display_name, str(value))
        else:
            result_table.add_row(str(i), display_name, "[dim]未填写[/dim]")
    
    console.print(result_table)
    return field_list

def edit_labels(labels, texts, field_configs):
    """编辑已标注的字段"""
    while True:
        # 显示摘要
        field_list = show_labels_summary(labels, field_configs)
        
        # 询问是否修改
        console.print("\n[yellow]需要修改吗？[/yellow]")
        console.print("[dim]  输入字段编号修改（如 1, 5, 8）[/dim]")
        console.print("[dim]  直接按 Enter 确认无误[/dim]")
        
        user_input = Prompt.ask("\n  修改字段编号", default="")
        
        if not user_input.strip():
            # 确认无误
            break
        
        # 解析编号
        try:
            edit_nums = [int(x.strip()) for x in user_input.split(',')]
            
            for num in edit_nums:
                if 1 <= num <= len(field_list):
                    field_name = field_list[num - 1]
                    field_config = field_configs[field_name]
                    
                    console.clear()
                    console.print(f"\n[bold magenta]修改字段: {field_config[2]}[/bold magenta]\n")
                    
                    # 重新标注这个字段（不使用现有值）
                    new_value = label_single_field(texts, field_name, field_config, existing_value=None)
                    
                    if new_value:
                        labels[field_name] = new_value
                    elif field_name in labels:
                        # 用户想删除这个字段
                        if Confirm.ask(f"\n删除 {field_config[2]} 吗？", default=False):
                            del labels[field_name]
                else:
                    console.print(f"[red]❌ 无效的编号: {num}[/red]")
        except ValueError:
            console.print(f"[red]❌ 输入格式错误[/red]")

def smart_label_bill(data_entry, field_configs):
    """智能标注单个提单"""
    console.clear()
    console.print(Panel(
        f"[bold blue]{data_entry['file_name']}[/bold blue]",
        title="🤖 智能标注",
        border_style="blue"
    ))
    
    texts = data_entry['texts']
    existing_labels = data_entry.get('labels', {})
    labels = {}
    
    # 第一遍：逐个标注（如果有现有值，先让用户确认）
    for field_name, field_config in field_configs.items():
        existing_value = existing_labels.get(field_name)
        value = label_single_field(texts, field_name, field_config, existing_value)
        if value:
            labels[field_name] = value
    
    # 第二遍：预览 + 修改
    console.clear()
    edit_labels(labels, texts, field_configs)
    
    # 最终确认
    console.clear()
    console.print(Panel(
        f"[bold green]✅ {data_entry['file_name']} 标注完成！[/bold green]",
        border_style="green"
    ))
    show_labels_summary(labels, field_configs)
    
    return labels

def smart_label_all(output_json):
    """批量智能标注"""
    # 加载或创建数据
    data = load_or_create_labeled_data(output_json)
    
    # 字段配置
    field_configs = {
        'shipper_name': ([], 'single', '📦 发货人名称'),
        'shipper_address': ([], 'multi', '📦 发货人地址'),
        'consignee_name': ([], 'single', '📬 收货人名称'),
        'consignee_address': ([], 'multi', '📬 收货人地址'),
        'bl_no': ([r'B/L\s*NO\.?:?', r'BILL OF LADING NO\.?:?'], 'single', '📋 B/L NO'),
        'oti_no': ([r'OTI\s*NO\.?:?', r'OTT\s*NO\.?:?'], 'single', '📋 OTI/OTT NO'),
        'ref_no': ([r'REF\s*#?:?', r'REFERENCE:?'], 'single', '📋 REF#'),
        'ein_no': ([r'EIN\s*#?:?'], 'single', '📋 EIN#'),
        'tel': ([r'TEL:?', r'PHONE:?'], 'single', '📞 TEL'),
        'goods_description': ([], 'multi', '📊 货物描述'),
    }
    
    console.print(Panel(
        f"[bold]共有 {len(data)} 个提单待处理[/bold]",
        title="🤖 智能标注系统",
        border_style="green"
    ))
    
    labeled_count = 0
    
    for i, entry in enumerate(data, 1):
        console.print(f"\n[bold magenta]{'#'*70}[/bold magenta]")
        console.print(f"[bold magenta]进度: {i}/{len(data)} - {entry['file_name']}[/bold magenta]")
        
        # 检查是否已标注
        if entry.get('labels'):
            console.print(f"[yellow]⚠️  此文件已有标注[/yellow]")
        
        console.print(f"[bold magenta]{'#'*70}[/bold magenta]\n")
        
        # 询问是否要标注这个文件
        if not Confirm.ask(f"[cyan]标注这个文件？[/cyan]", default=True):
            console.print("[dim]跳过...[/dim]")
            continue
        
        try:
            entry['labels'] = smart_label_bill(entry, field_configs)
            labeled_count += 1
            
            # 立即保存
            save_labeled_data(data, output_json)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  用户中断，已保存当前进度[/yellow]")
            save_labeled_data(data, output_json)
            break
        except Exception as e:
            console.print(f"[red]❌ 错误: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            continue
        
        # 询问是否继续
        if i < len(data):
            if not Confirm.ask("\n[cyan]继续下一个文件？[/cyan]", default=True):
                console.print("[yellow]已保存，退出标注[/yellow]")
                break
    
    console.print("\n" + "="*70)
    console.print(Panel(
        f"[bold green]✅ 完成！本次标注 {labeled_count} 个文件[/bold green]\n"
        f"[dim]总计: {sum(1 for e in data if e.get('labels'))} / {len(data)} 已标注[/dim]",
        title="完成",
        border_style="green"
    ))

if __name__ == '__main__':
    smart_label_all('bills_labeled_data.json')