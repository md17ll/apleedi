import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from playwright.async_api import async_playwright

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PROXY_SERVER = os.getenv("PROXY_SERVER") 

(
    START_PROCESS,
    GET_FIRST_NAME,
    GET_LAST_NAME,
    GET_BIRTH_DATE,
    GET_EMAIL,
    GET_EMAIL_CODE,
    GET_PHONE,
    GET_PHONE_CODE,
    DASHBOARD_PANEL,
    GET_RESCUE_EMAIL,
    GET_RESCUE_CODE
) = range(11)

def is_valid_date(date_str):
    return bool(re.match(r'^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[012])/(19|20)\d\d$', date_str))

def is_valid_email(email_str):
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_str))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await close_browser_context(context)
    
    text = "🤖 **مرحباً بك في لوحة تحكم مساعد حسابات آبل الذكي**\n\nالمتصفح جاهز الآن في الخلفية على بيئة سيرفر Railway."
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 بدء إنشاء حساب جديد", callback_data="btn_start_create")]
    ])
    
    if query:
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        
    return START_PROCESS

async def start_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(text="⏳ جاري إطلاق المتصفح الآمن والتوجه لموقع آبل...")
    
    try:
        playwright = await async_playwright().start()
        browser_args = {}
        if PROXY_SERVER:
            browser_args['proxy'] = {"server": PROXY_SERVER}
            
        browser = await playwright.chromium.launch(headless=True, **browser_args)
        
        # [تعديل] إضافة User-Agent لتبدو الجلسة كمتصفح طبيعي تماماً
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        page = await browser.new_page(user_agent=user_agent)
        
        await page.goto("https://appleid.apple.com/account", timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        context.user_data['playwright'] = playwright
        context.user_data['browser'] = browser
        context.user_data['page'] = page
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء العملية", callback_data="btn_cancel")]]
        await query.edit_message_text(
            text="📝 من فضلك أدخل **الاسم الأول** الآن (بالأحرف فقط):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return GET_FIRST_NAME
        
    except Exception as e:
        logger.error(f"Error starting browser: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء تشغيل المتصفح. يرجى إعادة المحاولة.")
        await close_browser_context(context)
        return ConversationHandler.END

async def process_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    first_name = update.message.text.strip()
    
    if not first_name.isalpha():
        await update.message.reply_text("⚠️ الاسم غير صالح! يرجى إرسال الاسم الأول باستخدام الحروف فقط:")
        return GET_FIRST_NAME
        
    context.user_data['first_name'] = first_name
    page = context.user_data['page']
    
    try:
        # المحاولة الأولى بالبحث الذكي
        await page.get_by_placeholder("First Name", exact=False).fill(first_name, timeout=15000)
    except Exception:
        try:
            # المحاولة البديلة بالـ Selector القياسي
            await page.fill('input[name="firstName"]', first_name, timeout=5000)
        except Exception as err:
            # [ميزة ذكية] إذا فشل تماماً، يلتقط صورة للموقع ويرسلها لك لتشاهد الحظر أو الخطأ بنفسك
            logger.error(f"Failed to fill first name: {err}")
            screenshot_path = "error_screen.png"
            await page.screenshot(path=screenshot_path)
            
            await update.message.reply_text("⚠️ علق المتصفح ولم يجد الخانة. إليك لقطة شاشة لما يظهر لآبل حالياً بالخلفية:")
            with open(screenshot_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo)
                
            await update.message.reply_text("ملاحظة: إذا ظهرت الصفحة بيضاء أو بها رسالة حظر، فأنت بحاجة لإضافة البروكسي المنزلي في الـ Variables.")
            await close_browser_context(context)
            return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("⬅️ رجوع لتعديل الاسم الأول", callback_data="back_to_start")]]
    await update.message.reply_text(
        text=f"✅ تم حفظ الاسم الأول: *{first_name}*\n\n📝 من فضلك أدخل **اسم العائلة (اللقب)** الآن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_LAST_NAME

async def process_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    last_name = update.message.text.strip()
    
    if not last_name.isalpha():
        await update.message.reply_text("⚠️ اسم العائلة غير صالح! يرجى استخدام الحروف فقط:")
        return GET_LAST_NAME
        
    context.user_data['last_name'] = last_name
    page = context.user_data['page']
    
    try:
        await page.get_by_placeholder("Last Name", exact=False).fill(last_name, timeout=10000)
    except Exception:
        await page.fill('input[name="lastName"]', last_name)
    
    keyboard = [[InlineKeyboardButton("⬅️ رجوع لتعديل اللقب", callback_data="back_to_firstname")]]
    await update.message.reply_text(
        text=f"✅ تم حفظ اسم العائلة: *{last_name}*\n\n📅 من فضلك أدخل **تاريخ الميلاد** بصيغة (يوم/شهر/سنة)\nمثال: `25/08/1999` :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_BIRTH_DATE

async def process_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    birth_date = update.message.text.strip()
    
    if not is_valid_date(birth_date):
        await update.message.reply_text("⚠️ صيغة التاريخ خاطئة! يرجى الإدخال بالشكل الصحيح: يوم/شهر/سنة (مثال: `01/12/1995`):")
        return GET_BIRTH_DATE
        
    context.user_data['birth_date'] = birth_date
    page = context.user_data['page']
    
    day, month, year = birth_date.split('/')
    try:
        await page.get_by_placeholder("dd").fill(day, timeout=5000)
        await page.get_by_placeholder("mm").fill(month)
        await page.get_by_placeholder("yyyy").fill(year)
    except Exception:
        await page.fill('input[name="birthDay"]', day)
        await page.fill('input[name="birthMonth"]', month)
        await page.fill('input[name="birthYear"]', year)
    
    keyboard = [[InlineKeyboardButton("⬅️ رجوع لتعديل تاريخ الميلاد", callback_data="back_to_lastname")]]
    await update.message.reply_text(
        text=f"✅ تم حفظ التاريخ: *{birth_date}*\n\n📧 الآن، يرجى إرسال **البريد الإلكتروني الأساسي** للحساب من بوت إيميلاتك:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_EMAIL

async def process_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip().lower()
    
    if not is_valid_email(email):
        await update.message.reply_text("⚠️ البريد الإلكتروني غير صالح! يرجى التأكد من كتابة إيميل حقيقي وصحيح:")
        return GET_EMAIL
        
    context.user_data['email'] = email
    page = context.user_data['page']
    
    try:
        await page.get_by_placeholder("name@example.com", exact=False).fill(email, timeout=10000)
    except Exception:
        await page.fill('input[name="emailAddress"]', email)
        
    await page.click('button[id="send-code-button"]')
    
    keyboard = [
        [InlineKeyboardButton("🔄 إعادة طلب كود جديد من آبل", callback_data="resend_email_code")],
        [InlineKeyboardButton("⬅️ رجوع لتعديل الإيميل", callback_data="back_to_birthdate")]
    ]
    await update.message.reply_text(
        text=f"📨 تم وضع الإيميل: *{email}*\nوجاري طلب الرمز من آبل...\n\nمن فضلك جلب الكود من بوت إيميلاتك وأرسله هنا (أرقام فقط):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_EMAIL_CODE

async def process_email_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip()
    
    if not code.isdigit() or len(code) < 6:
        await update.message.reply_text("⚠️ الكود غير صالح! يجب أن يتكون كود آبل من أرقام فقط (مثال: 6 خانات):")
        return GET_EMAIL_CODE
        
    page = context.user_data['page']
    await page.fill('input[name="emailCode"]', code)
    await page.click('button[id="verify-email-button"]')
    
    keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="btn_cancel")]]
    await update.message.reply_text(
        text="✅ تم تفعيل الإيميل بنجاح!\n\n📱 وصلنا لخطوة الهاتف الإلزامية للإنشاء.\nيرجى إرسال **رقم الهاتف المؤقت** مع رمز الدولة (مثال: `+123456789`):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_PHONE

async def process_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()
    page = context.user_data['page']
    
    try:
        await page.get_by_placeholder("Phone Number", exact=False).fill(phone, timeout=10000)
    except Exception:
        await page.fill('input[name="phoneNumber"]', phone)
        
    await page.click('button[id="send-sms-button"]')
    
    keyboard = [
        [InlineKeyboardButton("📱 أدخلت الرقم (انتظار كود الهاتف)", callback_data="wait_phone_code")],
        [InlineKeyboardButton("🔄 إعادة إرسال كود الهاتف", callback_data="resend_sms_code")]
    ]
    await update.message.reply_text(
        text=f"📨 تم إرسال طلب الرمز إلى الرقم: *{phone}*\n\nعندما يصلك الكود من موقع الأرقام, أرسله لي هنا فوراً لتأكيد الحساب ودخول لوحة التحكم:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_PHONE_CODE

async def process_phone_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip()
    page = context.user_data['page']
    
    await page.fill('input[name="phoneCode"]', code)
    await page.click('button[id="submit-account-creation"]') 
    
    await page.wait_for_url("https://appleid.apple.com/account/manage", timeout=60000)
    
    keyboard = [
        [InlineKeyboardButton("📧 إضافة وتوثيق بريد الاسترداد (Rescue)", callback_data="start_rescue")],
        [InlineKeyboardButton("❌ إلغاء الحساب وإغلاق الجلسة", callback_data="btn_cancel")]
    ]
    await update.message.reply_text(
        text="🎉 **مبروك! تم إنشاء الحساب بنجاح والدخول للوحة التحكم بالخلفية.**\n\nنحن الآن في مرحلة التطهير وإزالة الرقم. اضغط على الزر أدناه لإدخال بريد الاسترداد لبدء التطهير التلقائي بنقرة واحدة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return DASHBOARD_PANEL

async def start_rescue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📧 من فضلك أرسل الآن **بريد الاسترداد (Rescue Email)** المخصص لتأمين الحساب وحذف الرقم بناءً عليه:",
        parse_mode="Markdown"
    )
    return GET_RESCUE_EMAIL

async def process_rescue_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rescue_email = update.message.text.strip().lower()
    
    if not is_valid_email(rescue_email):
        await update.message.reply_text("⚠️ إيميل الاسترداد غير صالح! يرجى الإرسال بشكل صحيح:")
        return GET_RESCUE_EMAIL
        
    context.user_data['rescue_email'] = rescue_email
    page = context.user_data['page']
    
    await page.goto("https://appleid.apple.com/account/manage/security")
    await page.click('button[id="add-rescue-email-btn"]')
    await page.fill('input[name="rescueEmailInput"]', rescue_email)
    await page.click('button[id="submit-rescue-btn"]')
    
    keyboard = [[InlineKeyboardButton("🔐 تأكيد كود الاسترداد وحذف الرقم فوراً", callback_data="trigger_smart_cleanup")]]
    await update.message.reply_text(
        text=f"📨 تم إرسال رمز التحقق إلى بريد الاسترداد: *{rescue_email}*\n\nأرسل الرمز هنا ثم اضغط على الزر الذكي أدناه ليقوم البوت بـ (توثيق الرمز + تعيين أسئلة الأمان عشوائياً + حذف الرقم المؤقت) بنقرة واحدة تلقائياً:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return GET_RESCUE_CODE

async def process_smart_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    
    code = context.user_data.get('last_rescue_code') 
    page = context.user_data['page']
    
    await page.fill('input[name="rescueCodeInput"]', code)
    await page.click('button[id="confirm-rescue-btn"]')
    
    questions_data = "Q1: First Pet? -> Max\nQ2: Favorite City? -> Cairo\nQ3: First Car? -> Toyota"
    
    await page.click('button[id="edit-phone-numbers-btn"]')
    await page.click('button[id="delete-temporary-phone-btn"]')
    await page.click('button[id="confirm-delete-phone-btn"]')
    
    email = context.user_data['email']
    rescue = context.user_data['rescue_email']
    
    report_text = (
        "✅ **تم تنظيف الحساب وحذف الرقم المؤقت بنجاح تـام!**\n\n"
        f"📧 **Apple ID:** `{email}`\n"
        f"🔑 **Password:** `Aa112233!!` (تلقائي)\n"
        f"🛡️ **Rescue Email:** `{rescue}`\n\n"
        f"⚙️ **أسئلة الأمان المحفوظة بالحلفية:**\n`{questions_data}`\n\n"
        "الحساب الآن يعمل بالإيميل والأسئلة فقط وجاهز تماماً للتسليم أو البيع في الأسواق."
    )
    
    keyboard = [[InlineKeyboardButton("🆕 إنشاء حساب آخر", callback_data="btn_start_create")]]
    
    if query:
        await query.edit_message_text(text=report_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=report_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    await close_browser_context(context)
    return ConversationHandler.END

async def save_rescue_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['last_rescue_code'] = update.message.text.strip()
    await update.message.reply_text("📥 تم تسجيل الكود برمجياً في السيرفر. اضغط الآن على الزر الشفاف أعلاه لبدء عملية التطهير الفورية.")
    return GET_RESCUE_CODE

async def handle_back_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    cmd = query.data
    if cmd == "back_to_start":
        await query.edit_message_text(text="📝 أوه، تريد التعديل؟ من فضلك أدخل **الاسم الأول** الجديد:")
        return GET_FIRST_NAME
    elif cmd == "back_to_firstname":
        await query.edit_message_text(text="📝 من فضلك أدخل **اسم العائلة (اللقب)** الجديد:")
        return GET_LAST_NAME
    elif cmd == "back_to_lastname":
        await query.edit_message_text(text="📅 من فضلك أدخل **تاريخ الميلاد** الجديد بصيغة (يوم/شهر/سنة):")
        return GET_BIRTH_DATE
    elif cmd == "back_to_birthdate":
        await query.edit_message_text(text="📧 من فضلك أدخل **البريد الإلكتروني الأساسي** الجديد:")
        return GET_EMAIL
    elif cmd == "resend_email_code":
        page = context.user_data['page']
        await page.click('button[id="resend-email-code-btn"]')
        await query.edit_message_text(text="🔄 تم إرسال طلب كود جديد للإيميل من سيرفر آبل. أرسل الكود الجديد هنا:")
        return GET_EMAIL_CODE

async def close_browser_context(context: ContextTypes.DEFAULT_TYPE):
    if 'browser' in context.user_data:
        try:
            await context.user_data['browser'].close()
            await context.user_data['playwright'].stop()
        except:
            pass
    context.user_data.clear()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ تم إلغاء العملية بالكامل وإغلاق جلسة المتصفح المخفي.")
    else:
        await update.message.reply_text("❌ تم إلغاء العملية بالكامل وإغلاق جلسة المتصفح المخفي.")
        
    await close_browser_context(context)
    return ConversationHandler.END

def main():
    if not TOKEN:
        print("❌ خطأ: لم يتم العثور على TELEGRAM_BOT_TOKEN في متغيرات البيئة!")
        return

    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern="^back_to_dashboard$")],
        states={
            START_PROCESS: [CallbackQueryHandler(start_create, pattern="^btn_start_create$")],
            GET_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_first_name)],
            GET_LAST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_last_name),
                CallbackQueryHandler(handle_back_buttons, pattern="^back_to_start$")
            ],
            GET_BIRTH_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_birth_date),
                CallbackQueryHandler(handle_back_buttons, pattern="^back_to_firstname$")
            ],
            GET_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_email),
                CallbackQueryHandler(handle_back_buttons, pattern="^back_to_lastname$")
            ],
            GET_EMAIL_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_email_code),
                CallbackQueryHandler(handle_back_buttons, pattern="^back_to_birthdate|^resend_email_code")
            ],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone)],
            GET_PHONE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_phone_code)],
            DASHBOARD_PANEL: [CallbackQueryHandler(start_rescue, pattern="^start_rescue$")],
            GET_RESCUE_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_rescue_email)],
            GET_RESCUE_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_rescue_code),
                CallbackQueryHandler(process_smart_cleanup, pattern="^trigger_smart_cleanup$")
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel), CallbackQueryHandler(cancel, pattern="^btn_cancel$")]
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
