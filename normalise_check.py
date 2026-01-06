import json

# 读取原始文件
with open('check.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 标准化所有文件名
for bill in data['bills_of_lading']:
    if 'file_name' in bill:
        old_name = bill['file_name']
        new_name = old_name.replace(' ', '_')
        bill['file_name'] = new_name
        print(f'✅ {old_name} -> {new_name}')

# 保存
with open('check_normalized.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('✅ 已保存到 check_normalized.json')