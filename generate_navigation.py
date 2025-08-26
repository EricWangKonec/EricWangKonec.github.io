#!/usr/bin/env python3
"""
生成导航页面，用于导航到所有报告
"""

import os
import glob
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv

# 加载环境变量（从release-note-generator目录）
env_path = os.path.join(os.path.dirname(__file__), '../release-note-generator/.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NASReleaseSync:
    """
    从NAS同步Release Notes到本地
    """
    def __init__(self):
        self.nas_token = os.getenv('NAS_TOKEN')
        self.nas_base_url = os.getenv('NAS_BASE_URL')
        
        if not self.nas_token or not self.nas_base_url:
            logger.warning("缺少NAS配置，跳过NAS同步功能")
            self.enabled = False
        else:
            self.nas_base_url = self.nas_base_url.rstrip('/')
            self.nas_release_path = '/Local/Material/Release Notes'
            self.local_release_dir = 'releases'
            self.enabled = True
    
    def list_nas_files(self):
        """获取NAS上的Release Notes文件列表"""
        if not self.enabled:
            return []
        
        try:
            headers = {
                'Authorization': self.nas_token,
                'Content-Type': 'application/json'
            }
            
            data = {
                'path': self.nas_release_path,
                'password': '',
                'page': 1,
                'per_page': 1000,
                'refresh': False
            }
            
            list_url = f"{self.nas_base_url}/api/fs/list"
            response = requests.post(list_url, headers=headers, json=data)
            
            if response.status_code != 200:
                logger.error(f"获取NAS文件列表失败: {response.status_code}")
                return []
            
            result = response.json()
            if result.get('code') != 200:
                logger.error(f"获取NAS文件列表失败: {result.get('message', '未知错误')}")
                return []
            
            files = result.get('data', {}).get('content', [])
            # 只获取HTML文件
            html_files = [f for f in files if f.get('name', '').endswith('.html')]
            logger.info(f"NAS上找到 {len(html_files)} 个Release HTML文件")
            return html_files
            
        except Exception as e:
            logger.error(f"获取NAS文件列表失败: {str(e)}")
            return []
    
    def get_local_versions(self):
        """获取本地已有的版本号"""
        if not os.path.exists(self.local_release_dir):
            os.makedirs(self.local_release_dir)
            return set()
        
        local_versions = set()
        for file_path in glob.glob(f"{self.local_release_dir}/*/index.html"):
            parts = file_path.split('/')
            if len(parts) >= 3:
                version = parts[-2]  # 获取版本号目录名
                local_versions.add(version)
        
        logger.info(f"本地已有 {len(local_versions)} 个版本")
        return local_versions
    
    def extract_version_from_filename(self, filename):
        """从文件名提取版本号"""
        # 假设文件名格式为 v1.0.16.214_release_report.html
        if filename.startswith('v') and '_release_report.html' in filename:
            version = filename.replace('_release_report.html', '')[1:]  # 去掉v前缀
            return version
        return None
    
    def download_file(self, file_info):
        """从NAS下载文件"""
        try:
            filename = file_info.get('name')
            file_path = f"{self.nas_release_path}/{filename}"
            
            headers = {
                'Authorization': self.nas_token
            }
            
            # 获取文件下载链接
            get_data = {
                'path': file_path
            }
            
            get_url = f"{self.nas_base_url}/api/fs/get"
            response = requests.post(get_url, headers={'Authorization': self.nas_token, 'Content-Type': 'application/json'}, json=get_data)
            
            if response.status_code != 200:
                logger.error(f"获取文件信息失败: {filename}")
                return None
            
            result = response.json()
            if result.get('code') != 200:
                logger.error(f"获取文件信息失败: {result.get('message')}")
                return None
            
            raw_url = result.get('data', {}).get('raw_url')
            if not raw_url:
                logger.error(f"无法获取文件下载链接: {filename}")
                return None
            
            # 下载文件
            download_response = requests.get(raw_url, headers=headers)
            if download_response.status_code != 200:
                logger.error(f"下载文件失败: {filename}")
                return None
            
            return download_response.content
            
        except Exception as e:
            logger.error(f"下载文件失败 {file_info.get('name')}: {str(e)}")
            return None
    
    def save_release_html(self, version, content):
        """保存Release HTML到本地目录"""
        try:
            # 创建版本目录
            version_dir = os.path.join(self.local_release_dir, version)
            if not os.path.exists(version_dir):
                os.makedirs(version_dir)
            
            # 保存为index.html
            file_path = os.path.join(version_dir, 'index.html')
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"已保存版本 {version} 到 {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败 {version}: {str(e)}")
            return False
    
    def sync_releases(self):
        """同步NAS上的Release Notes到本地"""
        if not self.enabled:
            logger.info("NAS同步未启用")
            return 0
        
        logger.info("开始同步NAS上的Release Notes...")
        
        # 获取NAS文件列表
        nas_files = self.list_nas_files()
        if not nas_files:
            logger.info("NAS上没有找到Release文件")
            return 0
        
        # 获取本地已有版本
        local_versions = self.get_local_versions()
        
        # 找出需要下载的新版本
        new_versions = []
        for file_info in nas_files:
            filename = file_info.get('name')
            version = self.extract_version_from_filename(filename)
            
            if version and version not in local_versions:
                new_versions.append((version, file_info))
        
        if not new_versions:
            logger.info("没有新版本需要同步")
            return 0
        
        logger.info(f"发现 {len(new_versions)} 个新版本需要下载")
        
        # 下载新版本
        downloaded_count = 0
        for version, file_info in new_versions:
            logger.info(f"正在下载版本 {version}...")
            content = self.download_file(file_info)
            
            if content:
                if self.save_release_html(version, content):
                    downloaded_count += 1
                    logger.info(f"成功下载版本 {version}")
                else:
                    logger.error(f"保存版本 {version} 失败")
            else:
                logger.error(f"下载版本 {version} 失败")
        
        logger.info(f"同步完成，成功下载 {downloaded_count} 个新版本")
        return downloaded_count


def scan_reports():
    """
    扫描所有报告文件
    返回分类的报告列表
    """
    reports = {
        'daily': [],      # 每日报告
        'monthly': [],    # 每月精选
        'releases': [],   # 发布说明
        'focus': []       # 专项测试
    }
    
    # 扫描每日报告 (YYYY/MM/DD/index.html)
    daily_pattern = "[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9]/index.html"
    for file_path in glob.glob(daily_pattern):
        date_parts = file_path.split('/')
        if len(date_parts) >= 4:
            year, month, day = date_parts[0], date_parts[1], date_parts[2]
            reports['daily'].append({
                'path': file_path,
                'year': year,
                'month': month,
                'day': day,
                'date': f"{year}-{month}-{day}",
                'title': f"{year}年{month}月{day}日 测试日报"
            })
    
    # 扫描月度精选报告 (YYYY/MM/index.html)
    monthly_pattern = "[0-9][0-9][0-9][0-9]/[0-9][0-9]/index.html"
    for file_path in glob.glob(monthly_pattern):
        date_parts = file_path.split('/')
        if len(date_parts) == 3:  # 确保是月度报告，不是日报
            year, month = date_parts[0], date_parts[1]
            reports['monthly'].append({
                'path': file_path,
                'year': year,
                'month': month,
                'date': f"{year}-{month}",
                'title': f"{year}年{month}月 测试月报精选"
            })
    
    # 扫描发布说明 (releases/*/index.html)
    releases_pattern = "releases/*/index.html"
    for file_path in glob.glob(releases_pattern):
        parts = file_path.split('/')
        if len(parts) >= 3:
            version = parts[1]
            
            # 尝试从HTML文件中提取发布日期
            release_date = None
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 查找发布日期模式
                    import re
                    date_match = re.search(r'<span class="info-label">发布日期</span>\s*<span class="info-value">(\d{4}年\d{1,2}月\d{1,2}日)</span>', content)
                    if date_match:
                        release_date = date_match.group(1)
            except:
                pass
            
            reports['releases'].append({
                'path': file_path,
                'version': version,
                'title': f"Release {version}",
                'release_date': release_date
            })
    
    # 扫描专项测试报告 (focus/*/index.html)
    focus_pattern = "focus/*/index.html"
    for file_path in glob.glob(focus_pattern):
        parts = file_path.split('/')
        if len(parts) >= 3:
            project = parts[1]
            # 将项目名转换为更友好的标题
            project_title = project.replace('_', ' ').replace('-', ' ').title()
            reports['focus'].append({
                'path': file_path,
                'project': project,
                'title': f"{project_title} 专项测试报告"
            })
    
    # 按日期/版本排序
    reports['daily'].sort(key=lambda x: x['date'], reverse=True)
    reports['monthly'].sort(key=lambda x: x['date'], reverse=True)
    
    # 版本排序函数：解析版本号并返回可比较的元组
    def parse_version(version_str):
        """解析版本号，支持 1.0.16.220 格式"""
        try:
            # 分割版本号
            parts = version_str.split('.')
            # 转换为整数元组，方便比较
            return tuple(int(part) for part in parts)
        except (ValueError, AttributeError):
            # 如果解析失败，返回一个默认值
            return (0, 0, 0, 0)
    
    # 按版本号排序（从新到旧）
    reports['releases'].sort(key=lambda x: parse_version(x['version']), reverse=True)
    reports['focus'].sort(key=lambda x: x['project'])
    
    return reports

def generate_latest_report_section(latest_daily):
    """生成最新报告部分的HTML"""
    if not latest_daily:
        return ''
    
    return f'''
        <div class="hero-section">
            <div class="latest-report">
                <h2>📊 最新日报</h2>
                <p class="report-meta">发布时间：{latest_daily['date']}</p>
                <p>{latest_daily['title']}</p>
                <a href="{latest_daily['path']}" class="latest-report-link">查看最新报告</a>
            </div>
        </div>
    '''

def generate_navigation_html(reports):
    """
    生成导航页面HTML
    """
    # 获取最新的日报作为特色展示
    latest_daily = reports['daily'][0] if reports['daily'] else None
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告中心</title>
    <style>
        :root {{
            --primary-color: #FFD700;
            --secondary-color: #FFDF4F;
            --accent-color: #ff6b6b;
            --text-color: #333;
            --text-secondary: #666;
            --bg-color: #f5f7fa;
            --card-bg: #ffffff;
            --border-color: #e0e0e0;
            --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            --hover-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background: linear-gradient(135deg, #f5f7fa 0%, #f7f9fc 100%);
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            padding: 40px 0;
            text-align: center;
            border-radius: 16px;
            margin-bottom: 40px;
            box-shadow: var(--shadow);
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .subtitle {{
            font-size: 1.1rem;
            opacity: 0.95;
        }}

        .hero-section {{
            margin-bottom: 50px;
        }}

        .latest-report {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 30px;
            box-shadow: var(--shadow);
            margin-bottom: 40px;
            position: relative;
            overflow: hidden;
        }}

        .latest-report::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        }}

        .latest-report h2 {{
            color: var(--text-color);
            margin-bottom: 15px;
            font-size: 1.5rem;
        }}

        .latest-report-link {{
            display: inline-block;
            background: var(--primary-color);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            margin-top: 15px;
        }}

        .latest-report-link:hover {{
            background: var(--secondary-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 215, 0, 0.3);
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section-header {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--border-color);
        }}

        .section-icon {{
            width: 40px;
            height: 40px;
            background: var(--primary-color);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-size: 1.5rem;
        }}

        .section h2 {{
            color: var(--text-color);
            font-size: 1.8rem;
            font-weight: 600;
        }}

        .report-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}

        .report-card {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 20px;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            cursor: pointer;
            text-decoration: none;
            color: var(--text-color);
            display: block;
            position: relative;
            overflow: hidden;
        }}

        .report-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--primary-color);
            transform: scaleY(0);
            transition: transform 0.3s ease;
        }}

        .report-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--hover-shadow);
        }}

        .report-card:hover::before {{
            transform: scaleY(1);
        }}

        .report-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-color);
        }}

        .report-meta {{
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}

        .empty-state {{
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .stat-card {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: var(--shadow);
        }}

        .stat-number {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
        }}

        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 5px;
        }}

        footer {{
            text-align: center;
            padding: 40px 0 20px;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}

            h1 {{
                font-size: 2rem;
            }}

            .report-grid {{
                grid-template-columns: 1fr;
            }}

            .stats {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>测试报告中心</h1>
        </header>

        <!-- 统计信息 -->
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(reports['daily'])}</div>
                <div class="stat-label">日报总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(reports['monthly'])}</div>
                <div class="stat-label">月报总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(reports['releases'])}</div>
                <div class="stat-label">发布版本</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(reports['focus'])}</div>
                <div class="stat-label">专项测试</div>
            </div>
        </div>

        <!-- 最新报告 -->
        {generate_latest_report_section(latest_daily)}

        <!-- 月度精选报告 -->
        <section class="section">
            <div class="section-header">
                <div class="section-icon">📅</div>
                <h2>月度精选报告</h2>
            </div>
            {generate_report_cards(reports['monthly']) if reports['monthly'] else '<div class="empty-state">暂无月度报告</div>'}
        </section>

        <!-- 发布说明 -->
        <section class="section">
            <div class="section-header">
                <div class="section-icon">🚀</div>
                <h2>版本发布报告</h2>
            </div>
            {generate_report_cards(reports['releases']) if reports['releases'] else '<div class="empty-state">暂无发布报告</div>'}
        </section>

        <!-- 专项测试报告 -->
        <section class="section">
            <div class="section-header">
                <div class="section-icon">🎯</div>
                <h2>专项测试报告</h2>
            </div>
            {generate_report_cards(reports['focus']) if reports['focus'] else '<div class="empty-state">暂无专项测试报告</div>'}
        </section>

        <!-- 每日报告 -->
        <section class="section">
            <div class="section-header">
                <div class="section-icon">📆</div>
                <h2>每日测试报告</h2>
            </div>
            {generate_report_cards(reports['daily'][:12]) if reports['daily'] else '<div class="empty-state">暂无日报</div>'}
            {f'<p style="text-align: center; margin-top: 20px; color: var(--text-secondary);">仅显示最近12份日报，共{len(reports["daily"])}份</p>' if len(reports['daily']) > 12 else ''}
        </section>

        <footer>
            <p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Powered by 测试工具箱</p>
        </footer>
    </div>
</body>
</html>'''
    
    return html_content

def generate_report_cards(reports):
    """生成报告卡片HTML"""
    if not reports:
        return ''
    
    cards_html = '<div class="report-grid">'
    for report in reports:
        # 根据报告类型生成不同的描述信息
        if 'date' in report:
            # 对于日报和月报，计算距今天数
            try:
                report_date = datetime.strptime(report['date'], '%Y-%m-%d' if 'day' in report else '%Y-%m')
                days_ago = (datetime.now() - report_date).days
                if days_ago == 0:
                    meta_info = "今天发布"
                elif days_ago == 1:
                    meta_info = "昨天发布"
                elif days_ago < 7:
                    meta_info = f"{days_ago}天前发布"
                elif days_ago < 30:
                    weeks_ago = days_ago // 7
                    meta_info = f"{weeks_ago}周前发布"
                else:
                    meta_info = f"发布于 {report['date']}"
            except:
                meta_info = f"发布于 {report['date']}"
        elif 'version' in report:
            # 对于发布版本，显示发布日期或版本说明
            if report.get('release_date'):
                meta_info = f"发布于 {report['release_date']}"
            else:
                meta_info = f"Version {report['version']} - 功能更新与修复说明"
        elif 'project' in report:
            # 对于专项测试，显示项目描述
            project_desc = {
                'humansensor2nd': '人体传感器第二代专项测试',
                # 可以在这里添加更多项目的描述
            }.get(report['project'], f"{report['project']} 项目专项测试")
            meta_info = project_desc
        else:
            meta_info = "查看详情"
        
        cards_html += f'''
        <a href="{report['path']}" class="report-card">
            <div class="report-title">{report['title']}</div>
            <div class="report-meta">{meta_info}</div>
        </a>
        '''
    cards_html += '</div>'
    
    return cards_html

def main():
    """主函数"""
    try:
        print("🚀 开始生成导航页面...")
        
        # 首先尝试从NAS同步新的Release Notes
        try:
            nas_sync = NASReleaseSync()
            new_releases = nas_sync.sync_releases()
            if new_releases > 0:
                print(f"✅ 从NAS同步了 {new_releases} 个新版本的Release Notes")
        except Exception as e:
            print(f"⚠️ NAS同步失败（继续生成导航页面）: {e}")
        
        # 扫描所有报告
        reports = scan_reports()
        
        print(f"📊 扫描结果:")
        print(f"  - 日报: {len(reports['daily'])} 份")
        print(f"  - 月报: {len(reports['monthly'])} 份")
        print(f"  - 发布报告: {len(reports['releases'])} 份")
        print(f"  - 专项测试: {len(reports['focus'])} 份")
        
        # 生成导航页面HTML
        html_content = generate_navigation_html(reports)
        
        # 保存到index.html
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ 导航页面生成完成!")
        print(f"📄 文件路径: index.html")
        print(f"🕐 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ 生成导航页面时发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
