import streamlit as st
import os
import shutil
import json
import datetime
import time
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import streamlit.components.v1 as components

# LlamaIndex & Ollama
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter


# --- 0. ページ設定 ---
st.set_page_config(page_title="Closed-Book", page_icon="⚡", layout="wide")

# --- 1. 認証機能 ---
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

with open(config_path) as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 現在の状態をチェック
authentication_status = st.session_state.get('authentication_status')

if authentication_status is not True:
    tab1, tab2 = st.tabs(["ログイン", "新規ユーザー登録"])

    with tab1:
        authenticator.login(key='login_form')
        if st.session_state.get('authentication_status') is False:
            st.error('ユーザー名かパスワードが間違っています')

    with tab2:
        st.subheader("新しいアカウントを作成")
        
        # 入力欄を整える
        new_user = st.text_input("希望するユーザー名", key="reg_user")
        new_email = st.text_input("メールアドレス", key="reg_email")
        new_pw = st.text_input("パスワード", type="password", key="reg_pw")
        new_pw_confirm = st.text_input("パスワード（確認用）", type="password", key="reg_pw_conf")

        if st.button("この内容で登録する", use_container_width=True):
            # 1. バリデーション（入力チェック）
            if not new_user.isalnum():
                st.error("ユーザー名は英数字だけで入力してね。")
            elif "@" not in new_email or "." not in new_email: # ★簡易メアドチェック
                st.error("正しいメールアドレスを入力してね。")
            elif not new_user or not new_pw or not new_email:
                st.error("すべての項目を入力してね。")
            elif new_pw != new_pw_confirm:
                st.error("パスワードが一致しないよ！")
            elif new_user in config['credentials']['usernames']:
                st.error("そのユーザー名はもう使われてるよ。")
            
            # 2. すべてOKなら登録
            else:
                hashed_pw = stauth.Hasher.hash(new_pw)
                config['credentials']['usernames'][new_user] = {
                    'email': new_email, # ★入力されたメアドを保存
                    'name': new_user,
                    'password': hashed_pw
                }
                
                # YAMLにきれいに書き込み
                with open(config_path, 'w') as file:
                    yaml.dump(
                        config, 
                        file, 
                        default_flow_style=False, 
                        sort_keys=False, 
                        indent=4
                    )
                
                st.success(f"ユーザー「{new_user}」を登録したよ！ログインタブからログインしてね。")
    
    st.stop()

# --- 成功後の処理 (ログイン成功時のみここを通る) ---
name = st.session_state.get('name')
username = st.session_state.get('username')


# ... 以下、ディレクトリ作成の処理へ続く ...
# ログイン成功後の処理

# ログインしたユーザー名を使ってフォルダを分ける
user_id = username
# configからemailを取得（構造が変わったときのエラー回避を入れる）
try:
    user_email = config['credentials']['usernames'][username]['email']
except:
    user_email = "unknown@example.com"

# --- 2. 基本設定 ---
OLLAMA_URL = "http://ollama:11434"
DATA_DIR = os.path.join("/data", user_id)
PERSIST_DIR = os.path.join("/app/storage", user_id)
CHAT_LOG_DIR = os.path.join(PERSIST_DIR, "chat_history")

os.makedirs(CHAT_LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# モデル設定
Settings.llm = Ollama(model="gpt-oss:20b", base_url=OLLAMA_URL, request_timeout=600.0)
Settings.embed_model = OllamaEmbedding(model_name="nomic-embed-text:latest", base_url=OLLAMA_URL)

# --- 3. ユーティリティ関数 ---
def save_chat(chat_id, messages, selected_files):
    title = chat_id
    for msg in messages:
        if msg["role"] == "user":
            title = msg["content"][:15] + ("..." if len(msg["content"]) > 15 else "")
            break
    data = {"title": title, "messages": messages, "selected_files": selected_files}
    with open(os.path.join(CHAT_LOG_DIR, f"{chat_id}.json"), "w") as f:
        json.dump(data, f, ensure_ascii=False)

def list_chats():
    if not os.path.exists(CHAT_LOG_DIR):
        return []
    files = os.listdir(CHAT_LOG_DIR)
    chat_list = []
    for f in files:
        if f.endswith(".json"):
            chat_id = f.replace(".json", "")
            try:
                with open(os.path.join(CHAT_LOG_DIR, f), "r") as j:
                    data = json.load(j)
                    title = data.get("title", chat_id) if isinstance(data, dict) else chat_id
                    chat_list.append({"id": chat_id, "title": title})
            except:
                continue
    return sorted(chat_list, key=lambda x: x["id"], reverse=True)

@st.cache_resource(show_spinner=False)
def get_index(file_list):
    if not file_list: return None

    if os.path.exists(os.path.join(PERSIST_DIR, "docstore.json")):
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        index = load_index_from_storage(storage_context)
    else:
        index = VectorStoreIndex.from_documents([])

    input_files = [os.path.join(DATA_DIR, f) for f in file_list]
    documents = SimpleDirectoryReader(input_files=input_files).load_data()
    refreshed_docs = index.refresh_ref_docs(documents)

    if any(refreshed_docs):
        index.storage_context.persist(persist_dir=PERSIST_DIR)

    return index

# --- 4. セッション状態 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "pending_task_prompt" not in st.session_state:
    st.session_state.pending_task_prompt = None

# --- 5. サイドバー ---
with st.sidebar:
    st.write(f"👤 ログイン中: **{name}**")
    authenticator.logout('ログアウト', 'sidebar')
    st.divider()

    st.title("📂 PDF管理")
    is_locked = st.session_state.get("is_processing", False)

    uploaded_files = st.file_uploader(
        "ファイルを追加",
        type=["pdf", "txt", "docx", "xlsx"],
        accept_multiple_files=True,
        key="my_uploader",
        disabled=is_locked
    )
    if uploaded_files:
        for f in uploaded_files:
            with open(os.path.join(DATA_DIR, f.name), "wb") as buffer:
                buffer.write(f.getbuffer())

        st.success(f"{len(uploaded_files)}個のファイルを保存しました。2秒後にリロードします... ⏳")
        del st.session_state["my_uploader"]

        # JavaScriptを埋め込む
        components.html(
            """
            <script>
                // 念のためコンソールにも出す
                console.log("2秒後にリロードします");
                setTimeout(function(){
                    window.parent.location.reload();
                }, 2000);
            </script>
            """,
            height=0,
            width=0
        )


        st.stop()

    st.divider()

    target_exts = (".pdf", ".txt", ".docx", ".xlsx")
    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(target_exts)]
    st.subheader("現在のファイル一覧")

    selected_files = []
    for f in files:
        col1, col2 = st.columns([0.8, 0.2])
        if col1.checkbox(f, value=True, key=f"check_{f}", disabled=is_locked):
            selected_files.append(f)
        if col2.button("🗑️", key=f"del_{f}", disabled=is_locked):
            target_path = os.path.join(DATA_DIR, f)
            if os.path.exists(target_path):
                os.remove(target_path)
            if os.path.exists(target_path + ":Zone.Identifier"):
                os.remove(target_path + ":Zone.Identifier")
            st.rerun()

    if st.button("🔄 インデックスを再構築", use_container_width=True, disabled=is_locked):
        if os.path.exists(PERSIST_DIR):
            for item in os.listdir(PERSIST_DIR):
                if item == "chat_history":
                    continue  # チャット履歴は守る
                
                item_path = os.path.join(PERSIST_DIR, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    
        st.success("記憶をリセットしました。")
        st.rerun()

    st.divider()
    st.subheader("履歴")
    if st.button("➕ 新しいチャット", use_container_width=True, disabled=is_locked):
        st.session_state.chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.messages = []
        st.rerun()

    for chat in list_chats():
        col_h1, col_h2 = st.columns([0.8, 0.2])
        if col_h1.button(f"💬 {chat['title']}", key=f"h_{chat['id']}", use_container_width=True):
            with open(os.path.join(CHAT_LOG_DIR, f"{chat['id']}.json"), "r") as f:
                data = json.load(f)
                st.session_state.messages = data["messages"]
            st.session_state.chat_id = chat['id']
            st.rerun()
        if col_h2.button("❌", key=f"d_{chat['id']}"):
            os.remove(os.path.join(CHAT_LOG_DIR, f"{chat['id']}.json"))
            st.rerun()

# --- 6. メイン画面 ---
st.title("⚡ Closed-Book ")

with st.spinner("AIが資料を確認中..."):
    index = get_index(selected_files)

if selected_files:
    filters = MetadataFilters(
        filters=[
            ExactMatchFilter(key="file_path", value=os.path.join(DATA_DIR, f))
            for f in selected_files
        ],
        condition="or"
    )
    st.caption(f"✅ 参照中: {', '.join(selected_files)}")
else:
    filters = None
    st.warning("左側のメニューからファイルを選択してください。")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

col_btn1, col_btn2, _ = st.columns([0.3, 0.3, 0.4])

with col_btn1:
    if st.button("🚨 矛盾をチェック", use_container_width=True, disabled=st.session_state.is_processing):
        if not filters:
            st.error("ファイルを選びなさい！")
        else:
            st.session_state.is_processing = True
            st.session_state.pending_task_prompt = "選ばれた資料を比較し、数値や手順に矛盾（食い違い）があれば具体的に指摘してください。なければ『整合性に問題はありません』と答えて。"
            st.session_state.messages.append({"role": "user", "content": "🚨 資料間の矛盾チェックを開始します"})
            st.rerun()

with col_btn2:
    if st.button("📝 全体の要約", use_container_width=True, disabled=st.session_state.is_processing):
        if not filters:
            st.error("ファイルを選びなさい！")
        else:
            st.session_state.is_processing = True
            st.session_state.pending_task_prompt = "選ばれた資料全体の内容を、重要なポイントに絞って簡潔に要約してください。"
            st.session_state.messages.append({"role": "user", "content": "📝 全体の要約を作成します"})
            st.rerun()

if st.session_state.is_processing and st.session_state.pending_task_prompt:
    with st.chat_message("assistant"):
        with st.status("大急ぎで解析中...", expanded=True) as status:
            st.write("ドキュメントをスキャンしています...")
            query_engine = index.as_query_engine(filters=filters, similarity_top_k=10)
            response = query_engine.query(st.session_state.pending_task_prompt)
            status.update(label="解析完了！", state="complete", expanded=False)

        full_res = response.response
        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
        save_chat(st.session_state.chat_id, st.session_state.messages, selected_files)

        st.session_state.is_processing = False
        st.session_state.pending_task_prompt = None
        st.rerun()

if not st.session_state.is_processing:
    if index and (prompt := st.chat_input("質問を入力してください...", key="main_chat_input")):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            query_engine = index.as_query_engine(streaming=True, filters=filters, similarity_top_k=5)
            response = query_engine.query(prompt)
            placeholder = st.empty()
            full_res = ""
            for text in response.response_gen:
                full_res += text
                placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
        save_chat(st.session_state.chat_id, st.session_state.messages, selected_files)
