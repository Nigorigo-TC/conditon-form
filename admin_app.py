import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Supabase 接続情報 ---
SUPABASE_URL = st.secrets["supabase_url"]
SUPABASE_KEY = st.secrets["supabase_key"]
TABLE_NAME = "condition"

# --- Googleスプレッドシート情報 ---
SPREADSHEET_NAME = "2025年度_起床時コンディションチェック（実業団・NF）"
SHEET_NAME = "condition2025"

# --- Supabaseから未出力データ取得 ---
def fetch_unexported_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?exported=eq.false&select=*"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

# --- Supabaseのexported=trueに更新 ---
def mark_as_exported(ids):
    if not ids:
        return
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    for record_id in ids:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?id=eq.{record_id}"
        res = requests.patch(url, headers=headers, json={"exported": True})
        res.raise_for_status()

# --- Googleスプレッドシート出力 ---
def export_to_gsheet(df: pd.DataFrame):
    df = df.fillna("")

    # Supabase側の管理用カラムは除外（必要に応じて調整）
    drop_cols = [c for c in ["id", "created_at", "updated_at", "exported"] if c in df.columns]
    df_out = df.drop(columns=drop_cols, errors="ignore")

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = st.secrets["google_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_NAME)

    existing_data = sheet.get_all_values()
    if not existing_data:
        # ヘッダーが無い場合はカラム名を1行目に入れる
        sheet.insert_row(df_out.columns.tolist(), 1)

    sheet.append_rows(df_out.values.tolist())

# ========================
# Streamlit UI
# ========================

st.title("🛠 コンディション管理（Supabase → スプレッドシート）")

admin_pass = st.text_input("管理者パスワードを入力", type="password")

if admin_pass == st.secrets.get("admin_password"):
    st.success("管理者ログインOKです。")

    if st.button("📤 未出力データをスプレッドシートへ出力"):
        df = fetch_unexported_data()
        if df.empty:
            st.warning("未出力データはありません。")
        else:
            export_to_gsheet(df)
            mark_as_exported(df["id"].tolist())
            st.success(f"✅ {len(df)} 件のデータを出力し、exported=true に更新しました。")
else:
    if admin_pass:
        st.error("パスワードが間違っています。")
    st.info("管理者パスワードを入力してください。")
