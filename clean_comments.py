import tokenize
import io
import os
from pathlib import Path

def remove_comments_and_docstrings(source):
    """
    使用 tokenize 移除代码中的注释。
    """
    result = []
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0
    
    try:
        f = io.BytesIO(source.encode('utf-8'))
        for tok in tokenize.tokenize(f.readline):
            token_type = tok.type
            token_string = tok.string
            start_line, start_col = tok.start
            
            # 1. 过滤注释
            if token_type == tokenize.COMMENT:
                continue
                
            # 2. 过滤 Docstrings (类、函数开头的字符串)
            elif token_type == tokenize.STRING:
                if prev_toktype in (tokenize.INDENT, tokenize.NEWLINE, tokenize.NL):
                    continue

            # 还原代码间距
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                result.append(" " * (start_col - last_col))
                
            result.append(token_string)
            last_lineno, last_col = tok.end
            prev_toktype = token_type
            
        return "".join(result)
    except Exception:
        # 如果某些文件编码复杂导致解析失败，返回原内容
        return source

def batch_process(directory):
    """
    遍历文件夹并处理所有 .py 文件
    """
    path_obj = Path(directory)
    
    if not path_obj.exists():
        print(f"错误: 路径 {directory} 不存在")
        return

    # rglob 会递归搜索所有子文件夹
    for file_path in path_obj.rglob('*.py'):
        print(f"正在处理: {file_path}")
        
        try:
            # 读取内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 清理代码
            clean_code = remove_comments_and_docstrings(content)
            
            # 写回原文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clean_code)
                
        except Exception as e:
            print(f"无法处理文件 {file_path}: {e}")

if __name__ == "__main__":
    # 你的目标路径
    target_dir = r"D:\shv-code\scripts"
    
    # 执行前请确保已备份重要数据！
    confirm = input(f"确定要清理 {target_dir} 下所有 Python 文件的注释吗？(y/n): ")
    if confirm.lower() == 'y':
        batch_process(target_dir)
        print("\n所有操作已完成。")
    else:
        print("操作已取消。")