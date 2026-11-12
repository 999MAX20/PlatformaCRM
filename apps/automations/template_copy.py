from copy import deepcopy


TEMPLATE_COPY = {
    "en": {
        "appointment_created_prepare": (
            "New appointment: prepare the visit",
            "After an appointment is created, adds a task to prepare the client, service or resource.",
            "Prepare the client appointment",
        ),
        "message_received_handoff_task": (
            "New message: reply to the client",
            "When a client writes through a connected channel, CRM creates a task for a manual reply.",
            "Reply to the client in chat",
        ),
    },
    "kk": {
        "appointment_created_prepare": (
            "Жаңа жазба: қабылдауға дайындалу",
            "Жазба жасалған соң клиентті, қызметті немесе ресурсты дайындау тапсырмасын қосады.",
            "Клиенттің жазбасын дайындау",
        ),
        "message_received_handoff_task": (
            "Жаңа хабарлама: клиентке жауап беру",
            "Клиент қосылған арнаға жазғанда, CRM қолмен жауап беру тапсырмасын жасайды.",
            "Чатта клиентке жауап беру",
        ),
    },
}


def template_payload(template, language):
    payload = deepcopy({key: value for key, value in template.items() if key != "key"})
    copy = TEMPLATE_COPY.get(language, {}).get(template["key"])
    if copy:
        payload["name"], payload["description"], payload["actions"][0]["config"]["title"] = copy
    return payload
