# Независимый privacy/security review

Построчно просмотрены все 30 файлов исходного staging commit `f83bcc5`, включая
исходный текст и конфигурацию. Дополнительно проверены все новые/изменённые
файлы текущего release candidate и тесты adapters. Это локальный engineering
review, а не legal review и не доказательство отсутствия неизвестных форматов
секретов.

## Пофайловые результаты исходного staging

| Файл | Результат просмотра |
|---|---|
| `.env.example` | Секретов не было; описание откладывало адаптеры, теперь отражает environment-only конфигурацию и пустые значения без credentials. |
| `.github/workflows/ci.yml` | CI не передавал секреты; добавлен import smoke-check. Unit tests и release guard уже запускались. |
| `.gitignore` | Runtime state, `.env`, базы, логи, виртуальные окружения и build outputs исключены; исключение для `.env.example` сохранено. |
| `CONTRIBUTING.md` | Не содержал приватных данных; расширены проверочные команды и release attribution requirement. |
| `LICENSE` | Apache-2.0 текст сохранён без придуманного правообладателя. Требуется подтверждение владельца и attribution до публикации. |
| `README.md` | Вводная описывала только mock и утверждала, что Telegram/provider не включены; текст исправлен и описывает opt-in интеграции, их потоки данных и локальный статус. |
| `SECURITY.md` | Политика повторяла устаревшее отсутствие adapters; теперь указывает optional disabled-by-default adapters и ссылается на privacy notes. |
| `docs/ARCHITECTURE.md` | Описывала только mock; дополнена контрактом, транспортными границами, отказами без раскрытия тела ответа и ограничениями передачи данных. |
| `docs/PRIVACY.md` | Уточнены данные, отправляемые provider-у и Telegram, локальное хранение и отсутствие сетевых вызовов по умолчанию. |
| `docs/THREATS.md` | Пересмотрена граница для remote model и Telegram; документированы HTTPS, allowlist-before-dispatch и остающиеся ограничения. |
| `src/harness/data/migrations/0001_initial.sql` | SQL статический; внешние значения параметризуются приложением. Ограничения ролей и owner-only scope сохранены; migration входит в wheel. |
| `src/harness/data/profiles/teseus-seed/README.md` | Seed прямо обозначен синтетическим/публичным, опциональным и не являющимся записью реальных событий; сохранён в wheel. |
| `src/harness/data/profiles/teseus-seed/persona.json` | Только публичная synthetic persona, без реальных разговоров или идентификаторов; включена в wheel. |
| `src/harness/data/profiles/teseus-seed/seed-memory.json` | Только публичные synthetic идеи; сохранён состав seed и имя `teseus-harness`, файл включён в wheel. |
| `pyproject.toml` | Зависимости отсутствуют, Python 3.11+ и Apache-2.0 заданы; metadata/license оставлены без фиктивного attribution. |
| `scripts/public-files.txt` | Allowlist расширен на review, adapters и mocked tests, чтобы новые артефакты были явными. |
| `scripts/release_guard.py` | Исходный guard сканировал только текущие файлы и не проверял Git history, remotes или symlinks. Исправлено: проверяются достижимые исторические blobs, текущие allowlisted файлы, remotes и ссылки; совпавшие значения не выводятся. |
| `src/harness/__init__.py` | Только версия пакета; проблем не обнаружено. |
| `src/harness/__main__.py` | Только вызов CLI entry point; проблем не обнаружено. |
| `src/harness/cli.py` | DB значения передаются параметрами, состояние локально. Диалог был жестко привязан к mock; добавлена инъекция Engine и выбор mock/provider из environment. Telegram запускается только отдельной явной командой. |
| `src/harness/engine.py` | Исходный контракт и mock не выполняли действий и не использовали сеть; контракт сохранён, добавлен тип обобщённой sanitized ошибки. |
| `src/harness/memory.py` | Owner proposals валидируются, SQL параметризован; forget не является secure erase (уже документировано). Изменений логики не потребовалось. |
| `src/harness/persona.py` | Проверяется структура локального JSON; данные берутся из файла владельца. Никакой сетевой или секретной обработки. |
| `src/harness/storage.py` | SQL пользовательских данных параметризован, foreign keys включены, миграции транзакционные; best-effort permissions явно не считаются шифрованием. |
| `templates/config.example.toml` | Без credentials; defaults остаются mock, новые интеграции выключены. |
| `templates/memory/README.md` | Синтетический шаблон без личных данных; корректно описывает обратимость и ограничения forgetting. |
| `templates/memory/owner-profile.md` | Пустой локальный шаблон; предупреждает, что это не access-control policy. |
| `templates/system-instruction.md` | Только текстовые ограничения модели; документ не полагается на prompt как на access-control boundary. |
| `tests/test_defaults.py` | Только синтетические данные; проверяет deterministic mock и пустую memory proposal. |
| `tests/test_vertical_slice.py` | Только временные каталоги и synthetic fixtures; проверяет bootstrap, SQLite rollback, seed и memory cycle. |

## Проверка добавленных adapters и исправлений

- `openai_compatible.py`: только HTTPS endpoint, environment-only secrets,
  ограниченный timeout, POST chat-completions; пользовательский текст и ответ
  не печатаются. Транспортные/форматные ошибки сведены к общему сообщению без
  provider body или исключения. Отправляется только текущий turn и persona name.
- `telegram.py`: HTTPS Bot API, ограниченный long poll, token читается только
  из environment и хранится в памяти процесса. Обрабатывается private text,
  группа исключена. Sender ID проверяется до callback, вызывающего engine;
  незнакомый пользователь получает общий отказ. Ошибки не раскрывают URL/token.
- `tests/test_adapters.py`: реальные сетевые вызовы отсутствуют; проверяются
  provider request и интеграция с dialogue, отсутствующая/невалидная
  конфигурация, timeout/error sanitization, malformed Telegram updates,
  отключённый default, неизвестный owner до dispatch, запрет group chat и
  environment requirements.
- Runtime migration и публичные seed assets размещены как package data, а
  установленные wheel/sdist проверены в отдельных локальных virtualenv;
  release guard учитывает эти assets и helper нормализации sdist.
- Документация описывает opt-in сетевые потоки и их последствия; CI импортирует
  оба adapter. Release guard работает по текущему дереву и reachable history.

## Findings / решение перед публикацией

Исправлены устаревшая документация о наличии интеграций и отсутствие проверки
Git history в release guard. В проверенных файлах не обнаружено credentials,
private key material, живых host paths или данных реального проекта. Это вывод
в рамках настроенных pattern scans и ручного просмотра, а не универсальная
гарантия.

Открытый release blocker: владелец должен подтвердить copyright ownership и
attribution/правообладателя, а также право на публикацию под Apache-2.0 и
использование имени. Placeholder attribution не выдуман, файл Apache-2.0
сохранён. До подтверждения проект остаётся только локальным кандидатом.
