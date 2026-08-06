import os
import random
import re
import tempfile
from PIL import Image
import streamlit as st
import whisper

# 画面設定
st.set_page_config(page_title="数学A 証明発表フィードバック", page_icon="📐")

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
if "teacher_comment" not in st.session_state:
    st.session_state.teacher_comment = None

uploaded_file = st.file_uploader(
    "証明動画を選択してください",
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

        st.info("発表を解析中だよ...（※30秒〜1分かかります）")

        try:
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

            char_count = len(text)
            chars_per_min = (char_count / duration) * 60 if duration > 0 else 0

            # --- 解析データの抽出 ---

            # ① フィラー検出
            fillers = ["えー", "えっと", "あのー", "そのー", "まあ", "なんか"]
            filler_count = sum(text.count(f) for f in fillers)

            # ② 接続詞の種類（バリエーション）チェック
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

            # ③ 同じ言葉の繰り返し（「なので」「で、」など）
            repeat_words = ["なので", "で、", "から、"]
            found_repeats = [w for w in repeat_words if text.count(w) >= 3]

            # ④ 記号・式の読み上げ割合（簡易判定）
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

            # 【イケボシさん】：構造・スピード・時間・読み上げに関するフィードバック
            boy_msg = f"今回は【{time_str}】の発表だったね！最後までしっかり発表しきってお疲れ様！ "

            boy_aspects = []

            # 速度に関するアドバイス
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

            # 読み上げ傾向のアドバイス
            if symbol_count >= 5 and logic_type_count < 2:
                boy_aspects.append(
                    "式や記号を読み上げる場面が多く見受けられました。黒板の式を読むだけでなく『なぜその式が成り立つのか』の理由を言葉で添えると、さらに伝わる発表になるよ！"
                )

            boy_msg += random.choice(boy_aspects)

            # 【フゾクリーフさん】：言葉遣い・フィラー・接続詞・繰り返しに関するフィードバック
            girl_aspects = []

            # フィラーのアドバイス
            if filler_count >= 3:
                girl_aspects.append(
                    "『えー』『あのー』などの言葉が少し多めだったかな。考える時間が必要なときは、無理に言葉をつなげず一度黙って『間（ま）』を取る方が、聞き手には気持ちよく伝わるよ！"
                )

            # 接続詞の種類のアドバイス
            if logic_type_count >= 3:
                examples = "」や「".join(found_logic_types[:2])
                girl_aspects.append(
                    f"「{examples}」など、根拠と結論をつなぐ言葉をバリエーション豊かに使えていて論理的だったよ！"
                )
            elif logic_type_count == 0:
                girl_aspects.append(
                    "次は『仮定より』や『したがって』といった、理由や結論をつなぐ数学の言葉を1つ入れてみると、証明の流れがよりスッキリするよ！"
                )

            # 繰り返しのアドバイス
            if found_repeats:
                w = found_repeats[0]
                girl_aspects.append(
                    f"『{w}』という言葉が連続して使われているところがあったよ。『ここから分かることは〜』など別の表現を混ぜると、説明にメリハリが出るよ！"
                )

            # 特記要素がない場合のデフォルト褒め
            if not girl_aspects:
                girl_aspects.append(
                    "自分の声をしっかり吹き込んで、落ち着いて説明できていてとても良かったよ！"
                )

            # 語尾に必ず先生枠への誘導を追加
            girl_aspects.append("先生からのメッセージも見てみてね！")

            girl_msg = " ".join(girl_aspects)

            # 【先生の四字熟語・独り言（謎枠）】
            # 80%：普通 / 19%：渋い / 1%：シュール枠
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

            # 結果の保存（「先生：」を無くして顔文字だけに修正）
            st.session_state.boy_comment = boy_msg
            st.session_state.girl_comment = girl_msg
            st.session_state.teacher_comment = (
                f"（ ‾皿‾ ）： {chosen_quote}"
            )

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

    st.chat_message("user", avatar=boy_icon).write(
        f"**【イケボシさん】**\n\n{st.session_state.boy_comment}"
    )
    st.chat_message("assistant", avatar=girl_icon).write(
        f"**【フゾクリーフさん】**\n\n{st.session_state.girl_comment}"
    )

    # 先生の一言枠（画面下部にだけひっそり表示）
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

    # コピペ用テキストにはイケボシ・フゾクリーフのみ含める
    full_text_for_copy = f"【イケボシさん】\n{st.session_state.boy_comment}\n\n【フゾクリーフさん】\n{st.session_state.girl_comment}"
    st.code(full_text_for_copy, language=None)
