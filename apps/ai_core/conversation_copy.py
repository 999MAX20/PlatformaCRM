"""Localized deterministic workflow messages; facts come from domain results."""
COPY = {
    "analytics_read_only": ("В аналитике доступны вопросы и отчёты. Для изменения записей откройте «Работа с CRM».", "Аналитикада сұрақтар мен есептер қолжетімді. Жазбаларды өзгерту үшін «CRM-мен жұмыс» бөлімін ашыңыз.", "Analytics supports questions and reports. Open Work with CRM to change records."),
    "review": ("Проверьте предложенные действия и подтвердите выполнение.", "Ұсынылған әрекеттерді тексеріп, орындалуын растаңыз.", "Review the proposed actions and confirm execution."),
    "completed": ("Действия выполнены. Результаты показаны ниже.", "Әрекеттер орындалды. Нәтижелер төменде көрсетілген.", "The actions are complete. Results are shown below."),
    "cancelled": ("Ожидающие действия отменены. Уже выполненные изменения сохранены.", "Күтілген әрекеттер тоқтатылды. Орындалған өзгерістер сақталды.", "Pending actions were cancelled. Already completed changes were preserved."),
    "no_data": ("За выбранный период нет доступных данных для ответа.", "Таңдалған кезең бойынша жауап беруге қолжетімді деректер жоқ.", "No data is available for an answer for the selected period."),
    "choose_record": ("Уточните, какую запись нужно изменить: {choices}", "Қай жазбаны өзгерту қажет екенін нақтылаңыз: {choices}", "Clarify which record to change: {choices}"),
    "record_missing": ("Не удалось однозначно найти запись. Уточните её название или номер.", "Жазба бірмәнді табылмады. Оның атауын немесе нөмірін нақтылаңыз.", "The record could not be identified uniquely. Clarify its name or ID."),
    "period": ("Уточните начало и конец периода для анализа.", "Талдау кезеңінің басталу және аяқталу күндерін нақтылаңыз.", "Specify the start and end dates for the analysis."),
    "details": ("Уточните данные для действия.", "Әрекет үшін деректерді нақтылаңыз.", "Clarify the details needed for the action."),
    "partial": ("Часть действий выполнена. Для оставшихся требуется уточнение или новое подтверждение.", "Әрекеттердің бір бөлігі орындалды. Қалғандары үшін нақтылау немесе жаңа растау қажет.", "Some actions are complete. The remaining actions need clarification or new confirmation."),
}


def conversation_text(key, language="ru", **values):
    return COPY[key][{"ru": 0, "kk": 1, "en": 2}.get(language, 0)].format(**values)
