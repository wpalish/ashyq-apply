# Очередь ASHYQ

Это исходный backlog. Фактические статусы хранит единственный главный агент в ledger.

| ID | Приоритет | Работа | Зависимости |
|---|---|---|---|
| [T01](tasks/T01.md) | P0 | Reset без выдачи токена клиенту | — |
| [T02](tasks/T02.md) | P1 | Trusted proxy и защита rate limit | T01 |
| [T03](tasks/T03.md) | P1 | Атомарный reset и topology лимитера | T01, T02 |
| [T04](tasks/T04.md) | P1 | Полная, частичная и неизвестная стоимость | — |
| [T05](tasks/T05.md) | P2 | Currency/period-safe scholarship classification | T04 |
| [T06](tasks/T06.md) | P1 | Применимость award по датам и intake | T04, T05 |
| [T07](tasks/T07.md) | P1 | Подтверждённое stacking и совместимость aid | T06 |
| [T08](tasks/T08.md) | P1 | Согласованные buckets и affordability | T07 |
| [T09](tasks/T09.md) | P1 | Draft lifecycle и изоляция кейсов | — |
| [T10](tasks/T10.md) | P1 | Fencing всех writes после lease loss | — |
| [T11](tasks/T11.md) | P1 | Run snapshots и canonical state | T10 |
| [T12](tasks/T12.md) | P1 | Версии checklist и повторная сборка | T11 |
| [T13](tasks/T13.md) | P1 | Правильные TTL и recheck scheduling | T10 |
| [T14](tasks/T14.md) | P2 | Валидный и атомарный rerank contract | T08, T09, T11 |
| [T15](tasks/T15.md) | P2 | Безопасные XLSX/CSV text cells | T04, T05 |
| [T16](tasks/T16.md) | P1 | Browser/HTTP egress и корректные outcomes | — |
| [T17](tasks/T17.md) | P1 | Ограниченный и изолированный PDF parsing | — |
| [T18](tasks/T18.md) | P1 | Измеримый live research на curated scope | T08, T13, T16, T17 |
| [T19](tasks/T19.md) | P2 | Постепенное раскрытие анкеты | T09 |
| [T20](tasks/T20.md) | P2 | Mobile стоимость, период и accessibility | T08, T09 |
| [T21](tasks/T21.md) | P1 | Cross-module regression gates | T03, T08, T12, T13, T14, T15, T16, T17 |
| [T22](tasks/T22.md) | P1 | Стабильный E2E и отдельные artifacts | T19, T20, T21 |
| [T23](tasks/T23.md) | P2 | Правдивые docs и scope release | T18, T22 |
| [T24](tasks/T24.md) | P1 | Runtime, recovery, restore и release verdict | T23 |

На каждую задачу — четыре независимые роли; на критичные — дополнительный Security. Зависимости плюс реальные пересечения файлов определяют параллелизм.
