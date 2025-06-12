from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
import json, os
from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

MAX_QUESTIONS = 3
NUM_CARDS = 10

def load_card_data():
    """Load tarot card data from JSON file."""
    path = os.path.join(settings.BASE_DIR, 'chatbot', 'data', 'tarot_cards.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        data = []
        print(f"Error loading tarot_cards.json: {e}")

    card_dict = {}
    for i, card in enumerate(data):
        card_dict[str(i + 1)] = {
            "name": card.get("name", "ไม่ทราบชื่อไพ่"),
            "meaning": card.get("upright_meaning", "ไม่มีคำทำนาย")
        }
    return card_dict

def reset_chat(request):
    """Clear all session data and restart."""
    request.session.flush()
    return redirect('chatbot:index')

def get_card_image_filename(name):
    """Return filename for tarot card image, handling special cases."""
    special_cases = {
        "The Judgement": "Judgement.jpg",
        # Add more special cases here if needed
    }
    if not name:
        return ""
    filename = special_cases.get(name, name.replace(' ', '_') + '.jpg')
    return f"chatbot/{filename}"

CASUAL_RESPONSES = {
    'thx': "ยินดีค่ะ 😊 ขอให้โชคดีและพบเจอแต่สิ่งดี ๆ นะคะ",
    'thank': "ยินดีเสมอค่ะ 😊 ขอให้โชคดีและพบเจอแต่สิ่งดี ๆ นะคะ",
    'ขอบคุณ': "ยินดีมากค่ะ 💖 ขอให้คำทำนายเป็นประโยชน์นะคะ",
    'บาย': "ลาก่อนค่ะ ขอให้คุณพบเจอสิ่งดี ๆ 🌟",
    'bye': "ลาก่อนค่ะ ขอให้คุณพบเจอสิ่งดี ๆ 🌟",
    'บ๊ายบาย': "บ๊ายบายค่ะ แล้วกลับมาคุยกันใหม่นะคะ 💫",
    'love': "ขอบคุณค่ะ 💕 ขอให้ความรักของคุณเต็มไปด้วยพลังบวก",
    'ดีจัง': "ดีใจที่คุณชอบนะคะ 😊",
    'ชอบ': "ขอบคุณที่ชอบค่ะ ❤️",
    'ช่วยได้เยอะเลย': "ดีใจที่เป็นประโยชน์นะคะ 💡",
    'ตอบได้ดีมาก': "ขอบคุณค่ะ ฉันพยายามเต็มที่เพื่อคุณเลยนะ 🧙‍♀️"
}

def detect_casual_message(message):
    message = message.lower()
    for keyword, reply in CASUAL_RESPONSES.items():
        if keyword in message:
            return reply
    return None

@csrf_exempt
def index(request):
    CARD_DATA = load_card_data()

    # Initialize session variables if first visit
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
        request.session['has_drawn'] = False
        request.session['selected_cards'] = []
        request.session['question_count'] = 0
        request.session['extra_cards_info'] = []
        request.session['extra_cards_suggested'] = False

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'draw_extra_cards':
            # Draw 3 new cards that are not already in selected_cards
            already_drawn = request.session.get('selected_cards', [])
            import random
            available_ids = [str(i) for i in range(1, 79) if str(i) not in already_drawn]
            extra_drawn = random.sample(available_ids, 3)

            request.session['extra_drawn_cards'] = extra_drawn  # optional tracking
            CARD_DATA = load_card_data()

            extra_cards_info = [
                {
                    "position": f"ไพ่เพิ่มเติมใบที่ {i+1}",
                    "position_description": "ไพ่เพิ่มเติมเพื่อเจาะลึกสถานการณ์",
                    "card": CARD_DATA.get(card_id, {}),
                    "orientation": 'upright',
                    "image": get_card_image_filename(CARD_DATA.get(card_id, {}).get('name', ''))
                }
                for i, card_id in enumerate(extra_drawn)
            ]

            request.session['extra_cards_info'] = extra_cards_info
            request.session['chat_history'].append({
                'role': 'bot',
                'text': "🔮 คุณได้จับไพ่เพิ่มเติม 3 ใบแล้ว สามารถถามคำถามต่อได้เลยค่ะ"
            })
            request.session.modified = True
            return redirect('chatbot:index')   

        # Handle card selection submission
        selected = request.POST.getlist('selected_cards')

        if len(selected) == NUM_CARDS:
            request.session['selected_cards'] = selected
            request.session['has_drawn'] = True

            celtic_cross_positions = [
                {"label": "สถานการณ์ปัจจุบัน", "description": "ไพ่ใบนี้แสดงถึงสถานการณ์ที่คุณกำลังเผชิญอยู่ในปัจจุบัน"},
                {"label": "อุปสรรคและความท้าทาย", "description": "แสดงถึงสิ่งที่ขัดขวางหรือเป็นความท้าทายที่คุณต้องเผชิญ"},
                {"label": "อดีต", "description": "เป็นรากฐานของสถานการณ์นี้ อาจเป็นเหตุการณ์ในอดีตที่มีผลต่อปัจจุบัน"},
                {"label": "อนาคต", "description": "เป็นแนวโน้มของเหตุการณ์ที่อาจเกิดขึ้นในอนาคตอันใกล้"},
                {"label": "ความคิดหรือความตระหนักรู้", "description": "สิ่งที่คุณคิดหรือรับรู้เกี่ยวกับสถานการณ์นี้"},
                {"label": "จิตใต้สำนึก", "description": "แสดงถึงแรงขับภายในหรือสิ่งที่อยู่ในจิตใต้สำนึกของคุณ"},
                {"label": "คำแนะนำ", "description": "คำแนะนำหรือแนวทางที่ควรพิจารณา"},
                {"label": "ปัจจัยภายนอก", "description": "อิทธิพลจากสิ่งแวดล้อม คนรอบข้าง หรือปัจจัยภายนอก"},
                {"label": "ความหวังและความกลัว", "description": "สิ่งที่คุณหวังหรือกลัวว่าจะเกิดขึ้น"},
                {"label": "ผลลัพธ์", "description": "ผลลัพธ์สุดท้ายของสถานการณ์นี้หากดำเนินไปตามแนวทางปัจจุบัน"}
            ]

            orientations = ['upright'] * NUM_CARDS  # Static orientation for now

            selected_cards_info = [
                {
                    "position": celtic_cross_positions[i]["label"],
                    "position_description": celtic_cross_positions[i]["description"],
                    "card": CARD_DATA.get(card_id, {}),
                    "orientation": orientation,
                    "image": get_card_image_filename(CARD_DATA.get(card_id, {}).get('name', ''))
                }
                for i, (card_id, orientation) in enumerate(zip(selected, orientations))
            ]

            request.session['selected_cards_info'] = selected_cards_info

            summary = "🃏 ไพ่ที่คุณเลือกมีดังนี้:\n" + "\n".join([
                f"{i+1}. {card['card'].get('name', 'ไม่พบชื่อไพ่')}"
                for i, card in enumerate(selected_cards_info)
            ])

            request.session['chat_history'].append({'role': 'bot', 'text': summary})
            request.session.modified = True

            return redirect('chatbot:index')

        else:
            # Handle user questions
            user_message = request.POST.get('message')
            if user_message:
                request.session['chat_history'].append({'role': 'user', 'text': user_message})

                casual_reply = detect_casual_message(user_message)
                if casual_reply:
                    request.session['chat_history'].append({'role': 'bot', 'text': casual_reply})
                    request.session.modified = True
                    return redirect('chatbot:index')  # Skip tarot reading and return polite reply

                if not request.session.get('has_drawn', False):
                    request.session['chat_history'].append({
                        'role': 'bot',
                        'text': 'กรุณาเลือกไพ่ 10 ใบจากสำรับด้านล่างก่อนถามคำถามค่ะ'
                    })
                else:
                    selected_cards_info = request.session.get('selected_cards_info', [])
                    extra_cards_info = request.session.get('extra_cards_info', [])
                    all_cards_info = selected_cards_info + extra_cards_info

                    # # Suggest drawing extra cards after 3rd question
                    # if request.session.get('question_count', 0) == 3 and not request.session.get('extra_cards_suggested', False):
                    #     request.session['chat_history'].append({
                    #         'role': 'bot',
                    #         'text': '🃏 คุณได้ถามครบ 3 คำถามแล้ว หากต้องการคำแนะนำเพิ่มเติม คุณสามารถจับไพ่เพิ่มอีก 3 ใบเพื่อเจาะลึกสถานการณ์มากขึ้น'
                    #     })
                    #     request.session['extra_cards_suggested'] = True

                    # Build card summary from all drawn cards
                    card_summary = "\n".join([
                        f"{card['position']}: {card['card'].get('name', '')} - {card['card'].get('meaning', '')}"
                        for card in all_cards_info
                    ])

                    prompt = f"""ผู้ใช้ถามว่า: "{user_message}"

ไพ่ทั้งหมดที่ผู้ใช้จับได้ (รวมไพ่เพิ่มเติมถ้ามี):

{card_summary}

กรุณาตอบคำถามของผู้ใช้โดยอ้างอิงจากไพ่ข้างต้น รวมถึงการตีความในแง่จิตวิทยาและจิตวิญญาณ"""

                    try:
                        response = client.chat.completions.create(
                            # model="gpt-4o",
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "คุณคือหมอดูไพ่ทาโรต์ผู้ให้คำปรึกษาเรื่องความรัก การงาน และชีวิต"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7,
                            max_tokens=800,
                        )
                        bot_reply = response.choices[0].message.content.strip()
                    except Exception as e:
                        bot_reply = f"เกิดข้อผิดพลาดในการตอบคำถาม: {str(e)}"

                    request.session['chat_history'].append({'role': 'bot', 'text': bot_reply})
                    request.session['question_count'] = request.session.get('question_count', 0) + 1
                    request.session.modified = True

            return redirect('chatbot:index')

    # If GET or no POST redirect
    drawn_cards_info = request.session.get('selected_cards_info', []) if request.session.get('has_drawn', False) else []

    return render(request, 'chatbot/chat.html', {
        'chat_history': request.session.get('chat_history', []),
        'show_cards': not request.session.get('has_drawn', False),
        'selected_cards': request.session.get('selected_cards', []),
        'drawn_cards_info': drawn_cards_info,
        'extra_cards_info': request.session.get('extra_cards_info', []),
        'card_range': range(1, 79),
    })