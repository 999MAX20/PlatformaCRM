# Frontend PlatformaCRM

React/TypeScript/Vite, Tailwind 4 через PostCSS; Node >=22.22 по
[package.json](package.json). Установка в чистой среде — `npm ci`; неизменное
рабочее окружение переустанавливать для каждой задачи не нужно.

Из этой папки: `npm run dev`, `npm run build`, `npm run check:bundle`.
Build включает i18n, TypeScript и app/widget production builds; не запускает
полный пользовательский flow. Точный выбор проверок — [testing](../docs/testing/testing.md).

[router](src/app/router.tsx) определяет reachable страницы; [api](src/api)
отделяет запросы от UI; [features](src/features) содержит предметные сценарии;
[components](src/components) — общие элементы. Цвета —
[semantic tokens](src/theme/semantic-tokens.json), тексты — существующий i18n слой.
RU/EN используют Manrope, KK — Noto Sans. API и скрытая кнопка не заменяют
серверные permissions. Клиентские secrets не помещать в VITE_*.

[Действующий UI-контракт](../docs/current/frontend.md),
[карта возможностей](../docs/pre-production/capabilities.md),
[Storybook и безопасный visual workflow](../docs/testing/ui-testing-toolkit.md).
