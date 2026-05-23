"""
等待夸克网盘下载完成后，将文件转移到 iCloud Drive
"""
import os
import shutil
import subprocess
import sys
import time

DOWNLOAD_DIR = "/Users/kylin/test/夸克网盘下载/downloads"
ICLOUD_DIR = "/Users/kylin/Library/Mobile Documents/com~apple~CloudDocs/法律相关/全国法官培训统编教材（2025）"


def get_download_pids():
    """获取下载进程的 PID"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "download_from_pan.py"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            return result.stdout.strip().split("\n")
    except:
        pass
    return []


def is_file_complete(filepath):
    """
    检查 PDF 文件是否下载完整。
    多线程下载用 truncate 预分配空间，所以不能靠文件大小判断。
    通过检查文件末尾是否有有效数据来判断。
    """
    try:
        # 对于多线程分片下载的文件，预分配了完整大小，如果最后一片没写完，
        # 文件末尾是 \0 填充。读取最后 100KB 检查是否全是空字节
        size = os.path.getsize(filepath)
        if size < 1024:
            return False
        
        with open(filepath, "rb") as f:
            f.seek(max(0, size - 102400))  # 读取最后 100KB
            tail = f.read()
            # 检查是否有非零数据
            non_zero = sum(1 for b in tail if b != 0)
            if non_zero < 100:  # 如果最后 100KB 几乎全是 0，说明没写完
                return False
        
        # 额外检查：尝试读取 PDF 文件头
        with open(filepath, "rb") as f:
            header = f.read(5)
            if header == b"%PDF-":  # PDF 文件
                return True
            return True  # 非 PDF 文件只做末尾检查
    except:
        return False


def main():
    print("=" * 60)
    print("🔄 夸克下载监控 & iCloud 自动转移")
    print("=" * 60)
    print(f"📁 下载目录: {DOWNLOAD_DIR}")
    print(f"☁️  iCloud 目标: {ICLOUD_DIR}")
    print()
    
    os.makedirs(ICLOUD_DIR, exist_ok=True)
    
    print("⏳ 等待下载进程结束...")
    print("（每 60 秒检查一次，按 Ctrl+C 停止）\n")
    
    try:
        while True:
            pids = get_download_pids()
            if not pids:
                print("✅ 下载进程已结束")
                break
            time.sleep(60)
        
        # 等几秒确保文件写入完成
        print("等待文件写入完成...")
        time.sleep(5)
        
        # 开始转移
        print("\n📤 正在转移到 iCloud...")
        moved = 0
        skipped = 0
        
        for f in sorted(os.listdir(DOWNLOAD_DIR)):
            if f.endswith(".pdf"):
                src = os.path.join(DOWNLOAD_DIR, f)
                dst = os.path.join(ICLOUD_DIR, f)
                
                if os.path.exists(dst):
                    print(f"  ⏭️  已存在，跳过: {f}")
                    skipped += 1
                    continue
                
                if not is_file_complete(src):
                    print(f"  ⚠️  文件可能不完整，跳过: {f}")
                    skipped += 1
                    continue
                
                file_size = os.path.getsize(src) / 1024 / 1024
                print(f"  📄 复制: {f} ({file_size:.1f} MB)...", end=" ", flush=True)
                shutil.copy2(src, dst)
                
                if os.path.exists(dst):
                    print("✅")
                    os.remove(src)  # 删除源文件
                    moved += 1
                else:
                    print("❌ 失败")
        
        print(f"\n{'=' * 60}")
        print(f"🏁 完成！")
        print(f"  ✅ 已转移: {moved} 个文件")
        print(f"  ⏭️  跳过: {skipped} 个文件")
        print(f"☁️  位置: {ICLOUD_DIR}")
        print(f"{'=' * 60}")
    
    except KeyboardInterrupt:
        print("\n\n监控已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
