import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from matplotlib.patches import Patch
from matplotlib import colormaps
import textwrap

# === Task List with Collective Additions ===
tasks = sorted([
    # Existing tasks
    ("Barkın Saday", "Scraping External News Sources", datetime(2024, 12, 2), datetime(2025, 4, 30)),
    ("Zeynep Doğa Dellal", "News Objectification with LLMs", datetime(2024, 12, 2), datetime(2025, 4, 30)),
    ("Zeynep Doğa Dellal", "Register/Login + Social Auth (Backend)", datetime(2025, 2, 22), datetime(2025, 3, 5)),
    ("Zeynep Doğa Dellal", "Core Article Feed (Frontend + API)", datetime(2025, 3, 5), datetime(2025, 3, 20)),
    ("Zeynep Doğa Dellal", "AI Summarization of Articles", datetime(2025, 3, 15), datetime(2025, 4, 5)),
    ("Barkın Saday", "Cleaning & Validating News Data", datetime(2025, 3, 20), datetime(2025, 4, 10)),
    ("Zeynep Doğa Dellal", "Social Timeline & Friends Feed", datetime(2025, 3, 25), datetime(2025, 4, 11)),
    ("Mithat Emre Gürbüz", "Bug Fixes", datetime(2025, 4, 5), datetime(2025, 4, 30)),
    ("Yusuf Özyer", "Bug Fixes", datetime(2025, 4, 5), datetime(2025, 4, 30)),
    ("Mithat Emre Gürbüz", "UI for Notification & Settings", datetime(2025, 4, 22), datetime(2025, 4, 25)),
    ("Mithat Emre Gürbüz", "UI for Email/Password Auth", datetime(2025, 4, 22), datetime(2025, 4, 26)),
    ("Mithat Emre Gürbüz", "UI for Password Reset & Delete Account", datetime(2025, 4, 26), datetime(2025, 5, 2)),
    ("Barkın Saday", "Structuring News Schema", datetime(2025, 4, 10), datetime(2025, 4, 18)),
    ("Yağız Berk Uyar", "Category Timeline UI", datetime(2025, 4, 10), datetime(2025, 4, 10)),
    ("Barkın Saday", "Matching and Image Processing", datetime(2025, 4, 19), datetime(2025, 4, 22)),
    ("Zeynep Doğa Dellal", "Recommendation Ranking", datetime(2025, 4, 17), datetime(2025, 4, 30)),
    ("Zeynep Doğa Dellal", "Privacy Settings (Backend)", datetime(2025, 4, 22), datetime(2025, 4, 22)),
    ("Yağız Berk Uyar", "Scheduling Scraper Updates", datetime(2025, 4, 25), datetime(2025, 4, 26)),
    ("Yağız Berk Uyar", "Matching Pipeline Orchestration", datetime(2025, 4, 27), datetime(2025, 4, 30)),
    ("Zeynep Doğa Dellal", "Prioritization Engine", datetime(2025, 4, 30), datetime(2025, 5, 1)),
    ("Mithat Emre Gürbüz", "Premium Membership + Offline Access", datetime(2025, 5, 2), datetime(2025, 5, 10)),
    ("Mithat Emre Gürbüz", "Report Article or Bug", datetime(2025, 5, 2), datetime(2025, 5, 5)),
    ("Zeynep Doğa Dellal", "Direct Messaging & Sharing", datetime(2025, 5, 5), datetime(2025, 5, 14)),
    ("Zeynep Doğa Dellal", "Location-Based News Delivery", datetime(2025, 5, 5), datetime(2025, 5, 12)),
    ("Barkın Saday", "Push Notification Control", datetime(2025, 5, 5), datetime(2025, 5, 10)),
    ("Zeynep Doğa Dellal", "Fake News Detection & Reporting", datetime(2025, 5, 2), datetime(2025, 5, 9)),
    ("Zeynep Doğa Dellal", "Analytics + Trend Tracking", datetime(2025, 5, 6), datetime(2025, 5, 13)),
    ("Barkın Saday", "Admin Dashboard + Tools", datetime(2025, 5, 5), datetime(2025, 5, 14)),
    ("Yağız Berk Uyar", "Custom News Preferences", datetime(2025, 5, 8), datetime(2025, 5, 14)),
    ("Yağız Berk Uyar", "News De-duplication Logic", datetime(2025, 5, 8), datetime(2025, 5, 15)),

    # Collective team tasks (represented by Yusuf)
    ("Collective", "Market Research & Feature Benchmarking", datetime(2025, 4, 20), datetime(2025, 4, 26)),
    ("Collective", "Copyright / Licensing Compliance", datetime(2025, 4, 26), datetime(2025, 5, 2)),
    ("Collective", "User Testing & Feedback Evaluation", datetime(2025, 4, 28), datetime(2025, 5, 5)),
    ("Collective", "Final Quality Assurance (System-wide)", datetime(2025, 5, 3), datetime(2025, 5, 9)),
    ("Collective", "Demo Prep & Delivery", datetime(2025, 5, 6), datetime(2025, 5, 12)),
], key=lambda x: x[2])

# === Color Mapping by Contributor ===
contributors = sorted(set([t[0] for t in tasks]))
custom_colors = {
    "Zeynep Doğa Dellal": "#1f77b4",
    "Barkın Saday": "#ff7f0e",
    "Mithat Emre Gürbüz": "#2ca02c",
    "Yağız Berk Uyar": "#d62728",
    "Collective": "#9467bd",
    "Yusuf Özyer": "#8c564b",
}
color_map = {name: custom_colors.get(name, 'gray') for name in contributors}

# === Plot Setup ===
fig, ax = plt.subplots(figsize=(28, len(tasks) * 0.45 + 2))
min_duration_days = 7  # Ensure short tasks are visible

# === Plot Tasks with Duration Normalization
for i, (person, task_name, start, end) in enumerate(tasks):
    actual_duration = (end - start).days or 1
    display_duration = max(actual_duration, min_duration_days)

    ax.barh(i, display_duration, left=start, color=color_map[person])
    short_label = task_name

    if actual_duration >= min_duration_days:
        ax.text(start + timedelta(days=display_duration / 2), i, short_label,
                va='center', ha='center', color='white', fontsize=7, fontweight='bold')
    else:
        ax.text(start + timedelta(days=0.2), i, short_label,
                va='center', ha='left', color='white', fontsize=7, fontweight='bold')

# === Y-axis Label Wrapping ===
wrapped_labels = [textwrap.fill(task_name, width=45) for _, task_name, _, _ in tasks]
ax.set_yticks(range(len(tasks)))
ax.set_yticklabels(wrapped_labels, fontsize=9)
ax.invert_yaxis()

# === X-axis Date Formatting ===
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.xticks(rotation=45)
ax.grid(True, which='major', axis='x', linestyle='--', linewidth=0.5)

# === Milestones ===
milestones = [
    (datetime(2025, 3, 10, 10, 0), "Detailed Design Report"),
    (datetime(2025, 5, 2, 10, 0), "Final Report"),
    (datetime(2025, 5, 5), "Presentation Start"),
]
for date, label in milestones:
    ax.axvline(date, color='magenta', linestyle='--', linewidth=1)
    ax.text(date, len(tasks) + 0.5, label, rotation=90, va='bottom', color='magenta', fontsize=8)

# === Labels & Legend ===
ax.set_xlabel('Timeline', fontsize=12)
ax.set_title('VeritasNews Project Gantt Chart', fontsize=10, fontweight='bold', pad=20)
legend_elements = [Patch(facecolor=color_map[c], label=c) for c in contributors]
ax.legend(handles=legend_elements, title='Contributors', bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=9)

# Set X-axis range
ax.set_xlim(left=datetime(2025, 1, 15), right=datetime(2025, 5, 16))

plt.tight_layout()
plt.savefig('veritasnews_gantt_final.png', dpi=300, bbox_inches='tight')
plt.show()
