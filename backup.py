# def extract_bill_info(texts):
#     """从识别的文字中提取关键信息"""
    
#     info = {
#         'shipper': {'name': '', 'address': []},
#         'consignee': {'name': '', 'address': []},
#         'bill_info': {},
#         'cargo': []
#     }
    
#     # 标志变量
#     in_shipper_section = False
#     in_consignee_section = False
#     shipper_lines = []
#     consignee_lines = []
    
#     for i, text in enumerate(texts):
#         if not text or not isinstance(text, str):  # ✅ 添加安全检查
#             continue
            
#         text_upper = text.upper().strip()
        
#         # ===== 识别发货人区域 =====
#         if 'SHIPPER' in text_upper and 'EXPORTER' in text_upper:
#             in_shipper_section = True
#             in_consignee_section = False
#             shipper_lines = []
#             continue
        
#         # ===== 识别收货人区域 =====
#         if 'CONSIGNEE' in text_upper:
#             in_consignee_section = True
#             in_shipper_section = False
#             consignee_lines = []
#             continue
        
#         # ===== 收集发货人信息 =====
#         if in_shipper_section:
#             if any(keyword in text_upper for keyword in ['B/L NO', 'CONSIGNEE', 'NOTIFY', 'VESSEL', 'PORT OF']):
#                 in_shipper_section = False
#             else:
#                 if not any(skip in text_upper for skip in ['S/O NO', 'OTT NO', 'REF#', 'EIN#', 'TEL:', 'FAX:']):
#                     shipper_lines.append(text.strip())
        
#         # ===== 收集收货人信息 =====
#         if in_consignee_section:
#             if any(keyword in text_upper for keyword in ['NOTIFY', 'VESSEL', 'PORT OF', 'CONTAINER']):
#                 in_consignee_section = False
#             else:
#                 if not any(skip in text_upper for skip in ['NOT NEGOTIABLE', 'UNLESS']):
#                     consignee_lines.append(text.strip())
        
#         # ===== 提取提单信息字段 =====
        
#         # B/L NO
#         if 'B/L NO' in text_upper:
#             if i + 1 < len(texts) and texts[i + 1]:  # ✅ 添加安全检查
#                 next_text = texts[i + 1].strip()
#                 if re.match(r'^[A-Z]{2}[-\s]?\d+', next_text, re.IGNORECASE):
#                     info['bill_info']['B/L NO'] = next_text
#             elif ':' in text:
#                 parts = text.split(':', 1)
#                 if len(parts) > 1 and parts[1].strip():  # ✅ 添加安全检查
#                     info['bill_info']['B/L NO'] = parts[1].strip()
        
#         # 直接识别提单号
#         if re.match(r'^OH[-\s]?\d+', text, re.IGNORECASE):
#             info['bill_info']['B/L NO'] = text.strip()
        
#         # 船名
#         if 'VESSEL' in text_upper and 'VOY' not in text_upper:
#             if ':' in text:
#                 parts = text.split(':', 1)
#                 if len(parts) > 1 and parts[1].strip():  # ✅ 添加安全检查
#                     info['bill_info']['VESSEL'] = parts[1].strip()
        
#         # 航次
#         if 'VOYAGE' in text_upper or 'VOY' in text_upper:
#             match = re.search(r'VOY[A-Z]*[:\s]+([A-Z0-9]+)', text_upper)
#             if match:
#                 info['bill_info']['VOYAGE'] = match.group(1)
        
#         # 装货港
#         if 'PORT OF LOADING' in text_upper:
#             if i + 1 < len(texts) and texts[i + 1]:  # ✅ 添加安全检查
#                 info['bill_info']['PORT OF LOADING'] = texts[i + 1].strip()
        
#         # 卸货港
#         if 'PORT OF DISCHARGE' in text_upper:
#             if i + 1 < len(texts) and texts[i + 1]:  # ✅ 添加安全检查
#                 info['bill_info']['PORT OF DISCHARGE'] = texts[i + 1].strip()
        
#         # 货物描述
#         if any(keyword in text_upper for keyword in ['PALLETS', 'CASES', 'KGS', 'HS CODE']) or re.search(r'\d{6}', text):
#             if text.strip() and text not in info['cargo']:  # ✅ 添加安全检查
#                 info['cargo'].append(text.strip())
    
#     # 处理发货人和收货人信息
#     if shipper_lines:
#         info['shipper']['name'] = shipper_lines[0] if shipper_lines else ''
#         info['shipper']['address'] = shipper_lines[1:] if len(shipper_lines) > 1 else []
    
#     if consignee_lines:
#         info['consignee']['name'] = consignee_lines[0] if consignee_lines else ''
#         info['consignee']['address'] = consignee_lines[1:] if len(consignee_lines) > 1 else []
    
#     return info