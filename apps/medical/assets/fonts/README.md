# Medical document fonts

Noto Sans Regular and Bold are embedded in generated PDFs for RU/KK/EN.
They use the existing CRM Noto Sans family; no system-font fallback is required.
The draft DOCX renderer names Noto Sans but does not embed these font files;
Word rendering and fallback fonts remain part of its pending visual acceptance.

Source: [notofonts/noto-fonts](https://github.com/notofonts/noto-fonts/tree/ffebf8c1ee449e544955a7e813c54f9b73848eac/hinted/ttf/NotoSans),
commit `ffebf8c1ee449e544955a7e813c54f9b73848eac`.
The unmodified upstream SIL Open Font License is in `LICENSE.txt`.

SHA256:

- NotoSans-Regular.ttf: `b85c38ecea8a7cfb39c24e395a4007474fa5a4fc864f6ee33309eb4948d232d5`
- NotoSans-Bold.ttf: `c976e4b1b99edc88775377fcc21692ca4bfa46b6d6ca6522bfda505b28ff9d6a`
