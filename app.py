import streamlit as st
import pandas as pd
import plotly.express as px
from github import Github, Auth
import re
import os
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="PR Analyzer by Tejas P",
    page_icon="🔍",
    layout="wide"
)

# Custom Premium Styling
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #58a6ff;
    }
    .stMetric {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
        color: white;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(35, 134, 54, 0.4);
    }
    h1 {
        background: linear-gradient(90deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

def parse_rules(file_path="rules_mapping.md"):
    """
    Parses the rules_mapping.md file to extract categories and their compound keywords.
    Format expected: [Category Name]: keyword 1, keyword 2
    """
    rules = {}
    
    # Ensure we check both the root and the rules/ folder depending on where it is run
    target_path = file_path if os.path.exists(file_path) else f"rules/{file_path}"
    
    if not os.path.exists(target_path):
        st.warning(f"Could not find {target_path}. Keyword mapping will be disabled.")
        return rules
        
    with open(target_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Match the format: [Category Name]: keyword1, keyword2
            simple_match = re.match(r"\[(.*?)\]:\s*(.*)", line)
            if simple_match:
                cat = simple_match.group(1).strip()
                keywords = [k.strip().lower() for k in simple_match.group(2).split(",") if k.strip()]
                
                if cat in rules:
                    rules[cat].extend(keywords)
                else:
                    rules[cat] = keywords
                    
    # Deduplicate keywords
    for cat in rules:
        rules[cat] = list(set(rules[cat]))
        
    return rules

def extract_pr_info(url):
    """
    Extracts owner, repo, and pull number from a GitHub PR URL.
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2), int(match.group(3))
    return None, None, None

def categorize_comment(body, rules):
    if not body:
        return "General Discussion", "N/A"
    
    # 1. PRIORITY: Check for explicit Rule ID citations (e.g., A1.2, B3)
    id_match = re.search(r'\b([A-P][1-9](?:\.\d+)?)\b', body)
    if id_match:
        rule_id = id_match.group(1)
        category_map = {
            'A': 'A. Architecture', 'B': 'B. TypeScript', 'C': 'C. Naming',
            'D': 'D. Constants', 'E': 'E. UI Reuse', 'F': 'F. Styling',
            'G': 'G. API Layer', 'H': 'H. JSX Logic', 'I': 'I. Code Quality',
            'J': 'J. Utilities', 'K': 'K. Imports', 'L': 'L. Error Handling',
            'M': 'M. Performance', 'N': 'N. Security', 'O': 'O. Testing', 'P': 'P. Commits'
        }
        category_name = category_map.get(rule_id[0], "General Discussion")
        return category_name, f"Explicit Citation: {rule_id}"

    # 2. FALLBACK: Keyword Matching using rules_mapping.md
    body_lower = body.lower()
    for category, keywords in rules.items():
        for keyword in keywords:
            if keyword.lower() in body_lower:
                return category, keyword
                
    # 3. UNMATCHED: Treat as conversational
    return "General Discussion", "N/A"

def main():
    st.title("Binaried PR Comment Analyzer")
    st.markdown("### 📊 Code Review Quality & Feedback Patterns")

    # Sidebar for Authentication
    with st.sidebar:
        st.header("🔑 Authentication")
        env_token = os.getenv("GITHUB_TOKEN")
        
        # Priority: Manual Input > .env
        token_input = st.text_input("GitHub PAT", value=env_token if env_token and env_token != "your_personal_access_token_here" else "", type="password")
        
        st.markdown("---")
        st.markdown("#### About")
        st.write("This tool helps Binaried Technologies engineering leads audit PR feedback quality.")

    # Tabs for different functionalities
    tab1, tab2 = st.tabs(["Single PR Audit", "User PR Comparison"])

    # --- TAB 1: Single PR Audit ---
    with tab1:
        st.info("Input a GitHub Pull Request URL to audit review comments and categorize technical feedback.")
        user_input = st.text_input("GitHub PR URL", placeholder="https://github.com/BinariedUs/repo-name/pull/42")

        if st.button("Run Single Analysis", key="btn_tab1"):
            if not token_input:
                st.error("Please provide a GitHub Personal Access Token (PAT) in the sidebar or .env file.")
                return

            if not user_input:
                st.warning("Please enter a valid GitHub Pull Request URL.")
                return

            is_url = "github.com" in user_input
            if not is_url:
                st.error("Please enter a valid GitHub Pull Request URL.")
                return

            owner, repo_name, pr_number = extract_pr_info(user_input)
            if not owner:
                st.error("Could not parse the GitHub URL. Example format: https://github.com/owner/repo/pull/123")
                return

            try:
                with st.spinner("Analyzing PR from GitHub..."):
                    g = Github(auth=Auth.Token(token_input))
                    rules = parse_rules()
                    
                    st.info(f"Fetching PR #{pr_number} from {owner}/{repo_name}...")
                    repo = g.get_repo(f"{owner}/{repo_name}")
                    pr = repo.get_pull(pr_number)
                    
                    pr_author = pr.user.login
                    comments = pr.get_review_comments()
                    
                    data = []
                    for comment in comments:
                        if getattr(comment, 'in_reply_to_id', None):
                            continue
                        category, trigger = categorize_comment(comment.body, rules)
                        data.append({
                            "PR Number": f"PR #{pr.number}",
                            "PR Link": pr.html_url,
                            "Reviewer": comment.user.login,
                            "PR Author": pr_author,
                            "Category": category,
                            "Rule Trigger": trigger,
                            "Comment": comment.body,
                            "File": comment.path,
                            "Date": comment.created_at.strftime("%Y-%m-%d %H:%M")
                        })
                    
                    if not data:
                        issue_comments = pr.get_issue_comments()
                        for comment in issue_comments:
                            category, trigger = categorize_comment(comment.body, rules)
                            data.append({
                                "PR Number": f"PR #{pr.number}",
                                "PR Link": pr.html_url,
                                "Reviewer": comment.user.login,
                                "PR Author": pr_author,
                                "Category": category,
                                "Rule Trigger": trigger,
                                "Comment": comment.body,
                                "File": "General / Thread",
                                "Date": comment.created_at.strftime("%Y-%m-%d %H:%M")
                            })

                    if not data:
                        st.warning("No comments found in the requested Pull Request.")
                        return
                    
                    df = pd.DataFrame(data)
                    render_single_pr_dashboard(df, f"PR Analysis: *{pr.title}*", pr_number)

            except Exception as e:
                st.error(f"❌ Failed to analyze PR: {str(e)}")

    # --- TAB 2: User PR Comparison ---
    with tab2:
        st.info("Compare feedback across multiple PRs by a specific user within a timeframe.")
        col1, col2 = st.columns(2)
        with col1:
            target_username = st.text_input("Target GitHub Username", placeholder="e.g., user-binaried")
        with col2:
            target_repo = st.text_input("Target Repository", placeholder="e.g., binariedus/hn-rwa-web")
        
        import datetime
        default_start_date = datetime.date.today() - datetime.timedelta(days=30)
        since_date = st.date_input("Start Date (Since)", value=default_start_date)
        
        if st.button("Run User Comparison", key="btn_tab2"):
            if not token_input:
                st.error("Please provide a GitHub Personal Access Token (PAT).")
                return
            if not target_username or not target_repo:
                st.warning("Please provide both Target Username and Target Repository.")
                return
                
            try:
                formatted_since_date = since_date.strftime("%Y-%m-%d")
                with st.spinner(f"Searching for PRs by {target_username} in {target_repo} since {formatted_since_date}..."):
                    g = Github(auth=Auth.Token(token_input))
                    rules = parse_rules()
                    
                    query = f"repo:{target_repo} is:pr author:{target_username} created:>={formatted_since_date}"
                    
                    issues = g.search_issues(query, sort="updated", order="desc")
                    
                    data = []
                    blind_approval_list = []  # Tracks Closed/Merged PRs with 0 comments
                    awaiting_review_list = [] # Tracks Open PRs with 0 comments
                    prs_found = 0
                    
                    for issue in issues:
                        if prs_found >= 15: # Safety limit to avoid long loading times
                            break
                        try:
                            pr = issue.as_pull_request()
                            prs_found += 1
                            pr_author = pr.user.login
                            
                            comments = pr.get_review_comments()
                            pr_data = []
                            for comment in comments:
                                if getattr(comment, 'in_reply_to_id', None):
                                    continue
                                category, trigger = categorize_comment(comment.body, rules)
                                pr_data.append({
                                    "PR Number": f"PR #{pr.number}",
                                    "PR Title": pr.title,
                                    "PR Link": pr.html_url,
                                    "Reviewer": comment.user.login,
                                    "PR Author": pr_author,
                                    "Category": category,
                                    "Rule Trigger": trigger,
                                    "Comment": comment.body,
                                    "File": comment.path,
                                    "Date": comment.created_at.strftime("%Y-%m-%d %H:%M")
                                })
                                
                            if not pr_data:
                                issue_comments = pr.get_issue_comments()
                                for comment in issue_comments:
                                    category, trigger = categorize_comment(comment.body, rules)
                                    pr_data.append({
                                        "PR Number": f"PR #{pr.number}",
                                        "PR Title": pr.title,
                                        "PR Link": pr.html_url,
                                        "Reviewer": comment.user.login,
                                        "PR Author": pr_author,
                                        "Category": category,
                                        "Rule Trigger": trigger,
                                        "Comment": comment.body,
                                        "File": "General / Thread",
                                        "Date": comment.created_at.strftime("%Y-%m-%d %H:%M")
                                    })
                            
                            # --- FINAL LOGIC FOR ZERO-COMMENT PRs ---
                            if not pr_data:
                                # Create a clickable markdown link
                                pr_link = f"[PR #{pr.number}]({pr.html_url})"
                                if pr.state == 'open':
                                    awaiting_review_list.append(pr_link)
                                else:
                                    blind_approval_list.append(pr_link)
                            else:
                                data.extend(pr_data)
                                
                        except Exception as pr_e:
                            st.warning(f"Failed to process PR #{issue.number}: {pr_e}")
                            pass
                            
                    if prs_found == 0:
                        st.warning("No PRs found for this user in the specified timeframe.")
                        return
                        
                    df = pd.DataFrame(data)
                    # Pass the new lists into the dashboard function
                    render_comparison_dashboard(df, prs_found, target_username, target_repo, blind_approval_list, awaiting_review_list)
                    
            except Exception as e:
                st.error(f"❌ Failed to run comparison: {str(e)}")

def render_single_pr_dashboard(df, analysis_title, pr_number):
    """Renders the dashboard for a single PR audit."""
    st.markdown(f"#### 📈 {analysis_title}")
    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
    mcol1.metric("Total Feedback", len(df))
    mcol2.metric("Reviewers", df['Reviewer'].nunique())
    top_cat = df['Category'].mode()[0] if not df.empty else "N/A"
    mcol3.metric("Primary Category", top_cat)
    
    nitpick_count = len(df[df['Category'] == 'Nitpick'])
    nitpick_ratio = (nitpick_count / len(df)) * 100 if len(df) > 0 else 0
    mcol4.metric("Nitpick Ratio", f"{nitpick_ratio:.1f}%")
    
    st.markdown("---")

    st.markdown("#### 📊 Feedback Distribution")
    vcol1, vcol2 = st.columns(2)
    with vcol1:
        st.write("**Activity by Reviewer**")
        author_counts = df['Reviewer'].value_counts().reset_index()
        author_counts.columns = ['Reviewer', 'Count']
        st.bar_chart(author_counts.set_index('Reviewer'))

    with vcol2:
        st.write("**Categorized Impact**")
        cat_counts = df['Category'].value_counts().reset_index()
        cat_counts.columns = ['Category', 'Count']
        st.bar_chart(cat_counts.set_index('Category'))

    st.markdown("---")

    st.markdown("#### 🔍 Categorized Comments Detail")
    st.dataframe(
        df, 
        column_config={
            "Comment": st.column_config.TextColumn("Comment Content", width="large"),
            "File": st.column_config.TextColumn("File Path", width="medium"),
            "PR Link": st.column_config.LinkColumn("PR Link", width="small"),
            "Reviewer": st.column_config.TextColumn("Reviewer"),
            "Rule Trigger": st.column_config.TextColumn("Standard Violated", help="The specific pattern from rules.md that was triggered"),
        },
        width="stretch",
        hide_index=True
    )
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Analysis Report (CSV)", 
        csv, 
        f"pr_analysis_{pr_number}.csv", 
        "text/csv",
        key='dl_single'
    )


def render_comparison_dashboard(df, total_prs_found, username, repo, blind_approval_list, awaiting_review_list):
    """Renders the dashboard for multiple PRs by a specific user."""
    st.markdown(f"#### 📈 Comparison: `{username}` in `{repo}`")
    
    # Calculate exact numbers
    prs_with_feedback = df['PR Number'].nunique() if not df.empty else 0
    zero_comment_count = len(blind_approval_list) + len(awaiting_review_list)
    
    # 4-Column Metrics Layout
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Total PRs Evaluated", total_prs_found)
    mcol2.metric("PRs w/ Feedback", prs_with_feedback)
    mcol3.metric("Zero-Comment PRs", zero_comment_count)

    # --- UI ALERTS FOR ZERO-COMMENT PRs ---
    if blind_approval_list:
        st.warning(f"🚨 **Blind Approvals Detected:** The following PRs were closed or merged with ZERO technical feedback: {', '.join(blind_approval_list)}")
        
    if awaiting_review_list:
        st.info(f"⏳ **Awaiting Review:** The following PRs are currently OPEN and have not received any feedback yet: {', '.join(awaiting_review_list)}")

    if df.empty:
        mcol4.metric("Avg Feedback per PR", "0")
        st.info("No feedback comments found across these PRs.")
        return

    # Calculate average based ONLY on PRs that got feedback
    avg_comments = len(df) / prs_with_feedback
    mcol4.metric("Avg Feedback per PR", f"{avg_comments:.1f}")

    st.markdown("---")

    st.markdown("#### 📊 Comparison Visualizations")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Category Breakdown per PR (Stacked)**")
        chart_data = df.groupby(['PR Number', 'Category']).size().reset_index(name='Comment Count')
        fig = px.bar(chart_data, x='PR Number', y='Comment Count', color='Category', barmode='stack')
        fig.update_layout(legend=dict(yanchor="top", xanchor="left", y=1, x=1.02))
        st.plotly_chart(fig, width="stretch")
        
    with col2:
        st.write("**Reviewer Participation Matrix (Heatmap)**")
        # index=Reviewer, columns=PR Number
        rev_data = df.groupby(['Reviewer', 'PR Number']).size().unstack(fill_value=0)
        st.dataframe(rev_data.style.background_gradient(cmap='Blues'), width="stretch")

    st.markdown("---")
    st.markdown("#### 🔍 Aggregated Comments Detail")
    
    st.dataframe(
        df, 
        column_config={
            "PR Number": st.column_config.TextColumn("PR", width="small"),
            "Comment": st.column_config.TextColumn("Comment Content", width="large"),
            "File": st.column_config.TextColumn("File Path", width="medium"),
            "Reviewer": st.column_config.TextColumn("Reviewer"),
            "PR Link": st.column_config.LinkColumn("GitHub Link", width="small"),
        },
        width="stretch",
        hide_index=True
    )
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Comparison Report (CSV)", 
        csv, 
        f"pr_comparison_{username}.csv", 
        "text/csv",
        key='dl_comp'
    )

if __name__ == "__main__":
    main()
