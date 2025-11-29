import requests
import os
from datetime import datetime
import math

# === 配置项 ===
KEYWORDS = os.environ.get("KEYWORDS", "Large Language Models") 
# 时间窗：6 - 12 个月
MIN_MONTHS = 6  
MAX_MONTHS = 13 # 稍微放宽一点上限，防止因为刚好过了一年被切掉
# 基础门槛：降低到 1，确保至少能抓到东西，哪怕是刚起步的
MIN_CITATIONS = 1 

def fetch_and_analyze():
    print(f"🔍 正在检索关键词: {KEYWORDS}...")
    
    current_year = datetime.now().year
    # 扩大检索范围，确保不漏掉
    year_range = f"{current_year-2}-{current_year}"
    
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": KEYWORDS,
        "year": year_range,
        "limit": 100,
        # 🔥 关键修改：按引用量降序获取，而不是按相关性
        # 这样能保证取回来的都是引用高的，而不是刚发的
        "sort": "citationCount:desc", 
        "fields": "title,publicationDate,citationCount,influentialCitationCount,abstract,url,authors"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json().get('data', [])
        print(f"📡 API 返回了 {len(data)} 篇原始论文，正在进行时间窗过滤...")
    except Exception as e:
        print(f"API Error: {e}")
        return []

    candidates = []
    current_date = datetime.now()

    for paper in data:
        # 数据清洗：没有日期的跳过
        if not paper.get('publicationDate'): continue
        
        try:
            pub_date = datetime.strptime(paper['publicationDate'], "%Y-%m-%d")
        except:
            continue
            
        days_diff = (current_date - pub_date).days
        months_diff = days_diff / 30.0
        
        # 调试信息：你可以看到脚本实际上在看哪些论文（只在Log里显示）
        # print(f"Checking: {paper['title'][:30]}... ({months_diff:.1f} months ago, {paper['citationCount']} cites)")

        # Step 1: 时间窗筛选 (6-13个月)
        if not (MIN_MONTHS <= months_diff <= MAX_MONTHS):
            continue
            
        # Step 2: 基础过滤 (引用数 >= 1)
        if paper['citationCount'] < MIN_CITATIONS:
            continue
            
        # Step 3: 计算加速度
        velocity = paper['citationCount'] / months_diff
        
        # 加权分
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

    # 按分数排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    print(f"✅ 筛选后剩余 {len(candidates)} 篇符合条件的论文")
    return candidates[:10]

def generate_report(papers):
    # 如果还是没找到，生成一个带有调试信息的空报告
    if not papers:
        return (f"# ⚠️ 本周未发现符合标准的论文\n\n"
                f"**当前设置**:\n"
                f"- 关键词: `{KEYWORDS}`\n"
                f"- 时间窗: {MIN_MONTHS}-{MAX_MONTHS} 个月前\n"
                f"- 最低引用: {MIN_CITATIONS}\n\n"
                f"**可能原因**: 该领域在指定时间段内（约一年前）没有高引用爆发的论文，或者API未能获取到数据。\n"
                f"建议：尝试在 main.py 中将 MIN_MONTHS 改为 3，或更换关键词测试。")
    
    md = f"# 🚀 每周高潜力论文挖掘 ({datetime.now().strftime('%Y-%m-%d')})\n"
    md += f"**关键词**: `{KEYWORDS}` | **筛选标准**: 发布于 {MIN_MONTHS}-{MAX_MONTHS} 个月前 | 按引用加速度排序\n\n"
    
    for i, p in enumerate(papers):
        md += f"### {i+1}. [{p['title']}]({p['url']})\n"
        md += f"- **🔥 引用加速度**: `{p['velocity']} 次/月`\n"
        md += f"- **📈 总引用**: {p['citations']} | **🌟 核心引用**: {p['influential']}\n"
        md += f"- **📅 发布时间**: {p['date']} (约 {p['months_ago']} 个月前)\n"
        md += "<details><summary>📖 点击展开摘要</summary>\n\n"
        md += f"{p['abstract']}\n"
        md += "\n</details>\n\n"
        md += "---\n"
    
    return md

if __name__ == "__main__":
    top_papers = fetch_and_analyze()
    report = generate_report(top_papers)
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("报告已生成。")
