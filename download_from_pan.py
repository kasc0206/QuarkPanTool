"""
从用户自己的夸克网盘下载文件 - 修正版
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quark import QuarkPanFileManager


async def download_folder_contents(qm, pdir_fid, save_base_path, folders_map=None, depth=0):
    """递归下载文件夹中的所有内容"""
    if folders_map is None:
        folders_map = {}
    
    result = await qm.get_sorted_file_list(pdir_fid=pdir_fid, page='1', size='100', fetch_total='true')
    
    if result.get('status') != 200:
        print(f"{'  ' * depth}[错误] 获取文件列表失败: {result.get('message', '未知错误')}")
        return
    
    data = result.get('data', {})
    file_list = data.get('list', [])
    
    if not file_list:
        print(f"{'  ' * depth}  文件夹为空")
        return
    
    # 分离文件和文件夹
    files = [f for f in file_list if not f.get('dir')]
    dirs = [f for f in file_list if f.get('dir')]
    
    print(f"{'  ' * depth}  📄 {len(files)} 个文件, 📁 {len(dirs)} 个子文件夹")
    
    # 记录文件夹映射
    for d in dirs:
        folders_map[d['fid']] = {
            'file_name': d['file_name'],
            'pdir_fid': d['pdir_fid']
        }
    
    # 下载当前目录的文件
    if files:
        fids = [f['fid'] for f in files]
        print(f"{'  ' * depth}  开始下载 {len(files)} 个文件...")
        await qm.quark_file_download(fids, folder=save_base_path, folders_map=folders_map)
    
    # 递归下载子文件夹
    for d in dirs:
        folder_name = d['file_name']
        sub_save_path = os.path.join(save_base_path, folder_name)
        print(f"\n{'  ' * depth}  📁 进入子文件夹: {folder_name}")
        await download_folder_contents(qm, d['fid'], sub_save_path, dict(folders_map), depth + 1)


async def main():
    qm = QuarkPanFileManager(headless=True, slow_mo=0)
    
    print("=" * 60)
    print("夸克网盘文件下载工具 v2")
    print("=" * 60)
    
    # 验证登录
    try:
        nickname = await qm.get_user_info()
        print(f"✅ 登录用户: {nickname}")
    except Exception as e:
        print(f"❌ 获取用户信息失败: {e}")
        print("请先运行 quark.py 登录")
        return
    
    # 获取根目录内容
    print("\n📋 正在获取网盘根目录文件列表...")
    result = await qm.get_sorted_file_list(pdir_fid='0', page='1', size='100', fetch_total='true')
    
    if result.get('status') != 200:
        print(f"❌ 获取文件列表失败: {result.get('message', '未知错误')}")
        return
    
    data = result.get('data', {})
    file_list = data.get('list', [])
    
    if not file_list:
        print("网盘根目录为空")
        return
    
    print(f"\n📂 网盘根目录中共有 {len(file_list)} 项:")
    for i, item in enumerate(file_list, 1):
        is_dir = item.get('dir', False)
        icon = "📁" if is_dir else "📄"
        name = item.get('file_name', '未知')
        size = item.get('size', 0)
        if not is_dir:
            if size >= 1024**3:
                size_str = f"{size/1024**3:.2f} GB"
            elif size >= 1024**2:
                size_str = f"{size/1024**2:.2f} MB"
            elif size >= 1024:
                size_str = f"{size/1024:.2f} KB"
            else:
                size_str = f"{size} B"
        else:
            size_str = "文件夹"
        print(f"  {i}. {icon} {name} ({size_str})")
    
    # 查找刚转存的文件夹
    target_fid = '0'
    target_name = '根目录'
    
    for item in file_list:
        if item.get('dir') and '全国法官培训统编教材' in item.get('file_name', ''):
            target_fid = item['fid']
            target_name = item['file_name']
            break
    
    if target_fid == '0' and len(file_list) == 1 and file_list[0].get('dir'):
        target_fid = file_list[0]['fid']
        target_name = file_list[0]['file_name']
    
    print(f"\n📥 目标文件夹: {target_name}")
    print("自动开始下载...")
    
    save_path = os.path.join('downloads', target_name)
    print(f"💾 保存路径: {os.path.abspath(save_path)}")
    
    # 获取目标文件夹内容
    result = await qm.get_sorted_file_list(pdir_fid=target_fid, page='1', size='100', fetch_total='true')
    
    if result.get('status') != 200:
        print(f"❌ 获取文件列表失败")
        return
    
    data = result.get('data', {})
    file_list = data.get('list', [])
    
    if not file_list:
        print("该文件夹为空")
        return
    
    files = [f for f in file_list if not f.get('dir')]
    dirs = [f for f in file_list if f.get('dir')]
    
    total_size = sum(f.get('size', 0) for f in files)
    total_size_str = ""
    if total_size >= 1024**3:
        total_size_str = f"{total_size/1024**3:.2f} GB"
    elif total_size >= 1024**2:
        total_size_str = f"{total_size/1024**2:.2f} MB"
    else:
        total_size_str = f"{total_size/1024:.2f} KB"
    
    print(f"\n📊 总计: {len(files)} 个文件, {len(dirs)} 个子文件夹, 总大小: {total_size_str}")
    
    # 构建文件夹映射
    folders_map = {}
    for d in dirs:
        folders_map[d['fid']] = {
            'file_name': d['file_name'],
            'pdir_fid': target_fid
        }
    
    print(f"\n{'=' * 60}")
    print(f"⬇️  开始下载...")
    print(f"{'=' * 60}\n")
    
    # 下载当前目录的文件
    if files:
        fids = [f['fid'] for f in files]
        print(f"下载 {len(files)} 个文件到 {save_path} ...")
        await qm.quark_file_download(fids, folder=save_path, folders_map=folders_map)
    
    # 递归下载子文件夹
    for d in dirs:
        folder_name = d['file_name']
        sub_save_path = os.path.join(save_path, folder_name)
        print(f"\n进入子文件夹: {folder_name}")
        await download_folder_contents(qm, d['fid'], sub_save_path, dict(folders_map), 1)
    
    print(f"\n{'=' * 60}")
    print(f"✅ 全部下载完成！")
    print(f"📁 文件保存在: {os.path.abspath(save_path)}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    asyncio.run(main())
