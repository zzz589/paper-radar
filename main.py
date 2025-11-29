import requests
import os
from datetime import datetime
import math

# === 配置项 ===
# 你可以在 GitHub Secrets 设置 KEYWORDS，也可以直接在这里改
KEYWORDS = os.environ.get("KEYWORDS", "Large Language Models") 
# 只看发布了 6 - 12 个月的
MIN_MONTHS = 6  
MAX_MONTHS = 12
# 基础门槛：比如这期间至少要有 5 个引用
MIN_CITATIONS = 5

def fetch_and_analyze():
    print(f"🔍 正在检索关键词: {KEYWORDS}...")
    
    # 动态计算年份范围（近两年）
    current_year = datetime.now().year
    year_range = f"{current_year-2}-{current_year}"
    
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": KEYWORDS,
        "year": year_range,
        "limit": 100, # 每次分析前100个相关度最高的
        "fields": "title,publicationDate,citationCount,influentialCitationCount,abstract,url,authors"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json().get('data', [])
    except Exception as e:
        print(f"API Error: {e}")
        return []

    candidates = []
    current_date = datetime.now()

    for paper in data:
        if not paper.get('publicationDate'): continue
        
        # --- 核心逻辑：时间窗筛选 ---
        try:
            pub_date = datetime.strptime(paper['publicationDate'], "%Y-%m-%d")
        except:
            continue
            
        days_diff = (current_date - pub_date).days
        months_diff = days_diff / 30.0
        
        # Step 1: 必须是 6-12 个月前的
        if not (MIN_MONTHS <= months_diff <= MAX_MONTHS):
            continue
            
        # Step 2: 基础过滤
        if paper['citationCount'] < MIN_CITATIONS:
            continue
            
        # --- Step 3: 帮你自动计算 citation acceleration ---
        # 速度 = 总引用 / 发布月数
        velocity = paper['citationCount'] / months_diff
        
        # 加权分：高影响力引用权重 x 2
        score = velocity + (paper['influentialCitationCount'] * 2)

        candidates.append({
            "title": paper['title'],
            "date": paper['publicationDate'],
            "months_ago": round(months_diff, 1),
            "citations": paper['citationCount'],
            "influential": paper['influentialCitationCount'],
            "velocity": round(velocity, 2),
            "score": score,
            "url": paper['url'],
            "abstract": paper.get('abstract', 'No abstract')
        })

    # 按计算出的“加速度得分”排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:10] # 只取前10名

def generate_report(papers):
    if not papers:
        return "本周没有发现符合筛选标准（6-12个月前 + 高引用增长）的论文。"
    
    md = f"# 🚀 每周高潜力论文挖掘 ({datetime.now().strftime('%Y-%m-%d')})\n"
    md += f"**关键词**: `{KEYWORDS}` | **筛选标准**: 发布于 {MIN_MONTHS}-{MAX_MONTHS} 个月前 | 按引用加速度排序\n\n"
    
    for i, p in enumerate(papers):
        # 标题行
        md += f"### {i+1}. [{p['title']}]({p['url']})\n"
        
        # 关键指标展示
        md += f"- **🔥 引用加速度**: `{p['velocity']} 次/月`\n"
        md += f"- **📈 总引用**: {p['citations']} | **🌟 核心引用**: {p['influential']}\n"
        md += f"- **📅 发布时间**: {p['date']} (约 {p['months_ago']} 个月前)\n"
        
        # 摘要（折叠显示，保持页面整洁）
        md += "<details><summary>📖 点击展开摘要</summary>\n\n"
        md += f"{p['abstract']}\n"
        md += "\n</details>\n\n"
        md += "---\n"
    
    return md

if __name__ == "__main__":
    top_papers = fetch_and_analyze()
    report = generate_report(top_papers)
    
    # 将结果写入环境变量，供 GitHub Action 调用
    # 注意：在 Action 中如果内容太长，需要用特殊方式写入 GITHUB_OUTPUT，这里直接写入文件更稳妥
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("报告已生成。")
