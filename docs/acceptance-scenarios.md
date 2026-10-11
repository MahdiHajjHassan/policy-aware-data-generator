# PolicyForge | Validation Scenarios

> [!CAUTION]
> **Confidential work and public design.** This showcase contains no Thales implementation or data and carries no employer endorsement. The original generator is unavailable; this repository contains its public design and static example files, not a runnable generator. The expanded delivery controls are design recommendations. Country rules and records are fictional, and diagrams explain the design.

The policy matrix defines permitted datasets, refused requests, and the cases that block export. The country and recipient examples use the rules in [policies.example.json](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/policies.example.json).

## Expected decisions

| Scenario | Expected result |
| --- | --- |
| Operations analyst requests Aster and Boreal | Permit; omit financial fields in both country scopes |
| Finance analyst requests Aster | Permit; include fabricated financial values |
| Finance analyst requests Boreal | Permit; omit financial fields because the country restriction narrows the role |
| Partner developer requests Aster | Permit; include structural and work fields only |
| Partner developer requests Boreal | Reject the entire request because the country is outside recipient scope |
| Partner developer requests Aster and Boreal | Reject the entire request; no silent partial delivery |
| Unknown recipient team | Reject |
| Role does not belong to the resolved team | Reject |
| Role is valid but is not assigned to the authenticated subject | Reject |
| Unknown country or dataset | Reject |
| Empty requested-country list | Reject |
| A new field has no classification | Block export pending explicit classification |
| A requested field is explicitly denied | Omit if optional; reject if the output contract requires it |
| Policy is missing, stale under the deployment's rules, or invalid | Do not release the export |
| An output record contains an extra financial property | Reject before delivery |
| A parent-child export has an unresolved reference | Reject before delivery |
| A generated identifier duplicates another identifier in its declared scope | Reject |
| Country-specific outputs have different allowed schemas | Create separate country partitions with explicit field lists |
| Delivery is retried after permissions change | Reauthorize; reject if the recipient is no longer permitted |

## Compare the dataset files

- [Operations](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/operations.json): structural, identity, and work fields.
- [Aster finance](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/finance-aster.json): the same categories plus salary, bonus, and currency.
- [Boreal finance](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/finance-boreal.json): financial fields omitted by the country rule.
- [Aster partner](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/partner-aster.json): structural and work fields; no display name or financial columns.
- [Expected decisions](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/examples/expected-decisions.json): approvals and refusals.

## What validation covers

Policy decisions, unknown scopes, untrusted role claims, schema changes, restricted-field omission, country partitions, relationship integrity, duplicate identifiers, and permission changes before retries or downloads.

[Project overview](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/README.md) · [Export design](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/docs/reference-design.md)
