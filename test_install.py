print("测试 1: 导入 PaddleOCR...")
try:
    from paddleocr import PaddleOCR
    print("✅ PaddleOCR 导入成功！")
except Exception as e:
    print(f"❌ 失败：{e}")

print("\n测试 2: 导入 PaddlePaddle...")
try:
    import paddle
    print("✅ PaddlePaddle 导入成功！")
    print(f"   版本：{paddle.__version__}")
except Exception as e:
    print(f"❌ 失败：{e}")

print("\n测试 3: 导入其他库...")
try:
    import cv2
    import numpy as np
    from PIL import Image
    print("✅ OpenCV、NumPy、Pillow 都成功！")
except Exception as e:
    print(f"❌ 失败：{e}")

print("\n测试 4: 初始化 OCR 引擎（会下载模型）...")
try:
    # 新版本 API - 移除了 show_log 和 use_angle_cls
    ocr = PaddleOCR(
        use_textline_orientation=True,  # 替代 use_angle_cls
        lang='en'
    )
    print("✅ OCR 引擎初始化成功！")
except Exception as e:
    print(f"❌ 失败：{e}")

print("\n🎉 所有测试通过！可以开始使用了！")