import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import json
import os
from hashlib import sha256
import base64
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from PIL import Image
import io


# ---- Configuration ----
st.set_page_config(page_title="物流最適化システム", layout="wide")

# ---- Data Storage Functions ----
def save_user_data(username, password_hash):
    if not os.path.exists("user_data.json"):
        with open("user_data.json", "w") as f:
            json.dump({}, f)
            
    with open("user_data.json", "r") as f:
        users = json.load(f)
    
    users[username] = {
        "password_hash": password_hash,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open("user_data.json", "w") as f:
        json.dump(users, f)

def save_shipment_request(data):
    if not os.path.exists("shipment_data.json"):
        with open("shipment_data.json", "w") as f:
            json.dump([], f)
            
    with open("shipment_data.json", "r") as f:
        shipments = json.load(f)
    
    # Generate unique ID
    shipment_id = str(len(shipments) + 1).zfill(5)
    data["id"] = shipment_id
    data["status"] = "pending"
    data["created_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add deadline
    deadline = datetime.datetime.now() + datetime.timedelta(hours=24)
    data["deadline"] = deadline.strftime("%Y-%m-%d %H:%M:%S")
    
    shipments.append(data)
    
    with open("shipment_data.json", "w") as f:
        json.dump(shipments, f)
    
    return shipment_id

def get_all_shipments():
    if not os.path.exists("shipment_data.json"):
        return []
        
    with open("shipment_data.json", "r") as f:
        shipments = json.load(f)
    
    return shipments

def authenticate_user(username, password):
    if not os.path.exists("user_data.json"):
        return False
        
    with open("user_data.json", "r") as f:
        users = json.load(f)
    
    if username not in users:
        return False
    
    password_hash = sha256(password.encode()).hexdigest()
    return users[username]["password_hash"] == password_hash

def update_shipment_status():
    """Update shipment status based on time and load criteria"""
    if not os.path.exists("shipment_data.json"):
        return
        
    with open("shipment_data.json", "r") as f:
        shipments = json.load(f)
    
    current_time = datetime.datetime.now()
    pending_items = [s for s in shipments if s["status"] == "pending"]
    
    # Group by destination region
    regions = {}
    for item in pending_items:
        region = item["address"][:2]  # First two characters of address as region
        if region not in regions:
            regions[region] = []
        regions[region].append(item)
    
    updated = False
    
    # Check each region for load optimization
    for region, items in regions.items():
        # Calculate total items in this region
        total_items = sum(int(item["quantity"]) for item in items)
        
        # Check if we have enough items to meet minimum load (70% capacity - assuming 100 items is full)
        if total_items >= 70:
            updated = True
            for item in items:
                idx = shipments.index(item)
                shipments[idx]["status"] = "shipping"
                shipments[idx]["updated_at"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Check for deadline
            for item in items:
                deadline = datetime.datetime.strptime(item["deadline"], "%Y-%m-%d %H:%M:%S")
                if current_time > deadline:
                    idx = shipments.index(item)
                    shipments[idx]["status"] = "shipping"
                    shipments[idx]["updated_at"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
                    updated = True
    
    if updated:
        with open("shipment_data.json", "w") as f:
            json.dump(shipments, f)

# ---- Helper Functions ----
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def get_load_efficiency_by_region():
    shipments = get_all_shipments()
    pending_items = [s for s in shipments if s["status"] == "pending"]
    
    regions = {}
    for item in pending_items:
        region = item["address"][:2]
        if region not in regions:
            regions[region] = 0
        regions[region] += int(item["quantity"])
    
    result = []
    for region, total_items in regions.items():
        efficiency = min(total_items / 100, 1.0)  # Assuming 100 items is full capacity
        result.append({
            "region": region,
            "efficiency": efficiency,
            "items": total_items
        })
    
    return result

def create_load_efficiency_chart():
    efficiency_data = get_load_efficiency_by_region()
    
    if not efficiency_data:
        return None
    
    regions = [item["region"] for item in efficiency_data]
    efficiency = [item["efficiency"] * 100 for item in efficiency_data]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = cm.Blues(np.array(efficiency) / 100)
    bars = ax.bar(regions, efficiency, color=colors)
    
    ax.set_xlabel('地域')
    ax.set_ylabel('積載率 (%)')
    ax.set_title('地域別積載率状況')
    ax.set_ylim(0, 100)
    
    # Add efficiency value on top of bars
    for bar, eff in zip(bars, efficiency):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{eff:.1f}%', ha='center', va='bottom')
    
    # Draw threshold line at 70%
    ax.axhline(y=70, color='r', linestyle='--', alpha=0.7)
    ax.text(0, 71, '最小積載率基準(70%)', color='r')
    
    # Convert plot to image
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return buf

# ---- UI Components ----
def login_page():
    st.title("物流最適化システム - ログイン")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("ログイン")
        username = st.text_input("ユーザー名", key="login_username")
        password = st.text_input("パスワード", type="password", key="login_password")
        
        if st.button("ログイン"):
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("ログインに成功しました！")
                st.experimental_rerun()
            else:
                st.error("ユーザー名またはパスワードが間違っています")
    
    with col2:
        st.subheader("新規登録")
        new_username = st.text_input("ユーザー名", key="register_username")
        new_password = st.text_input("パスワード", type="password", key="register_password")
        confirm_password = st.text_input("パスワード（確認）", type="password")
        
        if st.button("登録"):
            if not new_username or not new_password:
                st.error("ユーザー名とパスワードを入力してください")
            elif new_password != confirm_password:
                st.error("パスワードが一致しません")
            else:
                password_hash = hash_password(new_password)
                save_user_data(new_username, password_hash)
                st.success("アカウントが作成されました！ログインしてください")

def main_dashboard():
    # Update shipment status based on criteria
    update_shipment_status()
    
    st.title("物流最適化システム")
    st.write(f"ようこそ, {st.session_state.username}さん!")
    
    # Sidebar with navigation
    with st.sidebar:
        st.subheader("メニュー")
        page = st.radio("", ["ダッシュボード", "配送依頼", "配送状況"])
        
        if st.button("ログアウト"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.experimental_rerun()
    
    if page == "ダッシュボード":
        show_dashboard()
    elif page == "配送依頼":
        show_shipment_request_form()
    elif page == "配送状況":
        show_shipment_status()

def show_dashboard():
    st.header("ダッシュボード")
    
    # Summary stats
    shipments = get_all_shipments()
    pending_count = len([s for s in shipments if s["status"] == "pending"])
    shipping_count = len([s for s in shipments if s["status"] == "shipping"])
    
    # Calculate total items and load efficiency
    total_pending_items = sum(int(s["quantity"]) for s in shipments if s["status"] == "pending")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("配送保留中", f"{pending_count}件")
    with col2:
        st.metric("配送中", f"{shipping_count}件")
    with col3:
        st.metric("保留中の総商品数", f"{total_pending_items}個")
    
    # Load efficiency chart
    st.subheader("地域別積載率状況")
    efficiency_chart = create_load_efficiency_chart()
    
    if efficiency_chart:
        st.image(efficiency_chart)
    else:
        st.info("現在、配送待ちの注文はありません")
    
    # Recent shipment requests
    st.subheader("最近の配送依頼")
    
    if shipments:
        recent_shipments = sorted(shipments, key=lambda x: x["created_at"], reverse=True)[:5]
        
        for shipment in recent_shipments:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**ID:** {shipment['id']} - **{shipment['name']}**")
                st.write(f"品目: {shipment['category']} ({shipment['quantity']}個)")
            with col2:
                st.write(f"配送先: {shipment['address']}")
                st.write(f"依頼日: {shipment['created_at'][:10]}")
            with col3:
                status_color = "orange" if shipment["status"] == "pending" else "green"
                status_label = "配送保留中" if shipment["status"] == "pending" else "配送中"
                st.markdown(f"<span style='color:{status_color};font-weight:bold'>{status_label}</span>", unsafe_allow_html=True)
            
            st.markdown("---")
    else:
        st.info("配送依頼はまだありません")

def show_shipment_request_form():
    st.header("配送依頼フォーム")
    
    with st.form("shipment_request_form"):
        name = st.text_input("名前")
        address = st.text_input("住所")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("商品カテゴリ", ["電子機器", "衣類", "食品", "家具", "書籍", "その他"])
        with col2:
            quantity = st.number_input("数量", min_value=1, value=1)
        
        additional_info = st.text_area("備考", height=100)
        
        submitted = st.form_submit_button("配送依頼を送信")
        
        if submitted:
            if not name or not address:
                st.error("名前と住所は必須です")
            else:
                shipment_data = {
                    "name": name,
                    "address": address,
                    "category": category,
                    "quantity": str(quantity),
                    "additional_info": additional_info,
                    "requester": st.session_state.username
                }
                
                shipment_id = save_shipment_request(shipment_data)
                st.success(f"配送依頼が送信されました！ (ID: {shipment_id})")
                st.info("注意: 積載率が70%に達するまで、または24時間が経過するまで配送は保留されます")

def show_shipment_status():
    st.header("配送状況")
    
    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.selectbox("ステータスでフィルタ", ["すべて", "配送保留中", "配送中"])
    with filter_col2:
        region_filter = st.text_input("地域でフィルタ (住所の先頭2文字)")
    
    shipments = get_all_shipments()
    
    # Apply filters
    if status_filter == "配送保留中":
        shipments = [s for s in shipments if s["status"] == "pending"]
    elif status_filter == "配送中":
        shipments = [s for s in shipments if s["status"] == "shipping"]
    
    if region_filter:
        shipments = [s for s in shipments if s["address"].startswith(region_filter)]
    
    # Show efficiency info
    efficiency_data = get_load_efficiency_by_region()
    if efficiency_data:
        st.subheader("積載率情報")
        eff_cols = st.columns(len(efficiency_data))
        
        for idx, data in enumerate(efficiency_data):
            with eff_cols[idx]:
                eff_percentage = data["efficiency"] * 100
                color = "red" if eff_percentage < 70 else "green"
                st.markdown(f"**{data['region']}**: <span style='color:{color}'>{eff_percentage:.1f}%</span>", unsafe_allow_html=True)
                st.progress(data["efficiency"])
                st.write(f"必要数: {max(0, 70 - data['items'])}個")
    
    # Display shipments
    if shipments:
        st.subheader("配送一覧")
        
        for shipment in shipments:
            col1, col2, col3, col4 = st.columns([1.5, 1, 1, 0.5])
            
            with col1:
                st.write(f"**ID:** {shipment['id']}")
                st.write(f"**依頼者:** {shipment['requester']}")
                st.write(f"**名前:** {shipment['name']}")
            
            with col2:
                st.write(f"**カテゴリ:** {shipment['category']}")
                st.write(f"**数量:** {shipment['quantity']}個")
                st.write(f"**住所:** {shipment['address']}")
            
            with col3:
                created_date = datetime.datetime.strptime(shipment['created_at'], "%Y-%m-%d %H:%M:%S")
                deadline_date = datetime.datetime.strptime(shipment['deadline'], "%Y-%m-%d %H:%M:%S")
                remaining_time = deadline_date - datetime.datetime.now()
                
                st.write(f"**依頼日:** {created_date.strftime('%Y-%m-%d')}")
                
                if shipment["status"] == "pending" and remaining_time.total_seconds() > 0:
                    hours, remainder = divmod(remaining_time.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    st.write(f"**期限まで:** {int(hours)}時間{int(minutes)}分")
                elif shipment["status"] == "pending":
                    st.write("**期限:** 期限切れ (間もなく配送)")
                else:
                    st.write("**配送中**")
            
            with col4:
                status_color = "orange" if shipment["status"] == "pending" else "green"
                status_label = "配送保留中" if shipment["status"] == "pending" else "配送中"
                st.markdown(f"<div style='background-color:{status_color};color:white;padding:10px;border-radius:5px;text-align:center'>{status_label}</div>", unsafe_allow_html=True)
            
            st.markdown("---")
    else:
        st.info("該当する配送依頼はありません")

# ---- Main App Logic ----
def main():
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if "username" not in st.session_state:
        st.session_state.username = None
    
    # CSS styling
    st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    h1, h2, h3 {
        color: #1e3c72;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Render appropriate page
    if st.session_state.logged_in:
        main_dashboard()
    else:
        login_page()

if __name__ == "__main__":
    main()
