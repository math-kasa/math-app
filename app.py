import streamlit as st
import whisper
import tempfile
import os
import random
from PIL import Image

# 画面設定
st.set_page_config(page_title="数学A 証明発表フィードバック", page_icon="📐")

st.title("📐 数学A 証明発表フィードバック")
st.write("動画をアップロードすると、イケボシさんとフゾクリーフさんからアドバイスが届くよ！")
st.write("※２人のアドバイスを、提出するGoogle formにコピペしてください。")

# 【軽量化】モデルを "base" から 最も軽い "tiny" に変更
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("tiny")

model = load_whisper_model()

# 画像の読み込みと自動分割（アイコン作成）
image_file = None
for name in ["chara.jpg", "chara.png", "chara.jpeg"]:
    if os.path.exists(name):
        image_file = name
        break

boy_icon, girl_icon = "👦", "👧"

if image_file:
    try:
        img = Image.open(image_file)
        width, height = img.size
        boy_icon = img.crop((0, 0, width // 2, height))
        girl_icon = img.crop((width // 2, 0, width, height))
    except Exception:
        pass

# セッション状態の初期化
if "boy_comment" not in st.session_state:
    st.session_state.boy_comment = None
if "girl_comment" not in st.session_state:
    st.session_state.girl_comment = None

uploaded_file = st.file_uploader("証明動画を選択してください", type=["mp4", "mov", "avi", "m4a", "mp3", "wav"])

if uploaded_file is not None:
    if st.button("解析を開始する") or st.session_state.boy_comment is None:
        suffix = os.path.splitext(uploaded_file.name)[1]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        st.info("発表を解析中だよ...（※30秒〜1分かかります）")

        try:
            # 1. 文字起こし & 時間計測（Whisper単体で完結させて軽量化）
            result = model.transcribe(tmp_path, language="ja")
            text = result.get("text", "")
            
            # 動画の長さを取得（Whisperのセグメント情報から算出）
            segments = result.get("segments", [])
            duration = segments[-1]["end"] if segments else 60.0
            
            char_count = len(text)
            chars_per_min = (char_count / duration) * 60 if duration > 0 else 0

            logic_words = ["したがって", "ゆえに", "なぜなら", "よって", "仮定より", "定義より", "つまり"]
            found_logic_words = [w for w in logic_words if w in text]

            # 2. 台詞作成
            boy_openings = [
                "最後までしっかりと自分の言葉で証明を説明しきることができたね！素晴らしい！",
                "順序立てて数学の考えを伝えようとする姿勢がすごく伝わってきたよ！",
                "落ち着いてプレゼンテーションをやり遂げたね！大変お疲れ様！",
                "証明の構成をしっかり準備して発表に臨めているのがよく分かったよ！"
            ]
            
            boy_speed_msg = ""
            if chars_per_min > 350:
                boy_speed_msg = "伝えたい意欲が素晴らしい反面、少し早口になる場面があったから、数式の変形を説明するときは一呼吸置くとさらに良くなるよ！"
            elif chars_per_min < 150:
                boy_speed_msg = "じっくりと丁寧に話せていたね。もう少しテンポアップすると、さらにスマートな印象になるよ！"
            else:
                boy_speed_msg = "早すぎず遅すぎず、相手が理解しやすい絶妙なスピード感で発表できていたよ！"

            boy_closings = [
                "今回の良さを活かして、次回の発表も自信を持ってチャレンジしてね！",
                "少し意識を変えるだけでさらに良いプレゼンになるよ。応援してるね！",
                "自分の考えを言葉で伝える経験は確実に力になってるよ。この調子で頑張ろう！"
            ]

            girl_voice_msg = "自分の声をしっかりと吹き込んで発表できていて素晴らしかったよ！"

            girl_logic_msg = ""
            if len(found_logic_words) >= 2:
                girl_logic_msg = f"「{found_logic_words[0]}」や「{found_logic_words[1]}」みたいな数学の接続詞を正しく使えていて、論理展開が明快だったよ！"
            else:
                girl_logic_msg = "次は「したがって」や「なぜなら」っていう言葉を意識して挟むと、証明の流れがより伝わりやすくなるよ！"

            # 3. 結果の保存
            st.session_state.boy_comment = f"{random.choice(boy_openings)} {boy_speed_msg} {random.choice(boy_closings)}"
            st.session_state.girl_comment = f"{girl_voice_msg} {girl_logic_msg}"

        except Exception as e:
            st.error(f"解析中にエラーが発生しました: {e}")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# 画面表示
if st.session_state.boy_comment is not None:
    st.subheader("🌟 ２人からのメッセージ")

    if image_file:
        st.image(image_file, use_container_width=True)

    st.chat_message("user", avatar=boy_icon).write(f"**【イケボシさん】**\n\n{st.session_state.boy_comment}")
    st.chat_message("assistant", avatar=girl_icon).write(f"**【フゾクリーフさん】**\n\n{st.session_state.girl_comment}")

    st.markdown("---")
    st.write("📋 **Google Form提出用テキスト（ここを右上のアイコンでコピーできます）**")
    full_text_for_copy = f"【イケボシさん】\n{st.session_state.boy_comment}\n\n【フゾクリーフさん】\n{st.session_state.girl_comment}"
    st.code(full_text_for_copy, language=None)