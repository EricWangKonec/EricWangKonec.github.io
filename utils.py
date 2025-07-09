#!/usr/bin/env python3
"""
工具模块：处理API请求、文件下载、目录创建等功能
"""

import os
import json
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def create_daily_directory(date=None):
    """
    根据日期创建目录结构 ./YYYY/MM/DD
    Args:
        date: datetime对象，默认为今天
    Returns:
        str: 创建的目录路径
    """
    if date is None:
        date = datetime.now()
    
    # 格式化日期路径
    year = date.strftime('%Y')
    month = date.strftime('%m') 
    day = date.strftime('%d')
    
    # 创建目录路径
    dir_path = Path(f"./{year}/{month}/{day}")
    dir_path.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ 创建目录: {dir_path}")
    return str(dir_path)

def fetch_notion_versions():
    """
    从Notion API获取版本信息
    Returns:
        dict: 版本数据
    """
    token = os.getenv('VERSION_INFO_NOTION_API')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not token or not database_id:
        print("⚠️ 警告: 未配置Notion API token或数据库ID")
        return None
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    headers = {
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28',
        'Authorization': f'Bearer {token}'
    }
    
    body = {
        "filter": {
            "property": "版本号",
            "title": {
                "is_not_empty": True
            }
        },
        "sorts": [
            {
                "property": "Date",
                "direction": "descending"
            }
        ]
    }
    
    try:
        print("🔄 正在从Notion获取版本信息...")
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ 成功获取 {len(data.get('results', []))} 条版本记录")
        return parse_notion_data(data)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Notion API请求失败: {e}")
        return None

def parse_notion_data(notion_data):
    """
    解析Notion API返回的数据为标准格式，并过滤上个月1号至今的数据
    Args:
        notion_data: Notion API返回的原始数据
    Returns:
        dict: 标准化的版本数据
    """
    releases = []
    
    # 计算上个月1号的日期
    today = datetime.now()
    if today.month == 1:
        last_month_first = datetime(today.year - 1, 12, 1)
    else:
        last_month_first = datetime(today.year, today.month - 1, 1)
    
    print(f"📅 数据过滤范围: {last_month_first.strftime('%Y-%m-%d')} 至今")
    
    for item in notion_data.get('results', []):
        properties = item.get('properties', {})
        
        # 提取版本号
        version_prop = properties.get('版本号', {})
        version = ""
        if version_prop.get('title'):
            version = version_prop['title'][0].get('plain_text', '')
        
        # 提取日期
        date_prop = properties.get('Date', {})
        date = ""
        if date_prop.get('date'):
            date = date_prop['date'].get('start', '')
        
        # 日期过滤：只保留上个月1号至今的数据
        if date:
            try:
                record_date = datetime.strptime(date, '%Y-%m-%d')
                if record_date < last_month_first:
                    continue  # 跳过过早的数据
            except ValueError:
                print(f"⚠️ 日期格式错误: {date}")
                continue
        
        # 提取类型
        type_prop = properties.get('Type', {})
        release_type = "main"
        if type_prop.get('select'):
            type_name = type_prop['select'].get('name', '')
            # 先检查更具体的类型
            if "分支版本开始" in type_name or "开始" in type_name:
                release_type = "branch-start"
            elif "分支合并" in type_name or "合并" in type_name or "并入" in type_name or "回主线" in type_name or "核入主线" in type_name:
                release_type = "branch-merge"
            elif "分支版本" in type_name or "分支" in type_name:
                release_type = "branch"
            
        
        # 提取状态
        status_prop = properties.get('Status', {})
        environment = "生产环境"
        
        if version and date:
            releases.append({
                "version": version,
                "date": date,
                "type": release_type,
                "environment": environment,
                "note": type_prop.get('select', {}).get('name', '') if type_prop.get('select') else ""
            })
    
    print(f"✅ 过滤后保留 {len(releases)} 条版本记录")
    return {"releases": releases}

def download_external_resource(url, local_path):
    """
    下载外部资源到本地
    Args:
        url: 资源URL
        local_path: 本地保存路径
    Returns:
        bool: 是否下载成功
    """
    try:
        print(f"🔄 正在下载: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 下载完成: {local_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 下载失败 {url}: {e}")
        return False

def load_config_json(config_path):
    """
    加载本地JSON配置文件
    Args:
        config_path: 配置文件路径
    Returns:
        dict: 配置数据
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ 无法加载配置文件 {config_path}: {e}")
        return {}

def save_daily_data(data, filename, date=None):
    """
    保存数据到当日目录
    Args:
        data: 要保存的数据
        filename: 文件名
        date: 日期，默认为今天
    Returns:
        str: 保存的文件路径
    """
    daily_dir = create_daily_directory(date)
    file_path = os.path.join(daily_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已保存: {file_path}")
    return file_path

def download_bug_resources(daily_dir):
    """
    下载Bug相关的图片资源到当日目录
    Args:
        daily_dir: 当日目录路径
    Returns:
        dict: 本地图片路径
    """
    images_dir = os.path.join(daily_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # 图片URL配置
    image_urls = {
        'priority_chart': os.getenv('PRIORITY_CHART_URL'),
        'variation_chart': os.getenv('BUG_VARIATION_CHART_URL'),
        'modules_chart': os.getenv('MODULES_CHART_URL'),
        'priority_history_chart': os.getenv('PRIORITY_HISTORY_CHART_URL'),
        'weekly_analysis_chart': os.getenv('WEEKLY_ANALYSIS_CHART_URL')
    }
    
    local_paths = {}
    
    for key, url in image_urls.items():
        if url:
            local_path = os.path.join(images_dir, f"{key}.png")
            if download_external_resource(url, local_path):
                local_paths[key] = local_path
                print(f"✅ 图片下载成功: {key}")
            else:
                # 如果下载失败，使用原URL
                local_paths[key] = url
                print(f"⚠️ 图片下载失败，使用原URL: {key}")
        else:
            print(f"⚠️ 未配置图片URL: {key}")
    
    return local_paths

def download_bug_data(daily_dir):
    """
    下载Bug数据文件到当日目录
    Args:
        daily_dir: 当日目录路径
    Returns:
        str: 本地数据文件路径，如果下载失败返回None
    """
    bug_data_url = os.getenv('BUG_DATA_URL')
    if not bug_data_url:
        return None
    
    local_path = os.path.join(daily_dir, "bug_data.md")
    
    if download_external_resource(bug_data_url, local_path):
        return local_path
    return None

def parse_bug_data(markdown_content):
    """
    解析Bug数据markdown文件，提取统计信息
    Args:
        markdown_content: markdown文件内容
    Returns:
        dict: Bug统计信息
    """
    bug_stats = {
        'monthly_new': 0,
        'monthly_closed': 0,
        'total_valid': 0,
        'in_review': 0
    }
    
    try:
        # 提取本月新报和关闭数量
        monthly_pattern = r'本月总计新报\*\*(\d+)\*\*个Bug.*?总计关闭\*\*(\d+)\*\*个Bug'
        monthly_match = re.search(monthly_pattern, markdown_content)
        if monthly_match:
            bug_stats['monthly_new'] = int(monthly_match.group(1))
            bug_stats['monthly_closed'] = int(monthly_match.group(2))
            print(f"📊 提取到月度数据: 新报{bug_stats['monthly_new']}, 关闭{bug_stats['monthly_closed']}")
        else:
            print("⚠️ 未找到月度Bug数据")
        
        # 提取有效Bug透视图总数（包含In Review）
        # 查找第一个表格的总数行，需要匹配表格最后一列的数字
        valid_section = re.search(r'### 有效Bug透视图.*?(?=###|$)', markdown_content, re.DOTALL)
        total_with_review = 0
        if valid_section:
            valid_content = valid_section.group(0)
            # 在这个部分查找总数行，匹配表格中最后一列的数字
            total_line = re.search(r'\| 总数.*?\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d+)\s*\|', valid_content)
            if total_line:
                total_with_review = int(total_line.group(1))
                print(f"📊 有效Bug总数(含In Review): {total_with_review}")
            else:
                print("⚠️ 在有效Bug透视图中未找到总数行")
        else:
            print("⚠️ 未找到有效Bug透视图部分")
        
        # 提取不含In Review的有效Bug透视图总数
        no_review_section = re.search(r'### 不含In Review的有效Bug透视图.*?(?=###|$)', markdown_content, re.DOTALL)
        if no_review_section:
            no_review_content = no_review_section.group(0)
            # 在这个部分查找总数行，匹配表格中最后一列的数字
            total_line = re.search(r'\| 总数.*?\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d+)\s*\|', no_review_content)
            if total_line:
                total_without_review = int(total_line.group(1))
                bug_stats['total_valid'] = total_without_review
                
                # 计算In Review数量
                if total_with_review > 0:
                    bug_stats['in_review'] = total_with_review - total_without_review
                
                print(f"📊 不含In Review Bug总数: {bug_stats['total_valid']}")
                print(f"📊 In Review Bug数量: {bug_stats['in_review']}")
            else:
                print("⚠️ 在不含In Review透视图中未找到总数行")
        else:
            print("⚠️ 未找到不含In Review的Bug透视图部分")
        
    except Exception as e:
        print(f"⚠️ 解析Bug数据时发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    return bug_stats

def get_bug_stats_from_data(daily_dir):
    """
    从下载的Bug数据中提取统计信息
    Args:
        daily_dir: 当日目录路径
    Returns:
        dict: Bug统计信息
    """
    bug_data_path = os.path.join(daily_dir, "bug_data.md")
    
    if os.path.exists(bug_data_path):
        try:
            with open(bug_data_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return parse_bug_data(content)
        except Exception as e:
            print(f"⚠️ 读取Bug数据文件失败: {e}")
    
    # 如果没有数据文件或读取失败，返回默认值
    return {
        'monthly_new': 0,
        'monthly_closed': 0,
        'total_valid': 0,
        'in_review': 0
    }

def load_watch_dog_data():
    """
    加载所有watch dog监控数据
    Returns:
        dict: 所有监控对象的数据，key为objectId，value为监控历史
    """
    watch_dog_dir = "config/watch_dog_data"
    watch_dog_data = {}
    
    if not os.path.exists(watch_dog_dir):
        print(f"⚠️ 监控数据目录不存在: {watch_dog_dir}")
        return watch_dog_data
    
    try:
        # 遍历所有JSON文件
        for filename in os.listdir(watch_dog_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(watch_dog_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    object_id = data.get('objectId')
                    if object_id:
                        watch_dog_data[object_id] = data
                        object_name = data.get('objectName', object_id)
                        print(f"✅ 加载监控数据: {object_name} ({len(data.get('history', []))} 条记录)")
    except Exception as e:
        print(f"❌ 加载监控数据失败: {e}")
        import traceback
        traceback.print_exc()
    
    return watch_dog_data

def calculate_daily_stability(watch_dog_data, start_date, end_date):
    """
    计算每天的稳定性数据
    Args:
        watch_dog_data: 监控数据
        start_date: 开始日期
        end_date: 结束日期
    Returns:
        dict: 每天的稳定性数据
    """
    daily_stats = {}
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        daily_stats[date_str] = {}
        
        # 遍历所有监控对象
        for object_id, obj_data in watch_dog_data.items():
            history = obj_data.get('history', [])
            
            # 统计当天的状态
            total_checks = 0
            online_checks = 0
            has_data = False
            
            for record in history:
                # 解析记录时间
                try:
                    record_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    record_date = record_time.date()
                    
                    # 如果是当天的记录
                    if record_date == current_date.date():
                        has_data = True
                        total_checks += 1
                        if record.get('status') == 'online':
                            online_checks += 1
                except Exception as e:
                    print(f"⚠️ 解析时间戳失败: {record.get('timestamp')}")
                    continue
            
            # 计算稳定性百分比
            if has_data:
                stability_percent = (online_checks / total_checks * 100) if total_checks > 0 else 0
                daily_stats[date_str][object_id] = {
                    'stability': stability_percent,
                    'total_checks': total_checks,
                    'online_checks': online_checks,
                    'has_data': True
                }
            else:
                daily_stats[date_str][object_id] = {
                    'stability': None,
                    'total_checks': 0,
                    'online_checks': 0,
                    'has_data': False
                }
        
        current_date += timedelta(days=1)
    
    return daily_stats