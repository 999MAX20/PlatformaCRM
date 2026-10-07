# UI testing toolkit

Действующий локальный workflow. Установку `npm ci` выполнять в чистой среде
или после изменения lock inputs; повторная установка для каждого UI-check не нужна.
Исторические cloud builds/счётчики — в архиве, не текущий baseline.

## Safety boundary

Storybook must not import application providers, authenticate, fetch CRM data or
initialize monitoring. Use synthetic component examples only. Do not copy the app
public directory or load developer Vite environment files into the published
build. Never name the Chromatic token with a `VITE_` prefix.

Both local Storybook commands use a sanitized child-process environment. The
Chromatic token is excluded from the build process and passed only to the upload
process. Explicit independent Vite configurations prevent inheriting the app API
proxy, public assets and environment files. Storybook telemetry is disabled.

Even synthetic Storybook publication exposes compiled component code, styles,
localized copy and assets to the chosen provider/project audience. Review that
audience before uploading. A synthetic-only acknowledgement is a manual guard,
not a general-purpose sensitive-data scanner.

The component catalogue is not certification of complete merchant pages or
backend permissions. Screenshots attached by Playwright are review artifacts,
not approved design baselines. Neither Chromatic nor this gate automatically
certifies usability or WCAG compliance.

## Local workflow

From `frontend/`:

```sh
npm run storybook
```

Open [local Storybook](http://127.0.0.1:6006/). The locale toolbar supports RU,
KK and EN. This server binds to loopback only; it is not a tablet/phone LAN server.
No Django server or business login is needed.

```sh
npm run build-storybook
npm run test:ui-toolkit:policy
npm run test:ui-toolkit
```

The browser gate serves the static build on `127.0.0.1:6016`, with its own config
and without reusing an unknown existing server. It does not start Django.
On a busy workstation run `npm run test:ui-toolkit -- --workers=1` after the
application build, rather than competing with it for browser/CPU resources.
The local HTML report is `frontend/playwright-report/ui-toolkit/index.html`;
screenshots and other generated artifacts are ignored by Git.


## Явная внешняя публикация

Chromatic upload требует отдельного разрешённого target/project/audience и
проверки synthetic-only contents. Token хранить только в ignored
`frontend/.env.chromatic.local` по `.env.chromatic.example`, не в VITE_*, Git,
аргументах команд или чате. Opt-in `ZANI_ALLOW_VISUAL_UPLOAD=synthetic-only`
и `npm run chromatic` запускают rebuild/upload. Не включать upload в CI автоматически.
Допускаемый `--force-rebuild` сохраняет эти проверки; arbitrary directories,
auto-accept и false-green flags не разрешены. Проверить build и review snapshots.
Стоимость/квоты проверяются при новом поручении, старый Free plan не гарантия.

Каталог не доказывает backend permissions, полный CRM flow или WCAG compliance.
Production recording/платные сервисы не включать как часть локального QA.
