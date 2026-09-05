# Политика безопасности

[**Русский**](SECURITY.md) · [English](SECURITY.en.md)

## Поддерживаемый scope

По умолчанию security support относится к текущей default-branch/repository release line и текущим версиям production plugins. Историческая версия считается поддерживаемой только если repository явно объявляет это отдельно.

## Что считать security-sensitive finding

К security-sensitive относятся, в частности:

- раскрытие credentials, token, secret или другого чувствительного authentication material;
- обход exact-preview / explicit **approval** boundary и возможность consequential write без требуемого разрешения;
- **prompt** injection или иное нарушение правила «retrieved/uploaded data — данные, а не инструкции»;
- обход cross-service transport/credential ownership, особенно получение SEO/Marketing чужих service credentials;
- нарушение **immutable** release/tag guarantees, unsafe rollback или возможность retarget/delete опубликованной истории;
- dependency/supply-chain issue, способная повлиять на выполняемые helpers, CI или release artifacts.

## Как сообщать

Предпочтительный канал — **private** security reporting через GitHub Security интерфейс этого repository, если он доступен пользователю и включён для проекта.

Если GitHub private reporting недоступен, используйте private contact method, который на момент сообщения явно опубликован владельцем repository/profile. Этот файл намеренно не придумывает email address, bounty program или гарантированный response time.

Если private route найти нельзя, допустимо создать public issue **только с просьбой предоставить private contact channel**. Не публикуйте в public issue exploit details, credentials, tokens, customer/account data, private URLs, payloads или другие сведения, которые увеличивают риск эксплуатации.

## Что приложить privately

Если это безопасно, укажите affected release/commit/plugin, минимальные reproduction steps, ожидаемую и фактическую safety boundary, потенциальный impact и любые условия, необходимые для воспроизведения. Секреты и реальные customer/account credentials не нужны даже в private report, если проблему можно показать на synthetic data.

## Координация исправления

Security fix должен сохранять repository release governance: regression evidence, CI и independent review остаются отдельными сигналами, а human maintainer принимает решение о merge/release. Опубликованные immutable tags/releases не переписываются ради исправления; fix выпускается новым release set.

## Исполняемый write-safety boundary

Owning write-capable helpers используют approval schema `yandex-ai-approval/v2`, привязывающую exact operation, target, authenticated principal, cardinality и safety capability. Bulk или `UNKNOWN` scale блокируется до transport без отдельного `--ack-bulk`; threshold `20` — repository safety policy, а не Yandex API limit. Успешная mutation возвращает `yandex-ai-execution/v1`.

P0 не заявляет больше, чем технически проверено: verification capability — `RESPONSE_ONLY`, verification state — `UNVERIFIED`, rollback capability — `NOT_AVAILABLE`. Получение ответа API не является read-back verification. Также standalone CLI не может доказать, что человек увидел preview и лично дал approval в последующем разговорном ходе; later-turn approval остаётся host/operator policy.