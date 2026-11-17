"""Customer reply language, shared by model replies and deterministic notices."""
import re
import unicodedata

from django.db import transaction


LANGUAGES = frozenset({"ru", "kk", "en"})
LANGUAGE_KEY = "customer_reply_language"
ACKNOWLEDGEMENTS = frozenset("да нет ага угу ок окей хорошо понятно спасибо пожалуйста yes no ok okay sure thanks thank you please иә жок жоқ жарайды рахмет рақмет".split())
SLOT_SELECTION = frozenset("вариант выбираю подходит пожалуйста option choose book please нұсқа таңдаймын жарайды".split())
WORDS = {
    "ru": frozenset("здравствуйте привет добрый день можно хочу сколько стоит цена цены есть ли у вас запись записаться когда завтра сегодня пожалуйста мне меня на русском ответьте отвечайте говорите напишите где адрес работаете нужен администратор оператор жалоба не это что как почему спасибо".split()),
    "kk": frozenset("сәлем салем сәлеметсіз сәлеметсізбе салеметсизбе сәлеметсіздерме ме ма бе ба пе па мен маған маган мені мени сіз сіздер сізде сизде біз биз бар бос қанша канша тұрады турады бағасы багасы баға бага керек ертең ертен бүгін бугин жазылу жазылғым жазылгым келеді келеди жазыламын болады бола қазақша казакша жауап беріңіз бериниз жазыңыз жазыныз рахмет рақмет кайда қайда сағат сагат уақыт уакыт".split()),
    "en": frozenset("hello hi good morning afternoon can could would do does is are i we you your me my the a an to for of with in on please how what when where why much price cost book booking appointment tomorrow today need want speak reply answer english thanks".split()),
}
PREFERENCES = {
    "ru": r"(?:по[- ]русски|на русском|\brussian\b|орысша|орыс тілінде)",
    "kk": r"(?:по[- ]казахски|на казахском|\bkazakh\b|қазақша|казакша|қазақ тілінде)",
    "en": r"(?:по[- ]английски|на английском|\benglish\b|ағылшынша|агылшынша|ағылшын тілінде)",
}
REQUEST = r"(?:отвеч\w*|ответ\w*|говор\w*|пиши\w*|напиш\w*|можно|давай\w*|please|reply|answer|speak|write|use|жауап|жаз\w*|сөйл\w*)"


def _plain_text(text):
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"https?://\S+|\S+@\S+|^[ \t]*>.*$", " ", text, flags=re.M)
    # Quoted material and product names must not choose the customer's language.
    text = re.sub(r'"[^"\n]*"|«[^»]*»|“[^”]*”', " ", text)
    return text


def _words(text):
    return re.findall(r"[^\W\d_]+", _plain_text(text), flags=re.UNICODE)


def _context_only(text):
    words = set(_words(text))
    return not words or words <= ACKNOWLEDGEMENTS or (bool(re.search(r"\d", text)) and words <= SLOT_SELECTION)


def explicit_language(text):
    chosen = None
    for sentence in re.split(r"[.!?\n]", _plain_text(text)):
        if not re.search(REQUEST, sentence):
            continue
        for clause in re.split(r"[,;]", sentence):
            if re.search(r"\b(?:не|not|don't)\b|емес", clause):
                continue
            matches = [(match.start(), language) for language, pattern in PREFERENCES.items()
                       for match in re.finditer(pattern, clause)
                       if re.search(REQUEST, clause) or re.fullmatch(r"\s*(?:" + pattern + r")\s*", clause)]
            if matches:
                chosen = max(matches)[1]
    return chosen


def language_signal(text):
    """Conservative offline fallback; qualification can resolve ambiguous text."""
    if language := explicit_language(text):
        return language
    words = _words(text)
    if _context_only(text):
        return None
    scores = {language: sum(word in vocabulary for word in words) for language, vocabulary in WORDS.items()}
    scores["kk"] += sum(bool(re.search("[әғқңөұүһі]", word)) for word in words)
    top = max(scores.values())
    winners = [language for language, score in scores.items() if score == top]
    if top and len(winners) == 1:
        return winners[0]
    if not top and len(words) >= 2 and all(re.fullmatch("[а-яё]+", word) for word in words):
        return "ru"
    return None


def _fallback(conversation):
    from apps.ai_core.models import AgentProfile
    language = AgentProfile.objects.filter(business_id=conversation.business_id,
        bot_id=conversation.bot_id, is_active=True).order_by("-updated_at", "-id").values_list("language", flat=True).first()
    language = language or conversation.bot.default_language
    return language if language in LANGUAGES else "ru"


def customer_reply_language(conversation, *, messages=None):
    saved = (conversation.metadata_json or {}).get(LANGUAGE_KEY) or {}
    saved = saved if isinstance(saved, dict) else {}
    if messages is None:
        messages = getattr(conversation, "_preview_messages", None)
    if conversation.pk:
        from apps.ai_core.models import AgentConversation
        query = conversation.messages.filter(direction="inbound")
        since = AgentConversation.objects.filter(inbox_conversation=conversation).values_list("memory_since", flat=True).first()
        if since:
            query = query.filter(created_at__gte=since)
        # Read the actual dialogue, not the model's truncated memory or outbound text.
        inbound = query.order_by("-created_at", "-pk").values("id", "text").iterator(chunk_size=100)
    else:
        inbound = reversed([item for item in messages or [] if item.get("direction") == "inbound"])
        preview = getattr(conversation, "_preview_language", None)
        if preview and preview[0] == len(messages or []):
            return preview[1]
    for item in inbound:
        if saved.get("message_id") == item.get("id") and saved.get("language") in LANGUAGES:
            return saved["language"]
        if language := language_signal(item.get("text", "")):
            return language
    return _fallback(conversation)


@transaction.atomic
def remember_customer_language(conversation, messages, language):
    """Only the latest classified inbound can advance the language checkpoint."""
    from apps.bots.models import BotConversation
    if not isinstance(language, str) or language not in LANGUAGES:
        return customer_reply_language(conversation, messages=messages)
    latest = next((item for item in reversed(messages) if item.get("direction") == "inbound"), None)
    if latest is None:
        return customer_reply_language(conversation, messages=messages)
    language = explicit_language(latest.get("text", "")) or language
    if _context_only(latest.get("text", "")):
        language = customer_reply_language(conversation, messages=messages)
    if conversation.pk is None:
        conversation._preview_language = (len(messages), language)
        return language
    current = BotConversation.objects.select_for_update().get(pk=conversation.pk,
        business_id=conversation.business_id, bot_id=conversation.bot_id)
    from apps.ai_core.inbox_runtime import assert_current_inbound
    assert_current_inbound(current)
    message_id = current.messages.filter(direction="inbound").order_by("-created_at", "-pk").values_list("pk", flat=True).first()
    if not message_id or message_id != latest.get("id"):
        return customer_reply_language(current)
    current.metadata_json = {**(current.metadata_json or {}), LANGUAGE_KEY: {"message_id": message_id, "language": language}}
    current.save(update_fields=["metadata_json", "updated_at"])
    conversation.metadata_json = current.metadata_json
    return language
