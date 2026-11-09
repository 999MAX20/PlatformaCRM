(() => {
  'use strict';
  const config = window.PLATFORMA_CONFIG;
  const all = selector => [...document.querySelectorAll(selector)];
  const ru = Object.fromEntries(all('[data-i18n]').map(el => [el.dataset.i18n, el.innerHTML]));
  Object.assign(ru, {
    title: 'Platforma CRM — работа стоматологии в одном пространстве',
    meta: 'Platforma CRM для работы стоматологии: обращения, запись, расписание специалистов и задачи команды в одном рабочем пространстве.',
    heroAlt: 'Администратор встречает посетителя на ресепшене стоматологии',
    mainNav: 'Основная навигация', productNav: 'Разделы продукта', scenarioNav: 'Пример рабочего сценария',
    menu: 'Открыть меню', close: 'Закрыть',
    demoMessage: 'Здравствуйте! Хочу посмотреть Platforma CRM для стоматологии. Интересует демонстрация работы с обращениями, записью и задачами команды.',
    supportMessage: 'Здравствуйте! Нужна помощь со входом в Platforma CRM.',
    emailSubject: 'Демонстрация Platforma CRM для стоматологии',
  });
  const en = {
    skip:'Skip to content',featuresNav:'Features',howNav:'How it works',language:'Language',login:'Log in',menu:'Open menu',close:'Close',aiNav:'AI assistant',questionsNav:'Questions',requestDemo:'Request a demo',
    heroLabel:'CRM for dental practices',heroLine1:'Care for your patients.',heroLine2:'Clarity for your front desk.',heroDescription:'Inquiries, appointments and team tasks — in one workspace.',seeFeatures:'Explore the features',dayExample:'An example working day',ribbon1:'Reply to an inquiry',ribbon2:'Confirm an appointment',ribbon3:'Find a suitable time',inquiries:'Inquiries',appointments:'Appointments',team:'Team',
    featuresLabel:'Throughout the day',featuresTitle:'Many tasks.<br>One workspace.',featuresDescription:'When calls come in, appointments change and people wait for a reply, see what needs to happen next.',
    feature1Title:'Every inquiry has a next step',feature1Description:'A contact, conversation history and a responsible team member. Return to every conversation with its context intact.',feature2Title:'Appointments and schedules',feature2Description:'Specialist schedules, available times, rescheduling and cancellations. Organize the work around each visit.',feature3Title:'Clear responsibility',feature3Description:'Assign tasks, set due dates and record next steps. Team members see the work their permissions allow.',feature4Title:'History at hand',feature4Description:'Inquiries, appointments and notes connect to the client profile. Keep the context for the next visit, too.',
    workdayLabel:'From inquiry to appointment',workdayTitle:'The next step.<br>Right in front of you.',workdayDescription:'Explore one example: a new inquiry, finding a time and a task for the team.',tabMessage:'Receive an inquiry',tabCalendar:'Find a suitable time',tabTask:'Save the next step',overview:'Overview',clients:'Clients',calendar:'Calendar',tasks:'Tasks',workspace:'Workspace',example:'Illustrative scenario',sampleClient:'Aigerim K.',sampleClient2:'Daniyar S.',messagePreview:'Can I book a consultation?',messagePreview2:'Thank you, I will be on time.',newInquiry:'New inquiry',inbound:'Hello! Can I book a consultation?',outbound:'Hello! Let’s find a time that works for you. When are you available?',conversationContext:'The conversation keeps its history and responsible team member.',calendarDate:'Friday, 16 October',specialist1:'Aliya',specialist2:'Daniyar',specialist3:'Maria',consultation:'Consultation',repeatVisit:'Follow-up visit',availableSlot:'Available time',nextStep:'Next action',taskTitle:'Confirm the appointment',taskDescription:'Check the preferred time and confirm the visit after the client replies.',clientLabel:'Client',responsible:'Responsible',administrator:'Administrator',due:'Due',todayTime:'Today, 12:30',inProgress:'In progress',taskContextTitle:'The context stays with the task',taskContextDescription:'No need to find the conversation again: the client, inquiry and next step are linked.',scenarioCaption:'Fictional data illustrates the workflow. We will show the actual interface and available features in a demo.',
    assistantLabel:'AI alongside your team',assistantTitle:'Helps with routine.<br>Keeps you in control.',assistantDescription:'The assistant uses your company’s knowledge to help with questions and booking. When a person is needed, it hands the conversation to a team member.',seeAssistant:'See it in a demo',ai1Title:'Answers from your knowledge',ai1Description:'Uses the information you prepare about your company, services and booking rules.',ai2Title:'Works within its permissions',ai2Description:'Creating inquiries or appointments depends on your settings and the permissions you grant.',ai3Title:'Brings in a team member',ai3Description:'Your team receives the conversation with its context and can continue it manually.',aiNote:'We confirm channels separately. Medical records, diagnoses and clinical decisions are outside the CRM’s scope.',
    questionsLabel:'Before we meet',questionsTitle:'Good<br>questions.',q1:'Is it only for dental practices?',a1:'Platforma CRM is a universal CRM for small businesses. We are starting with dental practices and focusing on the front desk’s daily work: inquiries, appointments, tasks and communication.',q2:'Do we have to use AI?',a2:'No. Clients, inquiries, the calendar and tasks work without AI. The assistant can be enabled separately for agreed scenarios.',q3:'Can we work across several branches?',a3:'The CRM supports branches within one business, staff access and branch-aware schedules. We will demonstrate the scenario that fits your team.',q4:'What about WhatsApp and Telegram?',a4:'We confirm the availability and connection requirements of each channel before launch. The demo distinguishes implemented features from scenarios that still need connection and verification.',q5:'How do we start, and what does it cost?',a5:'Start with a demo based on your workflow. We then agree on the available features, connections, pricing and timing. This page does not list fixed plans.',
    demoLabel:'Let’s start with your practice',demoTitle:'See how it could<br>work for you.',demoDescription:'Walk through a typical front-desk day and the CRM workflow you need.',whatsapp:'Message us on WhatsApp',emailAction:'Send an email',contactNote:'Your selected app will open with a prepared message.',demoSide:'First, a conversation.<br>Then, your workflow.',partOf:'Part of Platforma Digital',company:'Company details',privacy:'Privacy',legalName:'Platforma Digital LLP · BIN 260940027670',location:'Almaty, Kazakhstan',imageNote:'The photograph illustrates a working scenario.',loginTitle:'Log in to your workspace',loginDescription:'Use the CRM address provided by your team administrator. Contact us if you need help.',contactSupport:'Contact us',
    title:'Platforma CRM — one workspace for your dental practice',meta:'Platforma CRM for dental teams: inquiries, appointments, specialist schedules and team tasks in one workspace.',heroAlt:'An administrator welcomes a visitor at a dental practice reception',mainNav:'Main navigation',productNav:'Product sections',scenarioNav:'Example workflow',demoMessage:'Hello! I would like a demo of Platforma CRM for a dental practice, including inquiries, appointments and team tasks.',supportMessage:'Hello! I need help logging in to Platforma CRM.',emailSubject:'Platforma CRM demo for a dental practice',
  };
  const kk = {
    skip:'Мазмұнға өту',featuresNav:'Мүмкіндіктер',howNav:'Қалай жұмыс істейді',language:'Тіл',login:'Кіру',menu:'Мәзірді ашу',close:'Жабу',aiNav:'AI көмекші',questionsNav:'Сұрақтар',requestDemo:'Демонстрация сұрау',
    heroLabel:'Стоматологияға арналған CRM',heroLine1:'Пациентке — көңіл.',heroLine2:'Әкімшіге — жұмыс тәртібі.',heroDescription:'Өтініштер, қабылдауға жазылу және команда міндеттері — бір жұмыс кеңістігінде.',seeFeatures:'Мүмкіндіктерді қарау',dayExample:'Жұмыс күнінің мысалы',ribbon1:'Өтінішке жауап беру',ribbon2:'Жазылуды растау',ribbon3:'Уақыт таңдау',inquiries:'Өтініштер',appointments:'Жазылу',team:'Команда',
    featuresLabel:'Күнделікті жұмыс',featuresTitle:'Міндет көп.<br>Жұмыс кеңістігі бір.',featuresDescription:'Қоңырау келіп, қабылдау уақыты өзгеріп, жауап күтіп жатқанда, келесі қадамды білу маңызды.',feature1Title:'Әр өтініштің жалғасы бар',feature1Description:'Байланыс, хат алмасу тарихы және жауапты қызметкер. Әр әңгімеге сақталған мәліметтермен оралыңыз.',feature2Title:'Қабылдауға жазылу және кесте',feature2Description:'Мамандардың уақыты, бос аралықтар, уақытты ауыстыру және бас тарту. Қабылдауға қатысты ұйымдастыру жұмысы.',feature3Title:'Жауапкершілік анық',feature3Description:'Міндеттерді тағайындаңыз, мерзім мен келесі әрекетті белгілеңіз. Команда өз құқығы аясындағы жұмысты көреді.',feature4Title:'Тарих қол астында',feature4Description:'Өтініштер, жазылулар және ескертпелер клиент карточкасымен байланысты. Мәліметтер келесі қабылдауға да сақталады.',
    workdayLabel:'Өтініштен қабылдауға дейін',workdayTitle:'Келесі қадам<br>көз алдыңызда.',workdayDescription:'Бір жұмыс сценарийін қараңыз: жаңа өтініш, уақыт таңдау және командаға арналған міндет.',tabMessage:'Өтінішті қабылдау',tabCalendar:'Уақыт таңдау',tabTask:'Келесі қадамды сақтау',overview:'Шолу',clients:'Клиенттер',calendar:'Күнтізбе',tasks:'Міндеттер',workspace:'Жұмыс кеңістігі',example:'Сценарий мысалы',sampleClient:'Айгерім К.',sampleClient2:'Данияр С.',messagePreview:'Кеңес алуға жазылуға бола ма?',messagePreview2:'Рақмет, уақытында келемін.',newInquiry:'Жаңа өтініш',inbound:'Сәлеметсіз бе! Кеңес алуға жазылуға бола ма?',outbound:'Сәлеметсіз бе! Ыңғайлы уақытты таңдайық. Сізге қашан ыңғайлы?',conversationContext:'Әңгіме тарихы мен жауапты қызметкер диалогта сақталады.',calendarDate:'Жұма, 16 қазан',specialist1:'Әлия',specialist2:'Данияр',specialist3:'Мария',consultation:'Кеңес алу',repeatVisit:'Қайта қабылдау',availableSlot:'Бос уақыт',nextStep:'Келесі әрекет',taskTitle:'Жазылуды растау',taskDescription:'Ыңғайлы уақытты нақтылап, клиенттің жауабынан кейін қабылдауды растау.',clientLabel:'Клиент',responsible:'Жауапты',administrator:'Әкімші',due:'Мерзім',todayTime:'Бүгін, 12:30',inProgress:'Орындалуда',taskContextTitle:'Мәліметтер міндетпен бірге сақталады',taskContextDescription:'Диалогты қайта іздеудің қажеті жоқ: клиент, өтініш және келесі қадам өзара байланысты.',scenarioCaption:'Ойдан алынған деректер жұмыс логикасын көрсетеді. Нақты интерфейс пен қолжетімді мүмкіндіктерді демонстрацияда көрсетеміз.',
    assistantLabel:'AI командамен бірге',assistantTitle:'Күнделікті іске көмектеседі.<br>Бақылау өзіңізде.',assistantDescription:'Көмекші компания мәліметтерін пайдаланып, сұрақтарға жауап беруге және жазылуға көмектеседі. Адам қажет болса, диалогты қызметкерге береді.',seeAssistant:'Демонстрацияда көру',ai1Title:'Сіздің мәліметтеріңізге сүйенеді',ai1Description:'Компания, қызметтер және жазылу ережелері туралы дайындалған ақпаратты пайдаланады.',ai2Title:'Рұқсат аясында әрекет етеді',ai2Description:'Өтініш немесе жазылу жасау мүмкіндігі баптауларға және берілген құқықтарға байланысты.',ai3Title:'Қызметкерді қосады',ai3Description:'Команда диалогты сақталған мәліметтерімен қабылдап, әңгімені қолмен жалғастыра алады.',aiNote:'Қосылу арналарын бөлек келісеміз. Медициналық карталар, диагноздар және клиникалық шешімдер CRM құрамына кірмейді.',
    questionsLabel:'Танысу алдында',questionsTitle:'Маңызды<br>сұрақтар.',q1:'Бұл тек стоматологияға арналған ба?',a1:'Platforma CRM — шағын бизнеске арналған әмбебап CRM. Қазір стоматологиядан бастап, әкімшінің күнделікті жұмысына назар аударамыз: өтініштер, жазылу, міндеттер және қарым-қатынас.',q2:'AI қосу міндетті ме?',a2:'Жоқ. Клиенттер, өтініштер, күнтізбе және міндеттер AI-сыз жұмыс істейді. Көмекшіні келісілген сценарийлерге бөлек қосуға болады.',q3:'Бірнеше филиалмен жұмыс істеуге бола ма?',a3:'CRM бір бизнес ішіндегі филиалдарды, қызметкерлердің қолжетімділігін және филиалға байланысты кестені қолдайды. Сізге сәйкес сценарийді демонстрацияда көрсетеміз.',q4:'WhatsApp пен Telegram қалай қосылады?',a4:'Әр арнаның қолжетімділігі мен қосылу шарттарын іске қосу алдында растаймыз. Демонстрацияда дайын мүмкіндіктер мен әлі қосу және тексеру қажет сценарийлерді бөлек көрсетеміз.',q5:'Қалай бастауға болады және бағасы қанша?',a5:'Сіздің міндетіңізге негізделген демонстрациядан бастаймыз. Содан кейін қолжетімді мүмкіндіктерді, қосылымдарды, баға мен мерзімді келісеміз. Бұл бетте бекітілген тарифтер көрсетілмеген.',
    demoLabel:'Сіздің клиникаңыздан бастайық',demoTitle:'Сізде қалай жұмыс<br>істейтінін көрсетеміз.',demoDescription:'Әкімшінің әдеттегі жұмыс күнін талдап, CRM ішіндегі қажетті сценарийді көрсетеміз.',whatsapp:'WhatsApp арқылы жазу',emailAction:'Email жіберу',contactNote:'Таңдалған қосымша дайын хабарламамен ашылады.',demoSide:'Алдымен танысамыз.<br>Содан кейін — сіздің жұмыс сценарийіңіз.',partOf:'Platforma Digital құрамында',company:'Компания деректемелері',privacy:'Құпиялылық',legalName:'«Platforma Digital» ЖШС · БСН 260940027670',location:'Алматы, Қазақстан',imageNote:'Фотосурет жұмыс сценарийін бейнелейді.',loginTitle:'Жұмыс кеңістігіне кіру',loginDescription:'Команда әкімшісі берген CRM мекенжайын пайдаланыңыз. Көмек қажет болса, бізге жазыңыз.',contactSupport:'Бізбен байланысу',
    title:'Platforma CRM — стоматология жұмысы бір кеңістікте',meta:'Стоматология командасына арналған Platforma CRM: өтініштер, қабылдауға жазылу, мамандар кестесі және міндеттер бір жұмыс кеңістігінде.',heroAlt:'Әкімші стоматология ресепшенінде келушіні қарсы алады',mainNav:'Негізгі навигация',productNav:'Өнім бөлімдері',scenarioNav:'Жұмыс сценарийінің мысалы',demoMessage:'Сәлеметсіз бе! Стоматологияға арналған Platforma CRM демонстрациясын көргім келеді. Өтініштер, қабылдауға жазылу және команда міндеттері қызықтырады.',supportMessage:'Сәлеметсіз бе! Platforma CRM жүйесіне кіруге көмек қажет.',emailSubject:'Стоматологияға арналған Platforma CRM демонстрациясы',
  };
  const dictionaries = { ru, kk, en };
  Object.keys(dictionaries).forEach(lang => Object.assign(dictionaries[lang], window.PLATFORMA_PAGE_COPY?.[lang] || {}));
  Object.assign(ru, {telegram:'Написать в Telegram',contacts:'Контакты',contactEmail:'Электронная почта',allContacts:'Все контакты',aiPage:'AI-помощник',loginPage:'Вход в CRM'});
  Object.assign(en, {telegram:'Message us on Telegram',contacts:'Contact us',contactEmail:'Email',allContacts:'All contacts',aiPage:'AI assistant',loginPage:'Log in to CRM'});
  Object.assign(kk, {telegram:'Telegram арқылы жазу',contacts:'Байланыс',contactEmail:'Электрондық пошта',allContacts:'Барлық байланыс',aiPage:'AI көмекші',loginPage:'CRM жүйесіне кіру'});
  Object.assign(ru, {footerDescription:'Обращения, запись и работа команды.',footerProduct:'Продукт',footerCompany:'Компания',footerContact:'Связаться',footerAddress:'Юридический адрес: Алматы, ул. Прокофьева, д. 140, кв. 77',footerTop:'Наверх',footerHome:'Platforma CRM — на главную'});
  Object.assign(en, {footerDescription:'Inquiries, appointments and teamwork.',footerProduct:'Product',footerCompany:'Company',footerContact:'Get in touch',footerAddress:'Registered address: 140 Prokofyev Street, apartment 77, Almaty',footerTop:'Back to top',footerHome:'Platforma CRM — home'});
  Object.assign(kk, {footerDescription:'Өтініштер, жазылу және команда жұмысы.',footerProduct:'Өнім',footerCompany:'Компания',footerContact:'Байланысу',footerAddress:'Заңды мекенжай: Алматы, Прокофьев көшесі, 140 үй, 77 пәтер',footerTop:'Жоғары',footerHome:'Platforma CRM — басты бетке'});
  Object.assign(ru, {footerTagline:'Новые решения в IT',footerAbout:'О Platforma Digital',footerLegalAddress:'Юридический адрес',footerDocuments:'Документы',footerCountry:'Казахстан',footerNav:'Навигация по компании'});
  Object.assign(en, {footerTagline:'New solutions in IT',footerAbout:'About Platforma Digital',footerLegalAddress:'Registered address',footerDocuments:'Documents',footerCountry:'Kazakhstan',footerNav:'Company navigation'});
  Object.assign(kk, {footerTagline:'IT саласындағы жаңа шешімдер',footerAbout:'Platforma Digital туралы',footerLegalAddress:'Заңды мекенжай',footerDocuments:'Құжаттар',footerCountry:'Қазақстан',footerNav:'Компания навигациясы'});
  const footerGroups = all('.site-footer-directory details');
  Object.assign(ru, {footerPrivacyPolicy:'Политика конфиденциальности',footerTerms:'Условия использования',footerDataProcessing:'Обработка данных',footerAllDocuments:'Все документы'});
  Object.assign(kk, {footerPrivacyPolicy:'Құпиялылық саясаты',footerTerms:'Пайдалану шарттары',footerDataProcessing:'Деректерді өңдеу',footerAllDocuments:'Барлық құжаттар'});
  Object.assign(en, {footerPrivacyPolicy:'Privacy policy',footerTerms:'Terms of use',footerDataProcessing:'Data processing',footerAllDocuments:'All documents'});
  const footerMobile = matchMedia('(max-width: 640px)');
  function updateFooterLayout() {
    footerGroups.forEach(group => {
      group.open = !footerMobile.matches;
      group.querySelector('summary').tabIndex = footerMobile.matches ? 0 : -1;
    });
  }
  footerGroups.forEach(group => group.querySelector('summary').addEventListener('click', event => {
    if (!footerMobile.matches) event.preventDefault();
  }));
  footerMobile.addEventListener('change', updateFooterLayout);
  updateFooterLayout();
  const languageControl = document.getElementById('language');
  let language = 'ru';
  function setContent(element, value) {
    const fragments = value.split(/<br\s*\/?\s*>/i);
    element.replaceChildren(...fragments.flatMap((fragment, index) => index ? [document.createElement('br'), document.createTextNode(fragment)] : [document.createTextNode(fragment)]));
  }
  function applyLanguage(next) {
    language = Object.hasOwn(dictionaries, next) ? next : 'ru';
    const dict = dictionaries[language];
    document.documentElement.lang = language;
    all('[data-document-lang]').forEach(element => { element.hidden = element.dataset.documentLang !== language; });
    all('[data-i18n]').forEach(el => setContent(el, dict[el.dataset.i18n] ?? ru[el.dataset.i18n]));
    all('[data-aria]').forEach(el => el.setAttribute('aria-label', dict[el.dataset.aria]));
    all('[data-alt]').forEach(el => el.alt = dict[el.dataset.alt]);
    document.title = dict.title;
    document.querySelector('meta[name="description"]').content = dict.meta;
    document.querySelector('meta[property="og:title"]').content = dict.title;
    document.querySelector('meta[property="og:description"]').content = dict.meta;
    languageControl.value = language;
    languageControl.setAttribute('aria-label', dict.language);
    all('[data-whatsapp]').forEach(link => {
      const message = link.closest('dialog') ? dict.supportMessage : dict.demoMessage;
      link.href = `https://wa.me/${config.phone.replace(/\D/g, '')}?text=${encodeURIComponent(message)}`;
    });
    all('[data-email]').forEach(link => link.href = `mailto:${config.email}?subject=${encodeURIComponent(dict.emailSubject)}&body=${encodeURIComponent(dict.demoMessage)}`);
    all('[data-telegram]').forEach(link => link.href = `${config.telegramUrl}?text=${encodeURIComponent(dict.demoMessage)}`);
    all('a[href]').forEach(link => {
      const href = link.getAttribute('href');
      if (!href || !/^(?:\/landing\/[a-z][a-z-]*\.html|\/)(?:[?#]|$)/.test(href)) return;
      const destination = new URL(href, location.href);
      if (language === 'ru') destination.searchParams.delete('lang'); else destination.searchParams.set('lang', language);
      link.setAttribute('href', `${destination.pathname}${destination.search}${destination.hash}`);
    });
    try { localStorage.setItem('platforma-crm-language', language); } catch { /* The page remains usable when storage is unavailable. */ }
    const url = new URL(location.href);
    if (/^#legal-(ru|kk|en)-/.test(url.hash)) url.hash = url.hash.replace(/^#legal-(ru|kk|en)-/, `#legal-${language}-`);
    if (language === 'ru') url.searchParams.delete('lang'); else url.searchParams.set('lang', language);
    try { history.replaceState(null, '', url); } catch { /* Local file previews do not always allow history changes. */ }
  }
  let initial = new URL(location.href).searchParams.get('lang');
  if (!initial) { try { initial = localStorage.getItem('platforma-crm-language'); } catch { initial = 'ru'; } }
  applyLanguage(initial || 'ru');
  languageControl.addEventListener('change', () => applyLanguage(languageControl.value));
  all('[data-print-document]').forEach(button => button.addEventListener('click', () => window.print()));

  const menu = document.getElementById('mobile-nav');
  const menuButton = document.querySelector('.menu-toggle');
  function closeMenu(restoreFocus = false) {
    menu.hidden = true;
    menuButton.setAttribute('aria-expanded', 'false');
    if (restoreFocus) menuButton.focus();
  }
  menuButton.addEventListener('click', () => {
    menu.hidden = !menu.hidden;
    menuButton.setAttribute('aria-expanded', String(!menu.hidden));
  });
  menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => closeMenu()));
  document.addEventListener('click', event => { if (!event.target.closest('.header') && !menu.hidden) closeMenu(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !menu.hidden) closeMenu(true); });
  const header = document.querySelector('.header');
  const updateHeader = () => header.classList.toggle('scrolled', scrollY > 35);
  document.addEventListener('scroll', updateHeader, { passive: true });
  updateHeader();

  const tabs = all('[data-scenario]');
  const sideItems = all('.scenario-sidebar>span:not(:first-child)');
  function selectScenario(name, focus = false) {
    tabs.forEach(tab => {
      const active = tab.dataset.scenario === name;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
      if (active && focus) tab.focus();
    });
    sideItems.forEach(item => item.classList.remove('scenario-current'));
    sideItems[{ message: 1, calendar: 3, task: 4 }[name]].classList.add('scenario-current');
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectScenario(tab.dataset.scenario));
    tab.addEventListener('keydown', event => {
      let target;
      if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') target = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') target = 0;
      if (event.key === 'End') target = tabs.length - 1;
      if (target !== undefined) { event.preventDefault(); selectScenario(tabs[target].dataset.scenario, true); }
    });
  });

  let loginUrl;
  if (config.loginUrl) {
    try {
      const candidate = new URL(config.loginUrl, location.origin);
      if (candidate.protocol === 'https:' || (candidate.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(candidate.hostname))) loginUrl = candidate.href;
    } catch { /* Invalid deployment configuration falls back to the help dialog. */ }
  }
  all('[data-login]').forEach(link => {
    link.href = loginUrl || '/login';
    link.addEventListener('click', () => {
      try { localStorage.setItem('ai_smb_language', language); } catch { /* Sign-in remains available without browser storage. */ }
    });
  });
  all('[data-digital]').forEach(link => link.href = config.digitalUrl);
})();
