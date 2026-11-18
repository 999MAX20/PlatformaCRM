import re


_DIGITS = dict(zip(
    "ноль один два три четыре пять шесть семь восемь девять".split(), "0123456789"
))
_DIGITS.update(zip("нөл бір екі үш төрт бес алты жеті сегіз тоғыз".split(), "0123456789"))
_DIGITS.update(zip("zero one two three four five six seven eight nine".split(), "0123456789"))
_DIGITS["нуль"] = "0"
_WORD = "(?:" + "|".join(_DIGITS) + ")"
_LABEL = r"\b(?:телефон(?:ы|і)?(?:\s+(?:номер[іа]?|нөмірі))?|нөмірі|phone(?: number)?)\s*[:—–-]?\s*"
_MONTH = (
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|"
    r"(?:қаңтар|ақпан|наурыз|сәуір|мамыр|маусым|шілде|тамыз|қыркүйек|қазан|қараша|желтоқсан)(?:да|де)?|"
    r"January|February|March|April|May|June|July|August|September|October|November|December)\b"
)
_DATE_AFTER_SEPARATOR = r"[,;]\s*(?:0?[1-9]|[12][0-9]|3[01])(?:\s+" + _MONTH + r"|\.(?:0?[1-9]|1[0-2])\.[0-9]{4}\b)"
_PHONE = re.compile(
    r"(?P<label>" + _LABEL + r")"
    r"(?P<plus>(?:плюс|plus|\+)[\s,]*)?"
    r"(?P<digits>" + _WORD + r"(?:[\s,\-]+" + _WORD + r"){6,14})"
    r"(?=\s*(?:" + _DATE_AFTER_SEPARATOR + r"|[,;]?\s*(?:[.!?]|$|\b(?:на|к|для|at|for)\b)))",
    re.IGNORECASE,
)


def normalize_spoken_phone(text):
    """Preserve each explicitly dictated digit; never infer a missing digit."""
    def replace(match):
        digits = "".join(_DIGITS[word.lower()] for word in re.split(r"[\s,\-]+", match["digits"]))
        return match["label"] + ("+" if match["plus"] else "") + digits

    return _PHONE.sub(replace, text)


def ambiguous_spoken_phone(text):
    normalized = normalize_spoken_phone(text)
    # Unexpected words after a phone label are not evidence of a usable number.
    if re.search(_LABEL + r"(?:дұрыс\s*[:—–-]?\s*|номер[іа]?\s+дұрыс\s*[:—–-]?\s*)" + _WORD,
                 normalized, re.IGNORECASE):
        return True
    if re.search(r"\btelefon\s+(?:nömr\w*|nom\w*|number)\b", normalized, re.IGNORECASE):
        return True
    return bool(re.search(_LABEL + r"(?:(?:плюс|plus)\b|\+\s*(?=[^\W\d_])|" + _WORD + r"\b)",
                          normalized, re.IGNORECASE))
