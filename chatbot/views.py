from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
import json, os
from django.conf import settings

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

@csrf_exempt
def index(request):
    CARD_DATA = load_card_data()

    # Initialize session
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
        request.session['has_drawn'] = False
        request.session['selected_cards'] = []

    drawn_cards_info = []

    if request.method == 'POST':
        selected = request.POST.getlist('selected_cards')
        if len(selected) == 10:
            request.session['selected_cards'] = selected
            request.session['has_drawn'] = True

            selected_cards_info = [
                {
                    "name": CARD_DATA.get(card_id, {}).get('name', 'Unknown'),
                    "meaning": CARD_DATA.get(card_id, {}).get('meaning', 'ไม่มีคำทำนาย'),
                    "image": f"chatbot/{CARD_DATA.get(card_id, {}).get('name', '').replace(' ', '_')}.jpg"
                }
                for card_id in selected
            ]

            request.session['selected_cards_info'] = selected_cards_info

            summary = "คุณได้เลือกไพ่ครบแล้ว:\n" + "\n".join([
                f"{i+1}. {card['name']} - {card['meaning']}"
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
                        'text': 'กรุณาเลือกไพ่ 10 ใบจากสำรับด้านล่าง'
                    })
                else:
                    request.session['chat_history'].append({'role': 'bot', 'text': 'คุณได้เลือกไพ่ครบแล้ว สามารถถามคำถามต่อได้เลยค่ะ'})
                request.session.modified = True
            return redirect('chatbot:index')

    # Retrieve previously drawn cards (for display)
    if request.session.get('has_drawn'):
        drawn_cards_info = request.session.get('selected_cards_info', [])

    response = render(request, 'chatbot/chat.html', {
        'chat_history': request.session['chat_history'],
        'show_cards': not request.session.get('has_drawn', False),
        'selected_cards': request.session.get('selected_cards', []),
        'drawn_cards_info': request.session.get('selected_cards_info', []),
        'card_range': range(1, 79),
    })

    # # ✅ Now this line actually runs inside the function
    # if 'selected_cards_info' in request.session:
    #     del request.session['selected_cards_info']

    return response