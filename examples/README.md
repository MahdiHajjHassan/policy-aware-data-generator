# PolicyForge | Recipient Dataset Examples

> [!CAUTION]
> **Confidential work and public design.** This showcase contains no Thales implementation or data and carries no employer endorsement. The original generator is unavailable; this repository contains its public design and static example files, not a runnable generator. The expanded delivery controls are design recommendations. Country rules and records are fictional, and diagrams explain the design.

Compare these files to see how the same employee schema produces different output shapes for operations, finance, and a partner.

| File | What to inspect |
| --- | --- |
| [Employee schema](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/employee-schema.json) | Field types and categories. |
| [Operations](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/operations.json) | Identity and work fields, without financial fields. |
| [Aster finance](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/finance-aster.json) | Salary, bonus, and currency added to the work fields. |
| [Boreal finance](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/finance-boreal.json) | Financial columns removed by the country rule. |
| [Aster partner](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/partner-aster.json) | Work fields without display names or financial columns. |
| [Expected decisions](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/expected-decisions.json) | Which requests are approved or refused. |
| [Export manifest](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/export-manifest.example.json) | Recipient scope, policy version, and output fields. |

[Project overview](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/README.md) · [Validation scenarios](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/docs/acceptance-scenarios.md)
