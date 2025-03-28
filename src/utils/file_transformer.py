import os
import shutil
import win32com.client
import time

def convert_doc_to_docx(doc_path, docx_path):
    """将 .doc 文件转换为 .docx 文件"""
    try:
        # 创建 Word 应用程序对象
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False  # 不显示 Word 窗口
        
        # 检查文件是否存在
        if not os.path.exists(doc_path):
            print(f"错误: 文件 {doc_path} 不存在")
            return False
        
        # 打开 .doc 文件
        doc = word.Documents.Open(doc_path)
        
        # 保存为 .docx 格式（文件格式代码 16 表示 docx）
        doc.SaveAs(docx_path, FileFormat=16)
        
        # 关闭文档和应用程序
        doc.Close()
        word.Quit()
        return True
    
    except Exception as e:
        print(f"转换失败: {doc_path} - 错误: {str(e)}")
        return False
    finally:
        # 确保 Word 进程被清理
        try:
            if 'doc' in locals():
                doc.Close()
            if 'word' in locals():
                word.Quit()
        except:
            pass

def process_files(source_dir, target_dir):
    """递归遍历文件夹并处理 docx 和 doc 文件"""
    # 确保目标目录存在
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # 遍历源目录
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            # 获取文件完整路径
            source_path = os.path.join(root, file)
            
            # 检查文件扩展名
            if file.lower().endswith('.docx'):
                # 直接复制 docx 文件
                target_path = os.path.join(target_dir, file)
                shutil.copy2(source_path, target_path)
                print(f"已复制: {file}")
                
            elif file.lower().endswith('.doc'):
                # 转换 doc 文件为 docx
                filename = os.path.splitext(file)[0]
                target_docx = os.path.join(target_dir, f"{filename}.docx")
                
                success = convert_doc_to_docx(source_path, target_docx)
                if success:
                    print(f"已转换并复制: {file} -> {filename}.docx")
                else:
                    # 如果转换失败，复制原始 doc 文件
                    shutil.copy2(source_path, target_dir)
                    print(f"转换失败，已复制原始文件: {file}")

def main():
    # 设置源目录和目标目录
    source_directory = r"C:\Lee\files\采购\raw"  # 修改为你的源目录路径
    target_directory = r"C:\Lee\files\采购\trans"  # 修改为你的目标目录路径
    
    print("开始处理文件...")
    process_files(source_directory, target_directory)
    print("处理完成！")

if __name__ == "__main__":
    main()