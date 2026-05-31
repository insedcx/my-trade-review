import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# 1. 网页基础配置（设置高大上的宽屏模式）
st.set_page_config(page_title="量化交易智能化复盘系统", layout="wide")

FILE_NAME = "我的量化交易复盘表.xlsx"
HEADERS = ["品种", "盈亏", "时间级别", "方向", "入场价格", "出场价格", "入场时间", "出场时间", "位置与信号"]

# 2. 核心数据读取/初始化函数
def load_data():
    if not os.path.exists(FILE_NAME):
        # 初始化带表头的空DataFrame
        df = pd.DataFrame(columns=HEADERS)
        df.to_excel(FILE_NAME, index=False)
        return df
    try:
        df = pd.read_excel(FILE_NAME)
        # 确保列名没有空格
        df.columns = df.columns.str.strip()
        # 补齐缺失的列
        for h in HEADERS:
            if h not in df.columns:
                df[h] = None
        return df
    except Exception as e:
        st.error(f"读取Excel失败: {e}")
        return pd.DataFrame(columns=HEADERS)

def save_data(df):
    df.to_excel(FILE_NAME, index=False)

# 加载当前最新的历史数据
df = load_data()

# ==========================================
# 布局设计：左侧边栏 - 数据录入
# ==========================================
st.sidebar.markdown("## 📝 录入新交易流水")

with st.sidebar.form(key="trade_form", clear_on_submit=True):
    symbol = st.text_input("1. 品种", value="ETH/USDT").strip().upper()
    
    # 盈亏数字输入
    pnl = st.number_input("2. 盈亏点数 (盈利输正数，亏损输负数)", value=0.00, step=0.01, format="%.2f")
    
    time_frame = st.text_input("3. 时间级别", value="30min").strip()
    direction = st.selectbox("4. 方向", ["多", "空"])
    
    entry_p = st.number_input("5. 入场价格 (选填，不填保持0)", value=0.0, step=0.1)
    exit_p = st.number_input("6. 出场价格 (选填，不填保持0)", value=0.0, step=0.1)
    
    entry_time = st.text_input("7. 入场时间", value="2026/05/31").strip()
    exit_time = st.text_input("8. 出场时间", value="2026/05/31").strip()
    
    signal_notes = st.text_area("9. 位置与信号 (形态/入场逻辑描述)", value="").strip()
    
    submit_button = st.form_submit_button(label="🚀 提交复盘数据")

# 触发提交逻辑
if submit_button:
    # 智能纠错：如果是空头单且忘记输负号，自动帮用户转成负数
    if direction == "空" and pnl > 0:
        pnl = -pnl
        
    # 处理选填的价格
    final_entry = entry_p if entry_p != 0.0 else None
    final_exit = exit_p if exit_p != 0.0 else None
    
    # 打包成新行追加到现有表格
    new_row = {
        "品种": symbol, "盈亏": pnl, "时间级别": time_frame, "方向": direction,
        "入场价格": final_entry, "出场价格": final_exit, 
        "入场时间": entry_time, "出场时间": exit_time, "位置与信号": signal_notes
    }
    
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_data(df)
    st.sidebar.success(f"🎉 录入成功！数据已实时安全追加至Excel中。")
    # 强制网页刷新展示最新数据
    st.rerun()

# ==========================================
# 布局设计：右侧主面板 - 看板与图表
# ==========================================
st.title("📊 智能量化交易复盘数据看板")
st.markdown("---")

if df.empty or len(df) == 0:
    st.info("💡 当前表格内还没有历史数据，请在左侧边栏录入你的第一笔交易吧！")
else:
    # --- 1. 核心量化指标计算 ---
    # 清洗确保盈亏列是数值型
    df_clean = df.dropna(subset=["盈亏"]).copy()
    df_clean["盈亏"] = pd.to_numeric(df_clean["盈亏"])
    
    total_trades = len(df_clean)
    win_trades = len(df_clean[df_clean["盈亏"] > 0])
    loss_trades = len(df_clean[df_clean["盈亏"] < 0])
    
    win_rate = (win_trades / total_trades) if total_trades > 0 else 0
    total_profit = df_clean["盈亏"].sum()
    
    avg_win = df_clean[df_clean["盈亏"] > 0]["盈亏"].mean() if win_trades > 0 else 0
    avg_loss = df_clean[df_clean["盈亏"] < 0]["盈亏"].mean() if loss_trades > 0 else 0
    profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # --- 2. 网页顶部 KPI 卡片展示 ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 总交易次数", f"{total_trades} 次")
    col2.metric("🎯 综合胜率", f"{win_rate * 100:.2f} %")
    
    # 动态渲染总盈亏颜色（盈利绿，亏损红）
    if total_profit >= 0:
        col3.metric("💰 账户总净值(累计盈亏)", f"+{total_profit:.2f}", delta="盈利状态", delta_color="normal")
    else:
        col3.metric("💰 账户总净值(累计盈亏)", f"{total_profit:.2f}", delta="亏损状态", delta_color="inverse")
        
    col4.metric("⚖️ 核心盈亏比", f"{profit_loss_ratio:.2f}")

    st.markdown("### 📈 可视化统计图表")
    chart_col1, chart_col2 = st.columns(2)

    # --- 3. 图表一：动态交互式资金曲线 (Plotly) ---
    with chart_col1:
        cum_profit = df_clean["盈亏"].cumsum().tolist()
        trade_indices = list(range(1, len(cum_profit) + 1))
        
        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=trade_indices, y=cum_profit,
            mode='lines+markers',
            name='资金曲线',
            line=dict(color='#1F497D', width=3),
            marker=dict(size=8, color='#3182bd')
        ))
        fig_curve.update_layout(
            title="✨ 账户资产累计净值曲线 (Equity Curve)",
            xaxis_title="交易笔数",
            yaxis_title="累计盈亏",
            template="plotly_white",
            height=400
        )
        st.plotly_chart(fig_curve, use_container_width=True)

    # --- 4. 图表二：多空方向胜率与表现 ---
    with chart_col2:
        df_clean["结果"] = ["盈利" if x > 0 else "亏损" for x in df_clean["盈亏"]]
        
        fig_dir = px.bar(
            df_clean, x="方向", y="盈亏", color="结果",
            title="⚔️ 多空方向单笔盈亏分布对比",
            color_discrete_map={"盈利": "#A9D08E", "亏损": "#F4B183"},
            barmode="group",
            height=400
        )
        fig_dir.update_layout(template="plotly_white")
        st.plotly_chart(fig_dir, use_container_width=True)

# ==========================================
# 布局设计：底部 - 历史数据表格明细
# ==========================================
st.markdown("### 📋 历史复盘原始数据明细")
# 展示最新反转排列的表格（最新录入的在最上面，方便看）
if not df.empty:
    st.dataframe(df.iloc[::-1], use_container_width=True)
else:
    st.text("暂无明细数据")