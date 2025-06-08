from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
import json, os
from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def load_card_data():
    path = os.path.join(settings.BASE_DIR, 'chatbot', 'data', 'tarot_cards.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    card_dict = {}
    for i, card in enumerate(data):
        card_dict[str(i + 1)] = {
            "name": card["name"],
            "meaning": card.get("upright_meaning", "ไม่มีคำทำนาย")
        }
    return card_dict

def reset_chat(request):
    request.session.flush()
    return redirect('chatbot:index')

def get_card_image_filename(name):
    special_cases = {
        "The Judgement": "Judgement.jpg",
        # Add more if needed
    }
    return f"chatbot/{special_cases.get(name, name.replace(' ', '_') + '.jpg')}"

@csrf_exempt
def index(request):
    CARD_DATA = load_card_data()

    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
        request.session['has_drawn'] = False
        request.session['selected_cards'] = []
        request.session['question_count'] = 0

    drawn_cards_info = []

    if request.method == 'POST':
        selected = request.POST.getlist('selected_cards')
        
        if len(selected) == 10:
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

            orientations = ['upright'] * 10  # Static upright orientation

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
            request.session['chat_history'].append({
                'role': 'bot',
                'text': summary
            })
            request.session.modified = True
            return redirect('chatbot:index')

        else:
            user_message = request.POST.get('message')
            if user_message:
                request.session['chat_history'].append({'role': 'user', 'text': user_message})

                if not request.session['has_drawn']:
                    request.session['chat_history'].append({
                        'role': 'bot',
                        'text': 'กรุณาเลือกไพ่ 10 ใบจากสำรับด้านล่างก่อนถามคำถามค่ะ'
                    })

                elif request.session['question_count'] >= 3:
                    request.session['chat_history'].append({
                        'role': 'bot',
                        'text': 'คุณได้ถามครบ 3 คำถามแล้ว หากต้องการเริ่มใหม่ กรุณากดปุ่ม 🔄 เริ่มใหม่'
                    })

                else:
                    selected_cards_info = request.session.get('selected_cards_info', [])
                    card_summary = "\n".join([
                        f"{card['position']}: {card['card'].get('name', '')} - {card['card'].get('meaning', '')}"
                        for card in selected_cards_info
                    ])

                    prompt = f"""ผู้ใช้ถามว่า: "{user_message}"

ด้านล่างคือไพ่ 10 ใบที่ผู้ใช้จับได้ (รูปแบบ Celtic Cross):

{card_summary}

กรุณาตอบคำถามของผู้ใช้โดยอ้างอิงจากไพ่ข้างต้น รวมถึงการตีความในแง่จิตวิทยาและจิตวิญญาณ"""

                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o",  # or "gpt-4"
                            messages=[
                                {"role": "system", "content": "คุณคือหมอดูไพ่ทาโรต์ผู้ให้คำปรึกษาเรื่องความรัก การงาน และชีวิต"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7
                        )
                        bot_reply = response.choices[0].message.content.strip()
                    except Exception as e:
                        bot_reply = f"เกิดข้อผิดพลาดในการตอบคำถาม: {str(e)}"

                    request.session['chat_history'].append({'role': 'bot', 'text': bot_reply})
                    request.session['question_count'] += 1
                    request.session.modified = True

            return redirect('chatbot:index')

    if request.session.get('has_drawn'):
        drawn_cards_info = request.session.get('selected_cards_info', [])

    response = render(request, 'chatbot/chat.html', {
        'chat_history': request.session['chat_history'],
        'show_cards': not request.session.get('has_drawn', False),
        'selected_cards': request.session.get('selected_cards', []),
        'drawn_cards_info': drawn_cards_info,
        'card_range': range(1, 79),
    })

    return response