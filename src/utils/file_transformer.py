import os
import shutil
import win32com.client
from tqdm import tqdm

def convert_doc_to_docx(doc_path, docx_path):
    """将 .doc 文件转换为 .docx 文件"""
    try:
        # 创建 Word 应用程序对象
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False  # 不显示 Word 窗口
        
        # 检查文件是否存在
        if not os.path.exists(doc_path):
            print(f"\n错误: 文件 {doc_path} 不存在")
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
        print(f"\n转换失败: {doc_path} - 错误: {str(e)}")
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

def process_files(source_dir, target_dir, error_dir):
    """递归遍历文件夹并处理 docx 和 doc 文件"""
    # 确保目标目录和错误目录存在
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(error_dir, exist_ok=True)

    # 首先统计总文件数
    total_files = 0
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(('.doc', '.docx')):
                total_files += 1

    if total_files == 0:
        print("没有找到任何.doc或.docx文件")
        return

    # 初始化进度条
    progress_bar = tqdm(total=total_files, desc="处理进度", unit="file")

    # 遍历源目录
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            # 获取文件完整路径
            source_path = os.path.join(root, file)
            
            # 只处理.doc和.docx文件
            if not file.lower().endswith(('.doc', '.docx')):
                continue
            
            # 检查文件扩展名
            if file.lower().endswith('.docx'):
                # 直接复制 docx 文件
                target_path = os.path.join(target_dir, file)
                try:
                    shutil.copy2(source_path, target_path)
                    progress_bar.set_postfix_str(f"已复制: {file[:20]}...")
                except Exception as e:
                    progress_bar.write(f"\n复制失败: {file} - 错误: {str(e)}")
                    # 复制失败时移动到错误目录
                    error_path = os.path.join(error_dir, file)
                    shutil.move(source_path, error_path)
                    progress_bar.write(f"已将失败文件移动到: {error_path}")
                
            elif file.lower().endswith('.doc'):
                # 转换 doc 文件为 docx
                filename = os.path.splitext(file)[0]
                target_docx = os.path.join(target_dir, f"{filename}.docx")
                
                success = convert_doc_to_docx(source_path, target_docx)
                if success:
                    progress_bar.set_postfix_str(f"已转换: {file[:20]}...")
                else:
                    # 如果转换失败，移动到错误目录
                    error_path = os.path.join(error_dir, file)
                    shutil.move(source_path, error_path)
                    progress_bar.write(f"\n转换失败，已将文件移动到错误目录: {error_path}")
            
            # 更新进度条
            progress_bar.update(1)

    # 关闭进度条
    progress_bar.close()

def main():
    # 设置源目录和目标目录
    source_directory = r"C:\Lee\work\contract\all\error"  # 修改为你的源目录路径
    target_directory = r"C:\Lee\work\contract\all\trans"  # 修改为你的目标目录路径
    error_directory = r"C:\Lee\work\contract\all\error1"  # 转换失败文件存放目录
    
    print("开始处理文件...")
    process_files(source_directory, target_directory, error_directory)
    print("\n处理完成！")

if __name__ == "__main__":
    main()