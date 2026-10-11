# PolicyForge | Schemas, Permissions, and Export Design

> [!CAUTION]
> **Confidential work and public design.** This showcase contains no Thales implementation or data and carries no employer endorsement. The original generator is unavailable; this repository contains its public design and static example files, not a runnable generator. The expanded delivery controls are design recommendations. Country rules and records are fictional, and diagrams explain the design.

PolicyForge's design connects a declared schema, the recipient's permissions, synthetic value generation, and export validation. The central rule is to decide the allowed data shape before creating the values.

## Dataset contract

An API or file adapter supplies a common dataset description:

- Name and version.
- Fields, types, and required values.
- Primary keys and relationships.
- Field categories and permitted enumerated values.
- Generation constraints.

Input handling bounds payload size, validates types, and rejects malformed contracts. A new unclassified field blocks the affected export until its category and generation rule are reviewed. Field names alone do not establish their classification.

## Permission rules

The policy combines four scopes: dataset, team, role, and country.

```text
allowed categories = dataset ∩ team ∩ role ∩ country
allowed fields = declared fields in allowed categories minus explicit denials
```

Requested countries must be allowed by both the team and role. An unknown scope is rejected. A request containing permitted and forbidden countries is rejected as a whole; the caller must request a narrower scope explicitly.

After country checks, field selection can produce different country schemas. Aster finance includes financial fields; Boreal finance omits them. A required field that is forbidden makes the export invalid.

## Trusted recipient identity

The authenticated identity, team membership, and roles come from trusted access-control records. A request supplies the desired dataset and countries; typing `finance_analyst` into a payload does not grant that role.

Generation, retries, and downloads check the recipient's current permissions. Country attributes used in policy decisions come from approved dataset metadata.

## Generate within the selected schema

- Generate package-specific identifiers independently of source keys.
- Use a synthetic vocabulary for names and identity fields.
- Use approved values for departments and job families.
- Generate financial values only when permitted, within configured ranges.
- Preserve declared date ordering and parent-child relationships.
- Keep separate recipients' identifiers and records independent.

A fixed development seed makes outputs reproducible for the same schema, policy, and generation configuration.

## Omit restricted columns

Forbidden fields are absent from both the declared schema and every record. They are not represented by a masked string or an empty value. Country partitions carry their own permitted field lists.

Related records stay within the same recipient package and country. A child record cannot reveal an excluded parent through its identifier. An unresolved required relationship rejects the export.

## Validate before delivery

| Check | Requirement |
| --- | --- |
| Countries | Every requested country is recognized and permitted. |
| Columns | Schema and record properties match the selected field list exactly. |
| Values | Required fields, types, and configured constraints are valid. |
| Identifiers | Unique in the declared package scope. |
| Relationships | References resolve within the same package and partition. |
| Recipient fields | Financial and identity fields follow the recipient and country rules. |
| New fields | Classification is reviewed before export. |

## Failure handling

| Failure | Design response |
| --- | --- |
| Invalid input or unknown classification | Reject or block the affected export. |
| Unknown recipient, country, dataset, or unassigned role | Deny the request. |
| Missing or invalid policy | Do not generate or release an export. |
| Required field is forbidden | Reject the export. |
| Record or relationship validation fails | Do not deliver the package. |
| Delivery retry | Check permissions again and retain recipient isolation. |

## Export records and delivery

The manifest records dataset and policy versions, recipient team and role, countries, field lists, row counts, and validation status. Delivery uses authenticated recipient checks, isolated storage, retention rules, and authorization on download.

Operational logs record job identifiers, decisions, and error codes. They exclude source row samples and sensitive values.

## Other dataset domains

A product dataset can use the same rules with categories such as descriptions, stock information, and cost. Each domain supplies its own schema and classifications.

[Project overview](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/README.md) · [Validation scenarios](https://github.com/MahdiHajjHassan/policy-aware-data-generator/blob/main/docs/acceptance-scenarios.md)
