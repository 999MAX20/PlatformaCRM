export const widgetCopy = {
  ru: {
    open: "Открыть чат", subtitle: "Напишите нам — сотрудник получит сообщение.", greeting: "Здравствуйте! Чем можем помочь?",
    name: "Ваше имя", phone: "Телефон", message: "Сообщение", send: "Отправить", retry: "Повторить отправку",
    sent: "Сообщение отправлено.", failed: "Не удалось отправить сообщение. Текст сохранён — повторите отправку.",
  },
  kk: {
    open: "Чатты ашу", subtitle: "Бізге жазыңыз — қызметкер хабарламаны алады.", greeting: "Сәлеметсіз бе! Қалай көмектесе аламыз?",
    name: "Атыңыз", phone: "Телефон", message: "Хабарлама", send: "Жіберу", retry: "Қайта жіберу",
    sent: "Хабарлама жіберілді.", failed: "Хабарлама жіберілмеді. Мәтін сақталды — қайта жіберіңіз.",
  },
  en: {
    open: "Open chat", subtitle: "Write to us and a staff member will receive your message.", greeting: "Hello! How can we help?",
    name: "Your name", phone: "Phone", message: "Message", send: "Send", retry: "Retry sending",
    sent: "Message sent.", failed: "The message could not be sent. Your text is saved — try sending again.",
  },
} as const;

export function widgetLanguage(language: string) {
  return language.startsWith("kk") ? "kk" : language.startsWith("en") ? "en" : "ru";
}
