# Reference Design

> [!CAUTION]
> **Independent portfolio demo: no Thales implementation or data.**
> This showcase uses fictional data and generic reference designs to explain engineering ideas from my professional experience. It does not reproduce, document, or disclose Thales's actual systems, architecture, configuration, or critical data. It is not an official Thales project or endorsement.

I documented this public reference design to explain the original project concept. It defines the policy, generation, and delivery contracts without asserting that every reference control existed or was tested in the original tool.

## Input contracts

A source adapter accepts either an API response or a file and produces a canonical dataset contract. The public example uses an employee schema; the design does not depend on that domain.

The contract identifies:

- Dataset name and version.
- Declared fields, data types, and nullability.
- Primary keys and any foreign-key relationships.
- Field classifications.
- Explicit permitted enum values.
- Approved generation constraints.

For an implementation, input handling should bound payload size, validate types, reject malformed contracts, and avoid logging raw payloads. Any access credentials belong in runtime configuration and never in recipient exports.

Source rows can help establish a schema inside an approved source boundary. They are not output fixtures. The synthetic-generation boundary uses approved metadata and configured constraints instead of copying or lightly changing production values.

An undeclared field introduced by a schema change blocks the affected export until its classification and generation rule are reviewed. A field called salary is not classified solely by its name; classification is part of the explicit data contract.

## Policy model

The reference policy has four scopes:

1. Dataset scope defines the field categories available for that dataset.
2. Team scope defines recognized roles, countries, and categories.
3. Role scope further narrows the permitted countries and categories.
4. Country scope further narrows the permitted categories.

For each approved country:

~~~text
permitted categories =
  dataset categories
  intersect team categories
  intersect role categories
  intersect country categories

permitted fields =
  declared fields in permitted categories
  minus explicit denied fields
~~~

The requested countries must be a nonempty subset of both the team's and the role's permitted countries. Unknown scope is a rejection, not an unrestricted default.

An export requesting a mixture of permitted and forbidden countries is rejected as a whole. The caller must submit an explicitly narrower request; the engine does not silently produce a partial export.

After country validation, separate country partitions can have different field lists. Aster finance includes financial fields; Boreal finance omits them. Both remain successful authorized requests under this fictional policy.

A required field that is prohibited by an explicit denial or category restriction makes the export invalid. The generator must not silently retain the field or release a broken dataset.

## Trusted recipient context

A request contains the desired dataset and countries. The subject's authenticated identity, team membership, and role assignments are resolved through trusted authorization context.

A user cannot gain finance permissions by submitting finance_analyst in a payload. The request must match an assigned role. Policy checks are applied to every generation and delivery request, including retries and downloads.

The country attribute used for policy evaluation must also come from the approved dataset contract or trusted metadata. Changing a field in a request must not change a person's authorization.

This design follows the authorization principles of explicit defaults and request-level checks described in the [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

## Synthetic generation boundary

The permitted output field list is compiled before records are generated.

- Structural identifiers are fabricated, unique within the package, and independent of source keys.
- Names and other identity fields use fabricated values from an approved synthetic vocabulary.
- Departments and job families come from approved example enums.
- Financial fields, when permitted, are fabricated from configured ranges and currency markers.
- Date generation observes declared ordering constraints.
- Parent-child records use the same synthetic mapping within one recipient package.
- Separate recipients get independently generated identifiers and records.

The illustration deliberately uses a fictional currency marker and fabricated example names. Amounts are fixed examples, not modelled from a real payroll distribution.

A development seed makes fixture output reproducible for a fixed contract, policy, and generation configuration. It must not include original identifiers, sensitive values, or secrets. Reproducibility does not itself establish anonymity.

## Field omission and country partitions

Restricted columns are absent from a recipient's schema and records. They are not released as hashes, masked strings, or empty values.

When a country rule suppresses financial fields, finance output for that country uses a separate schema. The output manifest records the resulting field list.

The engine must inspect both the declared field list and every output record. A financial property appearing in a record outside the compiled field list rejects the export.

An approved synthetic structural identifier can be available to a partner without exposing identity fields. Its value does not encode a source identifier, a name, or a real employee relationship.

## Relationships and dependencies

For related datasets such as employees and assignments:

- Every generated assignment references an included synthetic employee.
- References are scoped to the same recipient package and country partition.
- An excluded parent cannot remain discoverable through a child record.
- If a required relationship cannot be represented within the permitted scope, the export is rejected or an explicitly documented alternative contract is required.

The employee-only fixtures in this repository do not demonstrate implemented multi-table generation. Relationship handling is part of the expanded reference design.

## Export validation

Before publication, an implementation should verify:

1. Every requested country is recognized and permitted.
2. Each generated country's field list matches the compiled policy.
3. Record properties exactly match the approved schema.
4. Required fields are present and data types are valid.
5. Generated identifiers are unique in their declared scope.
6. Foreign keys resolve inside the exported package.
7. Financial fields are absent for operations and partner outputs.
8. Boreal output has no financial fields for any recipient in this example.
9. Unknown fields and scopes produce explicit rejections.
10. Export manifests and logs contain no source values.

These are acceptance requirements; the public fixtures are static illustrations.

## Failure handling

| Failure | Expected reference behavior |
| --- | --- |
| Invalid API or file contract | Reject the input; record a non-sensitive error code |
| Unknown field classification | Block the affected export pending classification |
| Unknown team, role, dataset, or country | Deny the request |
| Subject is not assigned the requested role | Deny the request |
| Requested country is outside recipient scope | Reject the complete request |
| Policy fails to load or is invalid | Do not generate or release an export |
| Required output field is forbidden | Reject the export |
| Output validation fails | Do not deliver the package |
| Delivery fails | Keep recipient isolation; reauthorize before retry |

No failure should produce a fallback export containing all fields.

## Audit and delivery design

The reference manifest records the policy version, dataset contract version, recipient team and role, countries, output fields, synthetic row counts, and validation status. It does not contain input rows.

Audit events can capture a generated job identifier, an opaque authenticated-subject identifier, the policy version, a decision, and an error code. Logging should avoid names, salaries, source row samples, and source identifiers.

The distribution boundary requires authenticated delivery, recipient checks, isolated export storage, appropriate retention, and authorization on download. Removing fields does not replace those controls. These operational mechanisms are outside this documentation-only repository.

## Domain extension

A non-HR dataset follows the same policy model with its own explicit classifications. For example, a product dataset might distinguish structural identifiers, product descriptions, stock information, and cost fields.

The architecture permits that extension, but this repository only supplies an employee-domain fixture set. It does not claim that additional domain adapters are implemented.

## Evidence boundary

The repository establishes a documented approach, a consistent policy example, and fabricated output illustrations. It does not establish throughput, deployment status, legal certification, or correctness of an unpublished original implementation.
