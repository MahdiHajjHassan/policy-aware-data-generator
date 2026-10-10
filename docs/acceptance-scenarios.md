# Acceptance Scenarios

These scenarios describe reference expectations. They are not runtime test results.

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

## Reading the fixtures

The JSON files contain fabricated example records written for this public case study. They illustrate output shape, not execution of a generator.

- Operations has structural, identity, and work fields.
- Aster finance additionally has annual_salary, annual_bonus, and currency.
- Boreal finance has the same categories as operations because financial fields are restricted there.
- Aster partner has structural and work fields, with display_name absent.
- Expected decisions show both approvals and denials.

## Verification required for a future implementation

An executable reconstruction should test the policy matrix, schema changes, untrusted recipient context, invalid inputs, field omission, country restrictions, record relationships, output validation failures, retries, and delivery isolation.

Do not mark those implementation checks as passed merely because the static example files are consistent.
