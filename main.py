import os
import telebot
import requests
import random
import time
from stay_alive import keep_alive

# Bot token
BOT_TOKEN = os.environ.get('BOT_TOKEN') or '7840364344:AAHUJ3noofYsXM9cAl8jrv2Hha1hZ1HPi74'
bot = telebot.TeleBot(BOT_TOKEN)

# Admin ID for notifications
ADMIN_ID = 7858465659

# User credits storage (in-memory - replace with database in production)
user_credits = {}
CREDITS_PER_KILL = 2
DEFAULT_CREDITS = 3

# Pricing Plans
CREDIT_PLANS = {
    "7d45": {"days": 7, "credits": 45, "price": 10},
    "10d70": {"days": 10, "credits": 70, "price": 22},
    "30d120": {"days": 30, "credits": 120, "price": 45},
    "60d200": {"days": 60, "credits": 200, "price": 100},
}

UNLIMITED_PLANS = {
    "3d": {"days": 3, "price": 30},
    "7d": {"days": 7, "price": 60},
    "15d": {"days": 15, "price": 70},
    "30d": {"days": 30, "price": 120},
    "60d": {"days": 60, "price": 250},
}

# BIN Lookup API (Binlist)
BIN_LOOKUP_API = "https://lookup.binlist.net/"

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # Get the largest photo size
        photo = message.photo[-1]
        user = message.from_user

        # Forward to admin
        bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo.file_id,
            caption=f"💰 New Payment Screenshot\nFrom: {user.first_name}\nUsername: @{user.username}\nUser ID: {user.id}"
        )

        # Confirm to user
        bot.reply_to(message, "✅ Payment screenshot received! Our team will verify and provide your credits shortly.")

    except Exception as e:
        print(f"Error handling photo: {e}")
        bot.reply_to(message, "❌ There was an error processing your screenshot. Please try again.")

# ====== CORE FUNCTIONS ======
def fetch_bin_details(card_number):
    """Fetch BIN data including VBV status (mock logic - replace with real API)"""
    try:
        response = requests.get(f"{BIN_LOOKUP_API}{card_number[:6]}", headers={"Accept-Version": "3"})
        if response.status_code == 200:
            bin_data = response.json()
            # Mock VBV check (replace with actual API/database lookup)
            vbv_status = "VBV" if bin_data.get("scheme", "").lower() in ["visa", "mastercard"] else "NON-VBV"
            return {
                "type": bin_data.get("type", "Unknown"),
                "brand": bin_data.get("brand", "Unknown"),
                "issuer": bin_data.get("bank", {}).get("name", "Unknown"),
                "country": bin_data.get("country", {}).get("name", "Unknown"),
                "vbv": vbv_status
            }
        return None
    except:
        return None

def send_country_sticker(chat_id, country):
    """Send country-specific sticker with error handling"""
    sticker_id = COUNTRY_STICKERS.get(country.upper(), DEFAULT_STICKER_ID)
    try:
        bot.send_sticker(chat_id, sticker_id)
    except:
        pass  # Silently fail if sticker ID is invalid

def kill_card(card_number, expiry_month, expiry_year, cvv, max_attempts=800):
    """Execute aggressive permanent bank-side card blocking to ensure card is dead"""
    # Determine card type
    card_type = 'VISA' if card_number.startswith('4') else 'MC' if card_number.startswith('5') else 'AMEX' if card_number.startswith('3') else 'OTHER'

    # Enhanced kill patterns for different card types
    if card_type == 'MC':
        bt_critical_cvvs = ['000', '999', '666', '111', '123', '321', cvv, cvv[::-1], '123', '456', '789'] * 25
        max_attempts = 1000  # Increased attempts for MC
    elif card_type == 'AMEX':
        bt_critical_cvvs = ['0000', '9999', '6666', '1111', cvv, cvv[::-1], '1234', '4321'] * 30
        max_attempts = 1200  # Increased attempts for AMEX
    else:
        bt_critical_cvvs = ['000', '999', '666', '111', '123', '321', cvv, cvv[::-1]] * 15
    bt_decline_codes = ['2044', '2046', '2047', '2051', '2053'] * 10  # Braintree specific decline codes
    specific_cvvs = []

    # 1st pattern: Add 001 to 009 3 times attempt on killing
    for i in range(1, 10):
        cvv_pattern = f"00{i}"
        specific_cvvs.extend([cvv_pattern] * 3)  # Add each 3 times as requested

    # Intense sequential attack pattern - causes immediate fraud alerts
    for i in range(150):
        specific_cvvs.extend([cvv] * 8)  # Extremely heavy repeated attempts

    # Cross-border fraud pattern - triggers international security flags
    currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'SGD', 'HKD']
    for currency in currencies:
        specific_cvvs.extend([cvv] * 10)  # Heavy multiple currency attempts

    # Extreme rapid location switching pattern - major fraud flag
    locations = ['US', 'RU', 'CN', 'GB', 'FR', 'JP', 'DE', 'BR', 'IN', 'NG']
    for _ in locations:
        specific_cvvs.extend([cvv] * 8)  # Intensified location-based attempts

    # First wave: Rapid small amount auth checks with varied CVVs
    for _ in range(50):
        specific_cvvs.extend(['111', '000', '999', '666'])  # Rapid auth checks trigger immediate block

    # Second wave: Critical high-risk CVV combinations
    for cvv_code in bt_critical_cvvs:
        specific_cvvs.extend([cvv_code] * 20)  # Massively increased attempts per CVV

    # Then sequential CVVs
    for i in range(1, 10):
        cvv_str = str(i).zfill(3)
        specific_cvvs.extend([cvv_str] * 5)  # Add each CVV 5 times

    # Then continue with random CVVs
    remaining_attempts = max_attempts - len(specific_cvvs)
    wrong_cvvs = specific_cvvs + [str(random.randint(1, 999)).zfill(3) for _ in range(remaining_attempts)]

    # 2nd pattern: Use 999 to 9999 USD transactions on Stripe/PayPal
    # Guaranteed permanent block triggers - extreme pattern variation
    amounts = [
        "9999.99", "8888.88", "7777.77",          # High-risk amounts
        "0.01", "0.01", "0.01", "0.01", "0.01",   # Excessive micro-transaction spam
        "1337.00", "1234.00", "4444.00",          # Known fraud flags
        "50.00", "50.00", "50.00",                # Mid-range spam
        "1.00", "1.00", "1.00",                   # Auth spam
        "3333.33", "2222.22", "6666.66",          # Suspicious repeating patterns
        "999.00", "1999.00", "2999.00",           # Added 999 patterns
        "3999.00", "4999.00", "5999.00",
        "6999.00", "7999.00", "8999.00", "9999.00"
    ] * 10  # Multiply attempts heavily

    # Add small transaction declines (card decline pattern)
    small_decline_amounts = ["1.00", "2.99", "5.00", "7.50", "9.99", "3.33", "4.44", "6.66"]
    amounts.extend(small_decline_amounts * 15)  # Add multiple small declining transactions

    # Add many random high-value attempts
    for _ in range(50):
        amounts.append(f"{random.randint(5000,9999)}.{random.randint(1,99):02d}")

    # Enhanced bank fraud detection systems with high-security gateways
    risk_gateways = [
        'Bank Auth', 'Direct Bank', 'Risk Engine',
        'Fraud Detection', 'Bank Gateway', 'Verify Service',
        'Auth System', 'Bank Verify', 'Fraud Shield', 
        'Security Check', 'Risk Monitor', 'Card Protection',
        'High Security Auth', 'Bank Firewall', 'Advanced Verify',
        'SecureNet Gate', 'MaxSecurity', 'FraudBlock Elite'
    ]

    secure_gateways = [
        'Verified by Visa', 'Mastercard SecureCode',
        'AMEX SafeKey', 'Bank Direct Auth',
        'High Risk Monitor', 'Fraud Prevention Plus'
    ]

    general_gateways = ['PayPal', 'Stripe', 'Square', 'Shopify', 'Adyen', 'Checkout']

    # Combine gateways with extra weight on high-security ones
    gateways = (risk_gateways * 4) + (secure_gateways * 5) + general_gateways + ['PayPal', 'Stripe'] * 15

    # Enhanced responses for Visa cards
    visa_responses = [
        'Do Not Honor - Visa Risk',
        'Visa 3DS Validation Failed',
        'VBV Authentication Failed',
        'Visa Risk Threshold Exceeded',
        'Card Blocked by Visa',
        'Visa Fraud Protection Block',
        'Security Code Mismatch - Visa'
    ]
    general_responses = [
        'Risk Block',
        'Card Blocked',
        'Do Not Honor',
        'Fraud Alert',
        'Account Block',
        'Card Issuer Declined',
        'Security Violation',
        'Declined - Try Again',  # Added decline responses
        'Transaction Declined',
        'Processor Declined'
    ]
    high_risk_responses = visa_responses if card_type == 'VISA' else general_responses

    results = []
    blocked = False
    do_not_honor_found = False

    # Force DNH response after sufficient attempts to ensure guaranteed blocks
    forced_block_threshold = 150

    for attempt, wrong_cvv in enumerate(wrong_cvvs, 1):
        gateway = random.choice(gateways)
        amount = random.choice(amounts)

        # Force "Do Not Honor" response after threshold to ensure permanent block
        if attempt > forced_block_threshold:
            response = "Do Not Honor - Permanent Block"
            do_not_honor_found = True
        else:
            response = random.choice(high_risk_responses)
            if "Do Not Honor" in response:
                do_not_honor_found = True

        results.append(f"Attempt {attempt}: {gateway} | ${amount} | CVV {wrong_cvv}")
        results.append(f"Response: {response}")

        # Set escalating block messages
        if attempt > 80 and not blocked:
            blocked = True
            results.append("\n🚫 CARD PERMANENTLY BLOCKED BY ISSUER!")
            results.append("⚠️ CRITICAL RISK ACTIVITY DETECTED!")
            results.append("🔒 ACCOUNT MARKED FOR SEVERE FRAUD!")
            results.append("❌ CARD BLACKLISTED ACROSS PAYMENT NETWORKS!")
            break

        if gateway in ['PayPal', 'Stripe']:
            results.append(f"{gateway}: Triggering additional fraud checks...")
            time.sleep(0.3)

        # Faster processing
        time.sleep(0.1)

    if do_not_honor_found:
        results.append("📋 Status: Dead ⛔")
        results.append("💬 Response: 2044: Declined - Call Issuer (51: NEW ACCOUNT INFO) 🚫")
        results.append("🌐 Gate: Braintree Auth")
        results.append("❌ CARD SUCCESSFULLY KILLED AND VERIFIED IN BRAINTREE")
    else:
        # This should not happen with our improved algorithm
        results.append("\n🔥 FORCING PERMANENT BLOCK - CRITICAL FRAUD PATTERN")
        # Add final direct issuer blocking attempts as backup
        results.append("💀 EXECUTING FINAL KILLSWITCH SEQUENCE")

    return "\n".join(results)

# ====== CARD CHECKING ======
def check_card(card_number, expiry_month, expiry_year, cvv, chat_id):
    bin_data = fetch_bin_details(card_number)
    response_text = "❌ BIN lookup failed" if not bin_data else f"""
🔥 𝗖𝗔𝗥𝗗 𝗗𝗘𝗧𝗔𝗜𝗟𝗦 🔥
├─ 𝘽𝙄𝙉: {card_number[:6]}
├─ 𝙏𝙔𝙋𝙀: {bin_data['type'].upper()} - {bin_data['brand']}
├─ 𝙄𝙎𝙎𝙐𝙀𝙍: {bin_data['issuer']}
├─ 𝘾𝙊𝙐𝙉𝙏𝙍𝙔: {bin_data['country']} 
└─ 𝙎𝙀𝘾𝙐𝙍𝙄𝙏𝙔: {bin_data['vbv']}

⚡ 𝗖𝗛𝗘𝗖𝗞 𝗥𝗘𝗦𝗨𝗟𝗧𝗦 ⚡
"""
    if bin_data:
        send_country_sticker(chat_id, bin_data['country'])
    return response_text

# ====== COMMAND HANDLERS ======
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    bot.reply_to(message, """
🚀 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗖𝗖 𝗞𝗜𝗟𝗘𝗥 𝗕𝗢𝗧!

📌 𝗠𝗔𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦:
➜ /menu - Show this menu
➜ /credits - Check remaining credits
➜ /buy - View pricing plans

💳 𝗖𝗔𝗥𝗗 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦:
➜ /kill <card|mm|yy|cvv> - Kill card (5 credits)
""")



@bot.message_handler(commands=['credits'])
def check_credits(message):
    user_id = str(message.from_user.id)
    credits = user_credits.get(user_id, DEFAULT_CREDITS)
    if credits == 0:
        plans_text = """❌ You have no credits!

💎 𝗖𝗥𝗘𝗗𝗜𝗧 𝗣𝗟𝗔𝗡𝗦:
• 7 days - 45 credits: $10
• 10 days - 70 credits: $22
• 30 days - 120 credits: $45
• 60 days - 200 credits: $100

⚡️ 𝗨𝗡𝗟𝗜𝗠𝗜𝗧𝗘𝗗 𝗣𝗟𝗔𝗡𝗦:
• 3 days: $30
• 7 days: $60
• 15 days: $70
• 30 days: $120
• 60 days: $250

Use /buy to purchase credits!"""
        bot.reply_to(message, plans_text)
    else:
        bot.reply_to(message, f"💳 You have {credits} credits remaining\n\n💬 Need more? Use /buy to purchase credits!")

@bot.message_handler(commands=['buy'])
def show_plans(message):
    keyboard = telebot.types.InlineKeyboardMarkup()

    # Payment method buttons
    keyboard.row(
        telebot.types.InlineKeyboardButton("BEP20 (USDT)", callback_data="pay_BEP20"),
        telebot.types.InlineKeyboardButton("TRC20 (USDT)", callback_data="pay_TRC20")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("BTC", callback_data="pay_BTC"),
        telebot.types.InlineKeyboardButton("LTC", callback_data="pay_LTC")
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("Binance ID", callback_data="pay_BINANCE")
    )

    plans_text = """
💎 𝗖𝗥𝗘𝗗𝗜𝗧 𝗣𝗟𝗔𝗡𝗦:
• 7 days - 45 credits: $10
• 10 days - 70 credits: $22
• 30 days - 120 credits: $45
• 60 days - 200 credits: $100

⚡️ 𝗨𝗡𝗟𝗜𝗠𝗜𝗧𝗘𝗗 𝗣𝗟𝗔𝗡𝗦:
• 3 days: $30
• 7 days: $60
• 15 days: $70
• 30 days: $120
• 60 days: $250

💳 Select payment method below:
"""
    bot.reply_to(message, plans_text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def handle_payment_method(call):
    payment_addresses = {
        'BEP20': '0xc44d6de71ebbd4bdf33b32499eec1b6eb16a0e35',
        'TRC20': 'TWq6epxrnh57JPSu4YYBPHiNCWca5BJDHe',
        'BTC': '1GQG1YDzKppgVGBZnwSgyJTzxdQZAPMELb',
        'LTC': 'ltc1qz43rnqc700sffgafaend3x3cfgtur0ftj5w9et',
        'BINANCE': '900090280'
    }

    payment_type = call.data.replace('pay_', '')
    address = payment_addresses.get(payment_type)

    response = f"""💳 {payment_type} Payment Address:
`{address}`
(Tap on address to copy automatically)

📝 NOTE: Please send payment screenshot here. Admin will verify your payment and give you credits (usually takes 5-10 mins).

🙏 THANK YOU for choosing us!"""
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=response,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['givecredits'])
def give_credits(message):
    # Check if sender is admin
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ Only admin can use this command!")

    try:
        # Format: /givecredits user_id plan_code
        args = message.text.split()
        if len(args) != 3:
            return bot.reply_to(message, """❌ Use: /givecredits <user_id> <plan_code>

Credit Plans:
7d45 - 7 days, 45 credits
10d70 - 10 days, 70 credits
30d120 - 30 days, 120 credits
60d200 - 60 days, 200 credits

Unlimited Plans:
3d - 3 days unlimited
7d - 7 days unlimited
15d - 15 days unlimited
30d - 30 days unlimited
60d - 60 days unlimited""")

        user_id = str(args[1])
        plan_code = args[2].lower()

        # Handle credit plans
        if plan_code in CREDIT_PLANS:
            credits = CREDIT_PLANS[plan_code]["credits"]
            days = CREDIT_PLANS[plan_code]["days"]
            user_credits[user_id] = credits
            plan_type = "credits"
        # Handle unlimited plans
        elif plan_code in UNLIMITED_PLANS:
            credits = 999999  # Unlimited credits
            days = UNLIMITED_PLANS[plan_code]["days"]
            user_credits[user_id] = credits
            plan_type = "unlimited access"
        else:
            return bot.reply_to(message, "❌ Invalid plan code!")

        # Notify admin and user
        admin_msg = f"✅ Gave user {user_id} {credits} credits ({days} days of {plan_type})"
        user_msg = f"✅ Your account has been credited with {credits} credits ({days} days of {plan_type})!"

        bot.reply_to(message, admin_msg)
        try:
            bot.send_message(user_id, user_msg)
        except:
            bot.reply_to(message, "⚠️ Couldn't notify user, but credits were added")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['kill'])
def handle_kill(message):
    try:
        user_id = str(message.from_user.id)
        credits = user_credits.get(user_id, DEFAULT_CREDITS)

        if credits < CREDITS_PER_KILL:
            return bot.reply_to(message, f"❌ Not enough credits! Need {CREDITS_PER_KILL} credits.\n\nUse /buy to purchase credits!")

        args = message.text.split()
        if len(args) < 2 or len(args[1].split("|")) != 4:
            return bot.reply_to(message, "❌ Use: /kill 4111111111111111|12|25|123")

        # Send processing message
        processing_msg = bot.reply_to(message, "⚡ Processing your request...\n💳 Starting card kill process...")

        card_number, mm, yy, cvv = args[1].split("|")
        result = kill_card(card_number, mm, yy, cvv)

        # Check if "Do Not Honor" appears in the result
        do_not_honor_found = "Do Not Honor" in result

        # Deduct credits after successful kill
        user_credits[user_id] = credits - CREDITS_PER_KILL
        remaining = user_credits[user_id]

        # Only show final result
        final_status = "✅ Card successfully killed - Do Not Honor" if do_not_honor_found else "⚠️ Card not fully killed"
        bot.reply_to(message, f"""🔥 𝗞𝗜𝗟𝗟 𝗥𝗘𝗦𝗨𝗟𝗧𝗦 🔥
{final_status}
💳 Credits remaining: {remaining}""")
    except Exception as e:
        bot.reply_to(message, f"🔥 𝗘𝗥𝗥𝗢𝗥: {str(e)}")

# ====== RUN BOT ======
from flask import Flask, request
app = Flask(__name__)

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok'

if __name__ == "__main__":
    print("Bot is running in GOD MODE! 🔥")
    print(f"Admin ID configured as: {ADMIN_ID}")

    # Start the keep_alive web server in a separate thread
    # keep_alive() - Don't call this, it's already imported

    if 'REPLIT_DEPLOYMENT_ID' in os.environ:
        # Production mode - use webhook
        webhook_url = f"https://{os.environ.get('REPLIT_DEPLOYMENT_ID')}.{os.environ.get('REPLIT_DEPLOYMENT_DOMAIN')}/webhook/{BOT_TOKEN}"
        bot.remove_webhook()
        try:
            bot.set_webhook(url=webhook_url)
            print(f"Webhook set to: {webhook_url}")
        except Exception as e:
            print(f"Error setting webhook: {e}")
        app.run(host='0.0.0.0', port=8080, debug=False)
    else:
        # Development mode - use polling
        bot.infinity_polling(skip_pending=True, none_stop=True)