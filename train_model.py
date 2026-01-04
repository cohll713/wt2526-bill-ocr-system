import json
import re  # ← 添加这一行
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

def prepare_training_features(labeled_data):
    """准备训练特征"""
    X = []  # 特征
    y = []  # 标签（字段类型）
    
    for entry in labeled_data:
        texts = entry['texts']
        labels = entry['labels']
        
        for idx, text in enumerate(texts):
            # 特征工程
            features = {
                'text': text,
                'text_lower': text.lower(),
                'text_upper': text.upper(),
                'position': idx / len(texts),  # 相对位置
                'length': len(text),
                'has_number': bool(re.search(r'\d', text)),
                'has_colon': ':' in text,
                'has_comma': ',' in text,
                'is_upper': text.isupper(),
                'prev_text': texts[idx-1] if idx > 0 else '',
                'next_text': texts[idx+1] if idx < len(texts)-1 else ''
            }
            
            # 确定标签（这行文本属于哪个字段）
            label_type = 'other'
            
            if text == labels.get('shipper_name', ''):
                label_type = 'shipper_name'
            elif text in labels.get('shipper_address', []):
                label_type = 'shipper_address'
            elif text == labels.get('consignee_name', ''):
                label_type = 'consignee_name'
            elif text in labels.get('consignee_address', []):
                label_type = 'consignee_address'
            elif text == labels.get('bl_no', ''):
                label_type = 'bl_no'
            elif labels.get('oti_no', '') and labels['oti_no'] in text:
                label_type = 'oti_no'
            elif labels.get('ref_no', '') and labels['ref_no'] in text:
                label_type = 'ref_no'
            elif labels.get('ein_no', '') and labels['ein_no'] in text:
                label_type = 'ein_no'
            elif labels.get('tel', '') and labels['tel'] in text:
                label_type = 'tel'
            elif text in labels.get('goods_description', []):
                label_type = 'goods'
            
            X.append(features)
            y.append(label_type)
    
    return X, y

def train_field_classifier(labeled_json):
    """训练字段分类器"""
    with open(labeled_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f'📊 加载了 {len(data)} 个标注样本')
    
    # 准备特征
    X, y = prepare_training_features(data)
    
    print(f'📊 共提取 {len(X)} 行文本数据')
    
    # 统计标签分布
    from collections import Counter
    label_counts = Counter(y)
    print('\n📊 标签分布:')
    for label, count in label_counts.items():
        print(f'  {label}: {count}')
    
    # 文本向量化
    vectorizer = TfidfVectorizer(max_features=100)
    X_text = vectorizer.fit_transform([x['text'] for x in X])
    
    # 其他特征
    X_other = np.array([[
        x['position'],
        x['length'],
        int(x['has_number']),
        int(x['has_colon']),
        int(x['has_comma']),
        int(x['is_upper'])
    ] for x in X])
    
    # 合并特征
    X_combined = np.hstack([X_text.toarray(), X_other])
    
    # 编码标签
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # 分割数据
    X_train, X_test, y_train, y_test = train_test_split(
        X_combined, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    # 训练模型
    print('\n🚀 开始训练...')
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    
    # 评估
    accuracy = clf.score(X_test, y_test)
    print(f'✅ 训练完成！测试准确率: {accuracy:.2%}')
    
    # 特征重要性
    feature_importance = clf.feature_importances_
    print(f'\n📊 前 10 个重要特征:')
    feature_names = list(vectorizer.get_feature_names_out()) + ['position', 'length', 'has_number', 'has_colon', 'has_comma', 'is_upper']
    top_indices = np.argsort(feature_importance)[-10:][::-1]
    for idx in top_indices:
        if idx < len(feature_names):
            print(f'  {feature_names[idx]}: {feature_importance[idx]:.4f}')
    
    # 保存模型
    joblib.dump(clf, 'bill_classifier.pkl')
    joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')
    joblib.dump(le, 'label_encoder.pkl')
    
    print('\n💾 模型已保存到:')
    print('  - bill_classifier.pkl')
    print('  - tfidf_vectorizer.pkl')
    print('  - label_encoder.pkl')

if __name__ == '__main__':
    train_field_classifier('bills_labeled_data.json')