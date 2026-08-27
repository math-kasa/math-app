import gc
import os
import random
import re
import tempfile
import threading
from PIL import Image
import streamlit as st
import whisper

# 画面設定
st.set_page_config(page_title="数学A 証明発表フィードバック", page_icon="📐")


# 全セッション（全員）で完全共有される「真の順番待ち用の鍵」
@st.cache_resource
def get_global_lock():
    return threading.Lock()


global_lock = get_global_lock()

st.title("📐 数学A 証明発表フィードバック")
st.write(
    "動画をアップロードすると、イケボシさんとフゾクリーフさんからアドバイスが届くよ！"
)
st.write("※２人のアドバイスを、提出するGoogle formにコピペしてください。")


# 【軽量化】最も軽い "tiny" モデルをキャッシュ読み込み
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("tiny")


model = load_whisper_model()

# 画像の読み込みと自動分割
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
if "teacher_comment" not in st.session_state:
    st.session_state.teacher_comment = None

uploaded_file = st.file_uploader(
    "証明動画を選択してください（※3分以内の動画を推奨します）",
    type=["mp4", "mov", "avi", "m4a", "mp3", "wav"],
)

if uploaded_file is not None:
    if st.button("解析を開始する") or st.session_state.boy_comment is None:
        suffix = os.path.splitext(uploaded_file.name)[1]

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name

        st.info(
            "発表を解析中だよ...（他の人が実行中の場合は順番待ちになります。そのままお待ちください）"
        )

        try:
            # 全ユーザー共通の鍵を取得して1人ずつ順番に安全処理
            with global_lock:
                # 1. 文字起こし & 時間計測
                result = model.transcribe(tmp_path, language="ja")
                text = result.get("text", "")

                segments = result.get("segments", [])
                duration = segments[-1]["end"] if segments else 60.0

                # 分・秒の計算
                duration_min = int(duration // 60)
                duration_sec = int(duration % 60)
                time_str = (
                    f"{duration_min}分{duration_sec}秒"
                    if duration_min > 0
                    else f"{duration_sec}秒"
                )

                # 長すぎる動画への対応
                if duration > 300:
                    st.warning(
                        f"⚠️ 動画の時間が【{time_str}】と長いため、処理を中断しました。\n\n"
                        f"**【生徒のみなさんへ】**\n"
                        f"・授業中は自分の動画を見て振り返りを進めてね！\n"
                        f"・このアプリは**家でやり直す**か、フォームに**「動画長いため家で実行」**と書いて提出すればOKです。"
                    )
                else:
                    char_count = len(text)
                    chars_per_min = (
                        (char_count / duration) * 60 if duration > 0 else 0
                    )

                    # --- 解析データの抽出 ---
                    fillers = [
                        "えー",
                        "えっと",
                        "あのー",
                        "そのー",
                        "まあ",
                        "なんか",
                    ]
                    filler_count = sum(text.count(f) for f in fillers)

                    logic_words = [
                        "仮定より",
                        "定義より",
                        "だから",
                        "したがって",
                        "よって",
                        "以上より",
                        "なぜなら",
                        "ゆえに",
                        "つまり",
                    ]
                    found_logic_types = [w for w in logic_words if w in text]
                    logic_type_count = len(found_logic_types)

                    repeat_words = ["なので", "で、", "から、"]
                    found_repeats = [
                        w for w in repeat_words if text.count(w) >= 3
                    ]

                    symbols = [
                        "＝",
                        "=",
                        "∠",
                        "△",
                        "平行",
                        "合同",
                        "垂直",
                        "AB",
                        "BC",
                        "CA",
                    ]
                    symbol_count = sum(text.count(s) for s in symbols)

                    # --- コメント生成ロジック ---
                    boy_msg = f"今回は【{time_str}】の発表だったね！最後までしっかり発表しきってお疲れ様！ "
                    boy_aspects = []

                    if chars_per_min > 350:
                        boy_aspects.append(
                            "伝えたい気持ちが伝わる熱い発表だったよ！ただ少し早口になる場面があったから、数式を説明するときは一呼吸置くとさらに良くなるよ。"
                        )
                    elif chars_per_min < 140:
                        boy_aspects.append(
                            "1言葉1言葉を丁寧に話せていたね。もう少しテンポアップすると、さらに聞きやすいスマートな印象になるよ！"
                        )
                    else:
                        boy_aspects.append(
                            "早すぎず遅すぎず、相手が理解しやすい絶妙なスピード感で話せていて素晴らしかったよ！"
                        )

                    if symbol_count >= 5 and logic_type_count < 2:
                        boy_aspects.append(
                            "式や記号を読み上げる場面が多く見受けられました。黒板の式を読むだけでなく『なぜその式が成り立つのか』の理由を言葉で添えると、さらに伝わる発表になるよ！"
                        )

                    boy_msg += random.choice(boy_aspects)

                    girl_aspects = []

                    if filler_count >= 3:
                        girl_aspects.append(
                            "『えー』『あのー』などの言葉が少し多めだったかな。考える時間が必要なときは、無理に言葉をつなげず一度黙って『間（ま）』を取る方が、聞き手には気持ちよく伝わるよ！"
                        )

                    if logic_type_count >= 3:
                        examples = "」や「".join(found_logic_types[:2])
                        girl_aspects.append(
                            f"「{examples}」など、根拠と結論をつなぐ言葉をバリエーション豊かに使えていて論理的だったよ！"
                        )
                    elif logic_type_count == 0:
                        girl_aspects.append(
                            "次は『仮定より』や『したがって』といった、理由や結論をつなぐ数学の言葉を1つ入れてみると、証明の流れがよりスッキリするよ！"
                        )

                    if found_repeats:
                        w = found_repeats[0]
                        girl_aspects.append(
                            f"『{w}』という言葉が連続して使われているところがあったよ。『ここから分かることは〜』など別の表現を混ぜると、説明にメリハリが出るよ！"
                        )

                    if not girl_aspects:
                        girl_aspects.append(
                            "自分の声をしっかり吹き込んで、落ち着いて説明できていてとても良かったよ！"
                        )

                    girl_aspects.append("（下のメッセージも見てみてね！）")
                    girl_msg = " ".join(girl_aspects)

                    teachers_normal = [
                        "温故知新",
                        "日々精進",
                        "百折不撓",
                        "知行合一",
                        "切磋琢磨",
                        "初志貫徹",
                        "七転八起",
                        "勇往邁進",
                        "一意専心",
                        "自我作古",
                        "質実剛健",
                        "明鏡止水",
                    ]
                    teachers_shibui = [
                        "不言実行",
                        "臨機応変",
                        "乾坤一擲",
                        "行雲流水",
                        "虚心坦懐",
                        "大器晩成",
                        "雲外蒼天",
                        "愚公移山",
                        "一念通天",
                        "積土成山",
                    ]
                    teachers_funny = [
                        "天上天下唯我独尊や",
                        "トライ＆エラーやで",
                        "はい、集中！",
                        "暑いなぁ",
                        "よう頑張ってる。先生感動したわ",
                    ]

                    rand_val = random.random()
                    if rand_val < 0.80:
                        chosen_quote = random.choice(teachers_normal)
                    elif rand_val < 0.99:
                        chosen_quote = random.choice(teachers_shibui)
                    else:
                        chosen_quote = random.choice(teachers_funny)

                    st.session_state.boy_comment = boy_msg
                    st.session_state.girl_comment = girl_msg
                    st.session_state.teacher_comment = (
                        f"（ ‾皿‾ ）： {chosen_quote}"
                    )

        except Exception:
            # 処理落ち・エラーが発生した時に画面に表示する安心案内
            st.error(
                "⚠️【ただいまサーバーが混雑しています】\n\n"
                "みんなが一斉に使っているか、動画の処理に時間がかかっているため中断しました。\n\n"
                "**【生徒のみなさんへ】**\n"
                "・無理に何度も試さず、**自分の動画を見て振り返りを進めてください。**\n"
                "・このアプリでの処理は**「家でやり直す」**か、Google Formに**「混雑エラーのため家で実行」**と書いて提出すればOKです！"
            )

        finally:
            # 一時ファイル削除 ＆ メモリ強制解放
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            gc.collect()

# 画面表示
if st.session_state.boy_comment is not None:
    st.subheader("🌟 ２人からのメッセージ")

    if image_file:
        st.image(image_file, use_container_width=True)

    st.chat_message("user", avatar=boy_icon).write(
        f"**【イケボシさん】**\n\n{st.session_state.boy_comment}"
    )
    st.chat_message("assistant", avatar=girl_icon).write(
        f"**【フゾクリーフさん】**\n\n{st.session_state.girl_comment}"
    )

    st.info(st.session_state.teacher_comment)

    st.markdown("---")
    st.subheader("📝 振り返りワーク")
    st.write(
        "今回の発表を振り返って、**「自分の発表で良かったところ（次回も続けたいこと）」**"
        " や、**「改善したいこと（次の工夫）」** をGoogle Formに書こう！"
    )

    st.write(
        "📋 **Google Form提出用テキスト（下の右上のアイコンでコピーできます）**"
    )

    full_text_for_copy = f"【イケボシさん】\n{st.session_state.boy_comment}\n\n{st.session_state.girl_comment}"
    st.code(full_text_for_copy, language=None)
