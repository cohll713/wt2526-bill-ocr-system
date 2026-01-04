import cv2
import numpy as np
from PIL import Image

def preprocess_image(image_path, output_path=None):
    """
    图像预处理：去噪、增强对比度、二值化
    
    参数:
        image_path: 输入图片路径
        output_path: 输出路径（可选，用于查看效果）
    
    返回:
        processed_image: 处理后的图片路径
    """
    # 读取图片
    img = cv2.imread(image_path)
    
    # 1. 转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 去噪（高斯模糊）
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 3. 增强对比度（CLAHE）
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # 4. 二值化（自适应阈值）
    binary = cv2.adaptiveThreshold(
        enhanced, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        11, 2
    )
    
    # 保存处理后的图片
    if output_path is None:
        output_path = image_path.replace('.png', '_processed.png')
    
    cv2.imwrite(output_path, binary)
    print(f"预处理完成，保存到: {output_path}")
    
    return output_path

# 测试预处理效果
if __name__ == "__main__":
    original = "test_images/acs-No. OH23040018.png"
    processed = preprocess_image(original)
    
    # 对比原图和处理后的图
    print("请打开以下两个文件对比效果：")
    print(f"原图: {original}")
    print(f"处理后: {processed}")