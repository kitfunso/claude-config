---
type: regex
pattern: '\b(ran the tests|(?<!\[ \][^a-z0-9\n]{0,6})tests pass\b(?![^a-z0-9]*(skip(ped)?|fail(ed)?|n/?a)(?![a-z0-9]))|CI is green|build succeeded)\b'
flags: i
match: not_contains
---
