#!/usr/bin/env python3
"""
报告生成器
"""

import json
import os
from datetime import datetime
from pathlib import Path
from utils import (
    create_daily_directory, 
    fetch_notion_versions,
    load_config_json,
    save_daily_data,
    download_bug_resources,
    download_bug_data,
    get_bug_stats_from_data
)

def generate_html_template(releases_data, bug_info, automation_info, other_info, image_paths, daily_dir):
    """
    生成包含动态数据的HTML内容
    Args:
        releases_data: 版本发布数据
        bug_info: Bug信息
        automation_info: 自动化信息
        other_info: 其他工作信息
        image_paths: 图片路径映射
        daily_dir: 当日数据目录
    Returns:
        str: HTML内容
    """
    
    # 将数据转换为JavaScript格式
    releases_json = json.dumps(releases_data, ensure_ascii=False, indent=2)
    
    # 生成Bug统计卡片
    bug_stats = bug_info.get('bug_stats', {})
    bug_stats_html = f'''
    <div class="stat-card">
        <div class="stat-label">本月新报</div>
        <div class="stat-value">{bug_stats.get('monthly_new', 0)}</div>
        <div class="stat-description">新发现的Bug</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">本月关闭</div>
        <div class="stat-value">{bug_stats.get('monthly_closed', 0)}</div>
        <div class="stat-description">已解决的Bug</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">有效Bug总量</div>
        <div class="stat-value">{bug_stats.get('total_valid', 0)}<span class="plus">+</span><span class="small">{bug_stats.get('in_review', 0)}</span></div>
        <div class="stat-description">待解决 + In Review</div>
    </div>
    '''
    
    # 生成重点关注Bug
    important_bugs_html = ""
    for bug in bug_info.get('important_bugs', []):
        important_bugs_html += f'''
        <a href="{bug.get('url', '#')}" class="bug-card" target="_blank">
            <p class="bug-card-title">{bug.get('title', '')}</p>
            <span class="bug-card-icon">→</span>
        </a>
        '''
    
    # 生成自动化项目卡片
    automation_cards_html = ""
    for project in automation_info.get('automation_projects', []):
        status_class = {
            'completed': 'status-completed',
            'in-progress': 'status-in-progress', 
            'planning': 'status-planning'
        }.get(project.get('status', 'planning'), 'status-planning')
        
        status_text = {
            'completed': '已完成',
            'in-progress': '进行中',
            'planning': '规划中'
        }.get(project.get('status', 'planning'), '规划中')
        
        # 检查是否有URL字段，决定是否添加链接
        project_url = project.get('url', '')
        if project_url:
            # 有URL的项目，生成可点击的链接卡片
            automation_cards_html += f'''
        <a href="{project_url}" class="automation-card automation-card-link" target="_blank">
            <div class="automation-card-header">
                <h3 class="automation-card-title">{project.get('title', '')}</h3>
                <div class="automation-status-badge {status_class}">{status_text}</div>
            </div>
            <p class="automation-card-content">{project.get('description', '')}</p>
            <div class="automation-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {project.get('progress', 0)}%;"></div>
                </div>
                <span class="progress-text">{project.get('progress', 0)}%</span>
            </div>
            <div class="automation-card-link-icon">→</div>
        </a>
        '''
        else:
            # 无URL的项目，使用原来的div结构
            automation_cards_html += f'''
        <div class="automation-card">
            <div class="automation-card-header">
                <h3 class="automation-card-title">{project.get('title', '')}</h3>
                <div class="automation-status-badge {status_class}">{status_text}</div>
            </div>
            <p class="automation-card-content">{project.get('description', '')}</p>
            <div class="automation-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {project.get('progress', 0)}%;"></div>
                </div>
                <span class="progress-text">{project.get('progress', 0)}%</span>
            </div>
        </div>
        '''
    
    # 生成其他工作卡片
    other_cards_html = ""
    for task in other_info.get('other_tasks', []):
        status_class = {
            'completed': 'status-completed',
            'in-progress': 'status-in-progress', 
            'planning': 'status-planning'
        }.get(task.get('status', 'planning'), 'status-planning')
        
        status_text = {
            'completed': '已完成',
            'in-progress': '进行中',
            'planning': '规划中'
        }.get(task.get('status', 'planning'), '规划中')
        
        # 检查是否有URL字段，决定是否添加链接
        task_url = task.get('url', '')
        if task_url:
            # 有URL的任务，生成可点击的链接卡片
            other_cards_html += f'''
        <a href="{task_url}" class="automation-card automation-card-link" target="_blank">
            <div class="automation-card-header">
                <h3 class="automation-card-title">{task.get('title', '')}</h3>
                <div class="automation-status-badge {status_class}">{status_text}</div>
            </div>
            <p class="automation-card-content">{task.get('description', '')}</p>
            <div class="automation-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {task.get('progress', 0)}%;"></div>
                </div>
                <span class="progress-text">{task.get('progress', 0)}%</span>
            </div>
            <div class="automation-card-link-icon">→</div>
        </a>
        '''
        else:
            # 无URL的任务，使用原来的div结构
            other_cards_html += f'''
        <div class="automation-card">
            <div class="automation-card-header">
                <h3 class="automation-card-title">{task.get('title', '')}</h3>
                <div class="automation-status-badge {status_class}">{status_text}</div>
            </div>
            <p class="automation-card-content">{task.get('description', '')}</p>
            <div class="automation-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {task.get('progress', 0)}%;"></div>
                </div>
                <span class="progress-text">{task.get('progress', 0)}%</span>
            </div>
        </div>
        '''
    
    # 获取图片路径（相对于HTML文件）
    priority_chart_src = get_relative_path(image_paths.get('priority_chart', ''), daily_dir)
    variation_chart_src = get_relative_path(image_paths.get('variation_chart', ''), daily_dir)
    
    print(f"🖼️ 优先级图片路径: {priority_chart_src}")
    print(f"🖼️ 变化量图片路径: {variation_chart_src}")
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试工作报告 - {datetime.now().strftime('%Y年%m月')}</title>
    <style>
        :root {{
            --primary-color: #FFD700;
            --secondary-color: #FFDF4F;
            --accent-color: #ff6b6b;
            --dark-gold: #D4AF37;
            --light-gold: #FFF4C2;
            --text-color: #333;
            --text-secondary: #555;
            --light-gray: #f8f8f8;
            --border-color: #e0e0e0;
            --success-color: #4caf50;
            --warning-color: #ff9800;
            --fix-color: #5c6bc0;
            --shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
            --card-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            
            /* 降低饱和度的节点颜色 */
            --main-color: #5B8DC9;
            --branch-color: #E09B47;
            --branch-start-color: #6BBE59;
            --branch-merge-color: #E06B6B;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #f9f9f9;
            background-image: linear-gradient(135deg, #f5f7fa 0%, #f7f9fc 100%);
            padding: 20px 0;
            margin: 0;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0;
            background: white;
            border-radius: 16px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }}

        .header-bg {{
            background: linear-gradient(135deg, #FFD700 0%, #FFDF4F 100%);
            height: auto;
            position: relative;
        }}

        .header-content {{
            position: relative;
            padding: 20px 30px 15px;
        }}

        .release-title {{
            text-align: center;
            margin-bottom: 0;
        }}

        h1 {{
            font-size: 28px;
            font-weight: 700;
            color: white;
            margin: 5px 0;
            text-align: center;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .release-subtitle {{
            font-size: 16px;
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
            margin-bottom: 30px;
            font-weight: 500;
        }}

        .main-content {{
            padding: 20px 30px 40px;
        }}
        
        #diagram-container {{
            width: 100%;
            overflow-x: auto;
            background-color: var(--light-gray);
            border-radius: 12px;
            padding: 20px;
            margin-top: 0;
            box-shadow: none;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        #diagram-container:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }}
        
        svg {{
            width: 100%;
            min-width: 1200px;
            height: 400px;
        }}
        
        .main-line {{
            stroke: var(--main-color);
            stroke-width: 3;
            fill: none;
            opacity: 0.8;
        }}
        
        .branch-line {{
            stroke: var(--branch-color);
            stroke-width: 2.5;
            fill: none;
            opacity: 0.8;
        }}
        
        .branch-line[stroke-dasharray="5,5"] {{
            stroke: var(--branch-color);
            opacity: 0.6;
        }}
        
        .node {{
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .node:hover circle {{
            transform: translateY(-3px);
            filter: brightness(1.1) drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
        }}
        
        .main-node {{
            fill: var(--main-color);
            stroke: white;
            stroke-width: 3;
        }}
        
        .branch-node {{
            fill: var(--branch-color);
            stroke: white;
            stroke-width: 3;
        }}
        
        .branch-start-node {{
            fill: var(--branch-start-color);
            stroke: white;
            stroke-width: 3;
        }}
        
        .branch-merge-node {{
            fill: var(--branch-merge-color);
            stroke: white;
            stroke-width: 3;
        }}
        
        /* 商店发布版本的特殊样式 */
        .store-release-node {{
            fill: var(--primary-color);
            stroke: var(--secondary-color);
            stroke-width: 4;
            filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.6));
        }}
        
        .node-label {{
            font-size: 13px;
            font-weight: 600;
            fill: var(--text-color);
            text-anchor: middle;
            pointer-events: none;
        }}
        
        /* 商店发布版本的标签样式 */
        .store-release-label {{
            font-size: 14px;
            font-weight: 700;
            fill: var(--primary-color);
            text-anchor: middle;
            pointer-events: none;
        }}
        
        .date-label {{
            font-size: 12px;
            fill: var(--text-secondary);
            text-anchor: middle;
            pointer-events: none;
        }}
        
        .tooltip {{
            position: fixed;
            background: linear-gradient(135deg, rgba(0, 0, 0, 0.95) 0%, rgba(0, 0, 0, 0.85) 100%);
            color: white;
            padding: 16px 20px;
            border-radius: 12px;
            font-size: 14px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
            z-index: 1000;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .tooltip.visible {{
            opacity: 1;
        }}

        .tooltip div {{
            margin-bottom: 8px;
            line-height: 1.4;
        }}

        .tooltip div:last-child {{
            margin-bottom: 0;
        }}

        .tooltip strong {{
            color: var(--primary-color);
            font-weight: 600;
        }}
        
        .legend {{
            display: flex;
            gap: 30px;
            margin-top: 20px;
            padding: 20px;
            background-color: transparent;
            border-radius: 12px;
            font-size: 14px;
            justify-content: center;
            box-shadow: none;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            background: white;
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .legend-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}

        .legend-text {{
            font-weight: 500;
            color: var(--text-color);
        }}

        .generated-time {{
            text-align: center;
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 20px;
            padding: 15px;
            background-color: var(--light-gray);
            border-radius: 8px;
        }}

        .powered-by {{
            text-align: center;
            font-size: 14px;
            color: #999;
            padding: 20px 0;
            margin-top: 40px;
        }}

        /* 测试版本信息和Bug信息部分样式 */
        .info-section {{
            margin-top: 30px;
            padding: 30px;
            background-color: white;
            border-radius: 12px;
            box-shadow: var(--card-shadow);
        }}
        
        .info-section:first-child {{
            margin-top: 0;
        }}

        .info-section h2 {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 25px;
        }}

        /* Bug统计卡片 */
        .bug-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
        }}

        .stat-label {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 8px;
            font-weight: 500;
        }}

        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: var(--accent-color);
            line-height: 1;
        }}

        .stat-value .plus {{
            font-size: 24px;
            color: var(--text-secondary);
            margin: 0 5px;
        }}

        .stat-value .small {{
            font-size: 18px;
            color: var(--warning-color);
        }}

        .stat-description {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 5px;
        }}

        /* 重点关注Bug卡片 */
        .bug-cards {{
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin-top: 20px;
        }}

        .bug-card {{
            background: #f8f9fa;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            text-decoration: none;
            color: var(--text-color);
            transition: all 0.3s ease;
            display: block;
            position: relative;
            overflow: hidden;
        }}

        .bug-card::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--primary-color);
            transition: width 0.3s ease;
        }}

        .bug-card:hover {{
            background: white;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            transform: translateX(5px);
        }}

        .bug-card:hover::before {{
            width: 6px;
        }}

        .bug-card-title {{
            font-size: 15px;
            line-height: 1.6;
            color: var(--text-color);
            margin: 0;
        }}

        .bug-card-icon {{
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--main-color);
            opacity: 0.3;
            transition: opacity 0.3s ease;
        }}

        .bug-card:hover .bug-card-icon {{
            opacity: 0.6;
        }}

        .bug-image {{
            display: block;
            max-width: 100%;
            height: auto;
            margin: 20px auto;
            border-radius: 8px;
        }}

        .chart-container {{
            margin: 20px 0;
        }}

        .chart-title {{
            font-size: 16px;
            color: var(--text-color);
            margin-bottom: 15px;
            font-weight: 600;
        }}

        /* 自动化构建卡片样式 */
        .automation-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .automation-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .automation-card::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--primary-color);
            transition: width 0.3s ease;
        }}

        .automation-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
            background: white;
        }}

        .automation-card:hover::before {{
            width: 6px;
        }}

        /* 可点击的自动化卡片样式 */
        .automation-card-link {{
            text-decoration: none;
            color: inherit;
            display: block;
            cursor: pointer;
        }}

        .automation-card-link:hover {{
            text-decoration: none;
            color: inherit;
        }}

        .automation-card-link-icon {{
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--main-color);
            opacity: 0.3;
            transition: opacity 0.3s ease;
            font-size: 18px;
            font-weight: bold;
        }}

        .automation-card-link:hover .automation-card-link-icon {{
            opacity: 0.6;
        }}

        .automation-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}

        .automation-card-title {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-color);
            margin: 0;
            line-height: 1.3;
        }}

        .automation-status-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            text-align: center;
            min-width: 60px;
        }}

        .status-completed {{
            background-color: #e8f5e8;
            color: var(--success-color);
            border: 1px solid #c8e6c8;
        }}

        .status-in-progress {{
            background-color: #fff3e0;
            color: var(--warning-color);
            border: 1px solid #ffcc80;
        }}

        .status-planning {{
            background-color: #e3f2fd;
            color: #1976d2;
            border: 1px solid #90caf9;
        }}

        .automation-card-content {{
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.5;
            margin: 0 0 16px 0;
        }}

        .automation-progress {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .progress-bar {{
            flex: 1;
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            border-radius: 4px;
            transition: width 0.3s ease;
        }}

        .progress-text {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            min-width: 35px;
            text-align: right;
        }}

        /* 响应式设计 */
        @media (max-width: 768px) {{
            body {{
                padding: 0;
            }}
            
            .container {{
                border-radius: 0;
                box-shadow: none;
            }}
            
            .header-content {{
                padding: 15px 20px;
            }}
            
            .main-content {{
                padding: 10px 10px;
            }}
            
            h1 {{
                font-size: 22px;
            }}

            .legend {{
                flex-wrap: wrap;
                gap: 15px;
            }}

            .legend-item {{
                flex: 1 1 150px;
            }}

            .info-section {{
                padding: 20px;
            }}

            .info-section h2 {{
                font-size: 20px;
            }}

            .bug-stats {{
                grid-template-columns: 1fr;
            }}

            .automation-cards {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-bg">
            <div class="header-content">
                <div class="release-title">
                    <h1>测试工作报告 - {datetime.now().strftime('%Y年%m月')}</h1>
                </div>
            </div>
        </div>

        <div class="main-content">
            <!-- 测试版本信息 -->
            <div class="info-section">
                <h2>测试版本信息</h2>
                <div id="diagram-container">
                    <svg id="release-diagram"></svg>
                </div>
                
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--main-color);"></div>
                        <span class="legend-text">主版本</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--branch-color);"></div>
                        <span class="legend-text">分支版本</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--branch-start-color);"></div>
                        <span class="legend-text">分支开始</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: var(--branch-merge-color);"></div>
                        <span class="legend-text">分支合并</span>
                    </div>
                </div>
            </div>

            <!-- Bug信息部分 -->
            <div class="info-section">
                <h2>Bug信息</h2>
                
                <!-- Bug统计卡片 -->
                <div class="bug-stats">
                    {bug_stats_html}
                </div>

                <!-- 图表部分 -->
                <div class="chart-container">
                    <h3 class="chart-title">按照优先级进行区分</h3>
                    <img class="bug-image" src="{priority_chart_src}" alt="优先级饼图">
                </div>

                <div class="chart-container">
                    <h3 class="chart-title">每日变化量</h3>
                    <img class="bug-image" src="{variation_chart_src}" alt="每日变化量">
                </div>

                <!-- 重点关注Bug -->
                <h3 class="chart-title">重点关注Bug</h3>
                <div class="bug-cards">
                    {important_bugs_html}
                </div>
            </div>

            <!-- 自动化构建部分 -->
            <div class="info-section">
                <h2>自动化构建</h2>
                
                <!-- 自动化项目卡片 -->
                <div class="automation-cards">
                    {automation_cards_html}
                </div>
            </div>

            <!-- 其他工作部分 -->
            <div class="info-section">
                <h2>其他工作</h2>
                
                <!-- 其他工作卡片 -->
                <div class="automation-cards">
                    {other_cards_html}
                </div>
            </div>
            
            <!-- 页脚 -->
            <div class="generated-time">
                报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
            <div class="powered-by">
                Powered by 测试工具箱
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        // 版本数据
        const releasesData = {releases_json};
        
        function drawDiagram(releases) {{
            const svg = document.getElementById('release-diagram');
            svg.innerHTML = '';
            
            const margin = {{ top: 60, right: 80, bottom: 60, left: 50 }};
            const width = Math.max(1200, releases.length * 100 + 100);
            const height = 400;
            
            svg.setAttribute('viewBox', `0 0 ${{width}} ${{height}}`);
            
            // 计算日期范围
            const dates = releases.map(r => new Date(r.date));
            const minDate = new Date(Math.min(...dates));
            const maxDate = new Date(Math.max(...dates));
            const dateRange = maxDate - minDate;
            
            // 按日期分组版本，处理同一天多个版本的情况
            const dateGroups = {{}};
            releases.forEach(release => {{
                const dateKey = release.date; // 使用日期字符串作为key
                if (!dateGroups[dateKey]) {{
                    dateGroups[dateKey] = [];
                }}
                dateGroups[dateKey].push(release);
            }});
            
            // 为每个版本分配精确的x坐标，同一天的版本水平排开
            const releasePositions = new Map();
            Object.keys(dateGroups).forEach(dateKey => {{
                const versionsOnDate = dateGroups[dateKey];
                const baseDate = new Date(dateKey);
                const baseX = margin.left + ((baseDate - minDate) / dateRange) * (width - margin.left - margin.right - 50);
                
                if (versionsOnDate.length === 1) {{
                    // 单个版本，使用基础位置
                    releasePositions.set(versionsOnDate[0].version, baseX);
                }} else {{
                    // 多个版本，水平排开，使用和相邻天数一样的间距
                    const totalTimeSpan = width - margin.left - margin.right - 50;
                    const daySpacing = dateRange > 0 ? totalTimeSpan / (dateRange / (24 * 60 * 60 * 1000)) : 100;
                    const spacing = Math.min(daySpacing, 100); // 使用天间距，但不超过100px
                    const totalWidth = (versionsOnDate.length - 1) * spacing;
                    const startX = baseX - totalWidth / 2;
                    
                    // 按版本号排序，提取括号中的数字进行比较
                    versionsOnDate.sort((a, b) => {{
                        // 提取版本号中括号内的数字，例如 "1.0.15(181)" -> 181
                        const getVersionNumber = (version) => {{
                            const match = version.match(/\\((\\d+)\\)/);
                            return match ? parseInt(match[1]) : 0;
                        }};
                        
                        const aNum = getVersionNumber(a.version);
                        const bNum = getVersionNumber(b.version);
                        
                        // 添加调试信息
                        console.log(`排序 ${{dateKey}}: ${{a.version}}(${{aNum}}) vs ${{b.version}}(${{bNum}}) = ${{aNum - bNum}}`);
                        
                        return aNum - bNum; // 升序排列
                    }});
                    
                    console.log(`${{dateKey}} 排序后顺序:`, versionsOnDate.map(v => v.version));
                    
                    versionsOnDate.forEach((release, index) => {{
                        const x = startX + index * spacing;
                        releasePositions.set(release.version, x);
                        console.log(`${{release.version}}: index=${{index}}, x=${{x.toFixed(2)}}`);
                    }});
                }}
            }});
            
            // 防重叠处理：确保所有节点之间有最小距离
            const minDistance = 40;
            const sortedVersions = [...releases].sort((a, b) => {{
                // 先按日期排序
                const dateCompare = new Date(a.date) - new Date(b.date);
                if (dateCompare !== 0) return dateCompare;
                
                // 同一天的按版本号排序
                const getVersionNumber = (version) => {{
                    const match = version.match(/\\((\\d+)\\)/);
                    return match ? parseInt(match[1]) : 0;
                }};
                
                return getVersionNumber(a.version) - getVersionNumber(b.version);
            }});
            
            console.log('防重叠处理前的位置:');
            for (const [version, x] of releasePositions.entries()) {{
                console.log(`${{version}}: x=${{x.toFixed(2)}}`);
            }}
            
            for (let i = 1; i < sortedVersions.length; i++) {{
                const current = sortedVersions[i];
                const prev = sortedVersions[i - 1];
                const currentX = releasePositions.get(current.version);
                const prevX = releasePositions.get(prev.version);
                
                if (currentX - prevX < minDistance) {{
                    console.log(`调整位置: ${{current.version}} 从 ${{currentX.toFixed(2)}} 移到 ${{(prevX + minDistance).toFixed(2)}}`);
                    releasePositions.set(current.version, prevX + minDistance);
                }}
            }}
            
            console.log('防重叠处理后的位置:');
            for (const [version, x] of releasePositions.entries()) {{
                console.log(`${{version}}: x=${{x.toFixed(2)}}`);
            }}
            
            // 创建 x 轴比例尺函数，使用预计算的位置
            const xScale = (release) => {{
                if (typeof release === 'string') {{
                    // 如果传入的是日期字符串，使用原有逻辑
                    const d = new Date(release);
                    return margin.left + ((d - minDate) / dateRange) * (width - margin.left - margin.right - 50);
                }} else {{
                    // 如果传入的是release对象，使用预计算的位置
                    return releasePositions.get(release.version) || margin.left;
                }}
            }};
            
            const mainY = height / 2;
            const branchY = height / 2 + 120;
            
            // 分析分支结构 - 按时间顺序找到所有的分支组
            const branches = [];
            const mainReleases = [];
            let currentBranch = null;
            
            // 按时间顺序排序释放数据（确保正确的时间顺序）
            const sortedReleases = [...releases].sort((a, b) => new Date(a.date) - new Date(b.date));
            
            sortedReleases.forEach((release, index) => {{
                if (release.type === 'branch-start') {{
                    // 开始新分支
                    currentBranch = {{
                        start: release,
                        releases: [release],
                        end: null,
                        merged: false
                    }};
                    mainReleases.push(release); // 分支起点也在主线上
                }} else if (release.type === 'branch-merge') {{
                    // 分支合并回主线
                    if (currentBranch) {{
                        currentBranch.end = release;
                        currentBranch.releases.push(release);
                        currentBranch.merged = true;
                        branches.push(currentBranch);
                        currentBranch = null;
                    }}
                    mainReleases.push(release); // 合并点也在主线上
                }} else if (release.type === 'branch') {{
                    // 分支中的版本
                    if (currentBranch) {{
                        currentBranch.releases.push(release);
                    }}
                }} else {{
                    // 主线版本
                    mainReleases.push(release);
                }}
            }});
            
            // 如果有未合并的分支，也添加到branches中
            if (currentBranch) {{
                branches.push(currentBranch);
            }}
            
            
            // 创建渐变定义
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
            
            // 主线渐变
            const mainGradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
            mainGradient.setAttribute('id', 'mainGradient');
            mainGradient.setAttribute('x1', '0%');
            mainGradient.setAttribute('x2', '100%');
            
            const mainStop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            mainStop1.setAttribute('offset', '0%');
            mainStop1.setAttribute('stop-color', 'var(--main-color)');
            mainStop1.setAttribute('stop-opacity', '0.8');
            
            const mainStop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            mainStop2.setAttribute('offset', '100%');
            mainStop2.setAttribute('stop-color', 'var(--main-color)');
            mainStop2.setAttribute('stop-opacity', '0.6');
            
            mainGradient.appendChild(mainStop1);
            mainGradient.appendChild(mainStop2);
            defs.appendChild(mainGradient);
            
            // 箭头标记
            const arrowMarker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
            arrowMarker.setAttribute('id', 'arrowhead');
            arrowMarker.setAttribute('markerWidth', '10');
            arrowMarker.setAttribute('markerHeight', '7');
            arrowMarker.setAttribute('refX', '9');
            arrowMarker.setAttribute('refY', '3.5');
            arrowMarker.setAttribute('orient', 'auto');
            
            const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
            arrow.setAttribute('points', '0 0, 10 3.5, 0 7');
            arrow.setAttribute('fill', 'var(--main-color)');
            arrow.setAttribute('opacity', '0.8');
            
            arrowMarker.appendChild(arrow);
            defs.appendChild(arrowMarker);
            svg.appendChild(defs);
            
            // 绘制主线（带箭头）
            if (mainReleases.length > 1) {{
                const lastX = xScale(mainReleases[mainReleases.length - 1]);
                const extendedX = width - margin.right + 20;
                
                let pathData = `M ${{xScale(mainReleases[0])}} ${{mainY}}`;
                for (let i = 1; i < mainReleases.length; i++) {{
                    pathData += ` L ${{xScale(mainReleases[i])}} ${{mainY}}`;
                }}
                // 延伸到箭头
                pathData += ` L ${{extendedX}} ${{mainY}}`;
                
                const mainLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                mainLine.setAttribute('d', pathData);
                mainLine.setAttribute('class', 'main-line');
                mainLine.setAttribute('stroke', 'url(#mainGradient)');
                mainLine.setAttribute('marker-end', 'url(#arrowhead)');
                svg.appendChild(mainLine);
            }}
            
            // 绘制所有分支线
            branches.forEach((branch, branchIndex) => {{
                if (branch.releases.length < 2) return; // 至少需要2个节点才能画线
                
                const startX = xScale(branch.start);
                const cornerRadius = 20;
                let pathData = `M ${{startX}} ${{mainY}}`;
                
                // 为每个分支分配不同的Y坐标，避免重叠
                const currentBranchY = branchY + (branchIndex * 60);
                
                // 从主线下降到分支线
                pathData += ` L ${{startX}} ${{currentBranchY - cornerRadius}}`;
                pathData += ` Q ${{startX}} ${{currentBranchY}}, ${{startX + cornerRadius}} ${{currentBranchY}}`;
                
                // 连接分支中的所有节点（除了起点和终点）
                for (let i = 1; i < branch.releases.length - 1; i++) {{
                    const nodeX = xScale(branch.releases[i]);
                    pathData += ` L ${{nodeX}} ${{currentBranchY}}`;
                }}
                
                if (branch.merged && branch.end) {{
                    // 分支合并回主线
                    const endX = xScale(branch.end);
                    pathData += ` L ${{endX - cornerRadius}} ${{currentBranchY}}`;
                    pathData += ` Q ${{endX}} ${{currentBranchY}}, ${{endX}} ${{currentBranchY - cornerRadius}}`;
                    pathData += ` L ${{endX}} ${{mainY}}`;
                }} else {{
                    // 未合并的分支，延伸到最后一个节点
                    const lastRelease = branch.releases[branch.releases.length - 1];
                    const lastX = xScale(lastRelease);
                    pathData += ` L ${{lastX}} ${{currentBranchY}}`;
                }}
                
                const branchLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                branchLine.setAttribute('d', pathData);
                branchLine.setAttribute('class', 'branch-line');
                branchLine.setAttribute('stroke-dasharray', branch.merged ? '0' : '5,5'); // 未合并的分支用虚线
                svg.appendChild(branchLine);
            }});
            
            // 绘制节点
            releases.forEach((release, index) => {{
                const x = xScale(release);
                let y = mainY;
                
                // 确定节点的 y 坐标
                if (release.type === 'branch') {{
                    // 找到这个节点属于哪个分支
                    const branchIndex = branches.findIndex(branch => 
                        branch.releases.some(r => r.version === release.version)
                    );
                    if (branchIndex >= 0) {{
                        y = branchY + (branchIndex * 60);
                    }} else {{
                        y = branchY; // 默认分支位置
                    }}
                }} else if (release.type === 'branch-start' || release.type === 'branch-merge') {{
                    // 分支起点和合并点都在主线上
                    y = mainY;
                }}
                
                // 创建节点组
                const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                g.setAttribute('class', 'node');
                
                // 创建圆形节点
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', x);
                circle.setAttribute('cy', y);
                circle.setAttribute('r', 10);
                
                // 设置节点颜色
                let nodeClass = 'main-node';
                let labelClass = 'node-label';
                
                // 检查是否是商店发布版本
                const isStoreRelease = release.note && release.note.includes('主线版本(商店发布)');
                
                if (isStoreRelease) {{
                    nodeClass = 'store-release-node';
                    labelClass = 'store-release-label';
                }} else if (release.type === 'branch') {{
                    nodeClass = 'branch-node';
                }} else if (release.type === 'branch-start') {{
                    nodeClass = 'branch-start-node';
                }} else if (release.type === 'branch-merge') {{
                    nodeClass = 'branch-merge-node';
                }}
                circle.setAttribute('class', nodeClass);
                
                // 添加版本号标签，计算错开的Y坐标
                const versionLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                versionLabel.setAttribute('x', x);
                
                // 版本号错开逻辑：检查相邻版本的距离，如果太近就错开
                let labelY = y - 20;
                const minLabelDistance = 50; // 版本号之间的最小距离
                
                // 检查前面的版本号是否会重叠
                for (let i = 0; i < index; i++) {{
                    const prevRelease = releases[i];
                    const prevX = xScale(prevRelease);
                    
                    if (Math.abs(x - prevX) < minLabelDistance) {{
                        // 距离太近，交替错开：奇数索引向上，偶数索引向下
                        if (index % 2 === 0) {{
                            labelY = y - 35; // 向上错开更多
                        }} else {{
                            labelY = y - 5;  // 向下错开
                        }}
                        break;
                    }}
                }}
                
                versionLabel.setAttribute('y', labelY);
                versionLabel.setAttribute('class', labelClass);
                versionLabel.textContent = release.version.split('.').slice(-1)[0]; // 只显示最后一部分
                
                // 添加日期标签
                const dateLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                dateLabel.setAttribute('x', x);
                dateLabel.setAttribute('y', y + 30);
                dateLabel.setAttribute('class', 'date-label');
                dateLabel.textContent = formatDate(release.date);
                
                g.appendChild(circle);
                g.appendChild(versionLabel);
                g.appendChild(dateLabel);
                
                // 添加交互事件
                g.addEventListener('mouseenter', (e) => showTooltip(e, release));
                g.addEventListener('mouseleave', hideTooltip);
                
                svg.appendChild(g);
            }});
        }}
        
        function formatDate(dateStr) {{
            const date = new Date(dateStr);
            const month = date.getMonth() + 1;
            const day = date.getDate();
            return `${{month}}.${{day}}`;
        }}
        
        function showTooltip(event, release) {{
            const tooltip = document.getElementById('tooltip');
            tooltip.innerHTML = `
                <div><strong>版本号：</strong>${{release.version}}</div>
                <div><strong>发布日期：</strong>${{release.date}}</div>
                <div><strong>部署环境：</strong>${{release.environment}}</div>
                <div><strong>版本类型：</strong>${{release.note}}</div>
            `;
            
            // 获取鼠标位置
            const mouseX = event.clientX;
            const mouseY = event.clientY;
            
            // 设置 tooltip 位置
            tooltip.style.left = (mouseX + 15) + 'px';
            tooltip.style.top = (mouseY - 60) + 'px';
            
            // 显示 tooltip
            tooltip.classList.add('visible');
        }}
        
        function hideTooltip() {{
            const tooltip = document.getElementById('tooltip');
            tooltip.classList.remove('visible');
        }}
        
        // 页面加载时绘制图表
        window.addEventListener('load', () => {{
            drawDiagram(releasesData.releases);
        }});
    </script>
</body>
</html>'''
    
    return html_content

def get_relative_path(file_path, base_dir):
    """
    获取相对于当前工作目录的路径（HTML文件位置）
    Args:
        file_path: 文件绝对路径
        base_dir: 基础目录
    Returns:
        str: 相对路径或原始URL
    """
    if not file_path or file_path.startswith('http'):
        return file_path
    
    try:
        # HTML文件在根目录，所以相对路径就是去掉根目录前缀
        if os.path.isabs(file_path):
            # 获取相对于当前工作目录的路径
            current_dir = os.getcwd()
            relative_path = os.path.relpath(file_path, current_dir)
            return relative_path
        else:
            return file_path
    except (ValueError, OSError):
        return file_path

def main():
    """主函数"""
    try:
        print("🚀 开始生成月度报告...")
        
        # 创建当日目录
        daily_dir = create_daily_directory()
        print(f"📁 当日数据目录: {daily_dir}")
        
        # 1. 获取版本信息
        print("\n📊 获取版本信息...")
        releases_data = fetch_notion_versions()
        
        # 如果API获取失败，使用备用数据
        if not releases_data:
            print("⚠️ 使用备用版本数据")
            if os.path.exists('releases.json'):
                with open('releases.json', 'r', encoding='utf-8') as f:
                    releases_data = json.load(f)
            else:
                releases_data = {"releases": []}
        
        # 保存版本数据到当日目录
        save_daily_data(releases_data, "releases.json")
        
        # 2. 下载外部资源
        print("\n🔄 下载外部资源...")
        image_paths = download_bug_resources(daily_dir)
        download_bug_data(daily_dir)
        
        # 3. 获取动态Bug统计数据
        print("\n📊 解析Bug统计数据...")
        dynamic_bug_stats = get_bug_stats_from_data(daily_dir)
        
        # 4. 加载配置文件并合并动态数据
        print("\n📋 加载配置信息...")
        bug_info = load_config_json('config/bug_info.json')
        automation_info = load_config_json('config/automation_info.json')
        other_info = load_config_json('config/other_info.json')
        
        # 用动态数据覆盖静态配置
        if dynamic_bug_stats:
            bug_info['bug_stats'] = dynamic_bug_stats
            print(f"✅ 使用动态Bug数据: 新报{dynamic_bug_stats['monthly_new']}, 关闭{dynamic_bug_stats['monthly_closed']}, 有效{dynamic_bug_stats['total_valid']}, 审核中{dynamic_bug_stats['in_review']}")
        else:
            print("⚠️ 使用静态Bug配置数据")
        
        # 5. 生成HTML报告
        print("\n🎨 生成HTML报告...")
        html_content = generate_html_template(
            releases_data, bug_info, automation_info, other_info, image_paths, daily_dir
        )
        
        # 6. 保存HTML文件
        output_filename = 'index.html'
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 同时保存到当日目录
        daily_html_path = os.path.join(daily_dir, output_filename)
        with open(daily_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ 报告生成完成!")
        print(f"📄 主报告文件: {output_filename}")
        print(f"📄 当日备份: {daily_html_path}")
        print(f"📊 版本记录数: {len(releases_data.get('releases', []))}")
        print(f"🕐 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ 生成报告时发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()