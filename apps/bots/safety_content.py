"""Conservative customer boundary signals, not an authorization mechanism.

Pattern checks catch obvious attacks before paid classification. The model also
classifies intent; confidentiality still depends on withholding private sources.
"""
import re
import unicodedata


def _normalized(text):
    return "".join(char for char in unicodedata.normalize("NFKC", str(text)).casefold()
                   if unicodedata.category(char) != "Cf")


SECRET_VALUE = re.compile(
    r"\b(?:sk-or-v1-|sk-proj-|sk-live-|sk_live_)[a-z0-9_-]{8,}"
    r"|\b(?:authorization\s*:\s*)?bearer\s+[a-z0-9._~-]{12,}"
    r"|\b(?:api[_ -]?key|access[_ -]?token|secret[_ -]?key|database_url|password)\s*[:=]\s*[^\s\"']{6,}", re.I)
SECURITY_REQUEST = re.compile(
    r"(?:openrouter|api.?key|api.?ключ|секретн.{0,16}ключ|secret.{0,12}key|access.?token|\.env\b|парол|password|құпия.{0,16}кілт)"
    r"|(?:system.{0,8}prompt|системн.{0,12}(?:промпт|инструкц)|жүйелік.{0,12}нұсқау)"
    r"|(?:ignore|игнорируй|забудь).{0,30}(?:instructions|rules|правил|инструкц)"
    r"|(?:выполни|execute|run).{0,15}(?:sql|shell|команд|код)", re.I)
PRIVATE_REQUEST = re.compile(
    r"(?:покажи|найди|напомни|проверь|дай|скажи|какие|есть ли).{0,65}(?:мо[яюие].{0,10}запис|запис[ьиь].{0,15}(?:на имя|у |когда)|записан|истори[юя].{0,12}(?:клиент|посещ)|телефон.{0,12}(?:клиент|пациент))"
    r"|(?:show|find|remind|check|tell).{0,60}(?:my appointment|booking for|appointment for|client history|customer.{0,10}(?:phone|email))"
    r"|(?:менің.{0,20}(?:жазыл|кездесу)|клиент.{0,20}(?:телефон|тарих))", re.I)


def contains_secret(value):
    if isinstance(value, dict):
        return any(contains_secret(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_secret(item) for item in value)
    return bool(SECRET_VALUE.search(_normalized(value))) if isinstance(value, str) else False


def obvious_risk(text):
    normalized = _normalized(text)
    if contains_secret(text) or SECURITY_REQUEST.search(normalized):
        return "security_request"
    if PRIVATE_REQUEST.search(normalized):
        return "private_record_request"
    return ""


COPY = {
    "ru": {
        "boundary": "Извините, я могу помочь только с вопросами о компании, её услугах, товарах и записи. Чем могу помочь по вашему обращению?",
        "handoff": "Нужна помощь администратора. Я передал ему обращение; вы можете продолжить писать в этом чате.",
        "private_record_request": "Для проверки записи или личных данных нужна помощь администратора.",
        "security_request": "Запрос касается закрытой информации или запрещённого действия.",
        "off_topic": "Повторные вопросы вне тематики бизнеса.",
        "call_limit": "Достигнут лимит вызовов AI для этого диалога за24 часа.",
        "message_burst": "Слишком много сообщений за короткое время.",
        "message_too_long": "Сообщение превышает допустимую длину для AI.",
        "repeated_messages": "Повторяющиеся сообщения требуют внимания сотрудника.",
        "unsafe_context": "Материалы агента требуют проверки перед ответом клиенту.",
        "unsafe_output": "Ответ AI требует проверки перед отправкой клиенту.",
        "uncertain": "Не удалось безопасно определить тип обращения.",
    },
    "kk": {
        "boundary": "Кешіріңіз, мен тек компания, оның қызметтері, тауарлары және жазылу туралы сұрақтарға көмектесе аламын. Өтінішіңіз бойынша қалай көмектесейін?",
        "handoff": "Әкімшінің көмегі қажет. Өтінішті оған жібердім; осы чатқа жаза беруіңізге болады.",
        "private_record_request": "Жазылуды немесе жеке деректерді тексеру үшін әкімшінің көмегі қажет.",
        "security_request": "Сұрау жабық ақпаратқа немесе тыйым салынған әрекетке қатысты.",
        "off_topic": "Бизнес тақырыбына қатысы жоқ қайталанатын сұрақтар.",
        "call_limit": "Осы диалог үшін24 сағаттық AI сұрауларының шегіне жетті.",
        "message_burst": "Қысқа уақытта тым көп хабарлама түсті.",
        "message_too_long": "Хабарлама AI үшін рұқсат етілген ұзындықтан асады.",
        "repeated_messages": "Қайталанатын хабарламалар қызметкердің назарын қажет етеді.",
        "unsafe_context": "Клиентке жауап бермес бұрын агент материалдарын тексеру қажет.",
        "unsafe_output": "Жібермес бұрын AI жауабын тексеру қажет.",
        "uncertain": "Өтініш түрін қауіпсіз анықтау мүмкін болмады.",
    },
    "en": {
        "boundary": "Sorry, I can only help with questions about the company, its services, products and bookings. How can I help with your enquiry?",
        "handoff": "An administrator needs to help. I have passed your enquiry to them; you can continue writing in this chat.",
        "private_record_request": "An administrator needs to verify bookings or personal records.",
        "security_request": "The request concerns restricted information or a prohibited action.",
        "off_topic": "Repeated questions outside the business topic.",
        "call_limit": "The conversation AI call limit for24 hours has been reached.",
        "message_burst": "Too many messages arrived in a short time.",
        "message_too_long": "The message exceeds the AI length limit.",
        "repeated_messages": "Repeated messages need staff attention.",
        "unsafe_context": "Agent materials need review before replying to the customer.",
        "unsafe_output": "The AI reply needs review before sending to the customer.",
        "uncertain": "The enquiry could not be classified safely.",
    },
}


def safety_text(conversation, code):
    from apps.ai_core.models import AgentProfile
    language = AgentProfile.objects.filter(business_id=conversation.business_id,
        bot_id=conversation.bot_id, is_active=True).order_by("-updated_at", "-id").values_list("language", flat=True).first()
    return COPY.get(language or conversation.bot.default_language, COPY["ru"])[code]
