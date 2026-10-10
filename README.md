# Policy-Aware Synthetic Data Generator

**Recipient-specific development datasets shaped by team, role, and country rules.**

A data platform can serve many teams without giving every team the same view of the information. Operations may need employee assignments while finance needs compensation fields. A partner development team may need a much smaller subset. Country rules can further narrow each recipient's scope.

I developed a configurable synthetic data generator to support this kind of development-data distribution. This repository presents a public case study and an expanded reference design using entirely fictional examples.

> **Repository status:** Documentation-only case study. The original source implementation is not included. Configurations and output fixtures are illustrative reference examples; they are not execution results or proof of production controls.

## The business problem

Teams need realistic development data to build integrations, dashboards, and workflows. Sharing one unrestricted dataset makes it easy to expose fields that a recipient has no reason to receive. Removing all structure, on the other hand, makes the data less useful for development.

The goal is to give each team useful synthetic datasets that reflect its permitted view: appropriate fields, country scope, data types, and relationships.

This applies beyond HR. The same pattern can support operational, customer, inventory, or other datasets once their fields and access rules have been explicitly classified.

## My contribution

The original work focused on configuration-driven generation of dummy data for recipients with different access requirements. Inputs could arrive through APIs or files, and the recipient configuration determined the scope of the development dataset.

The public reference below explains that approach through a concrete example. Its additional validation, audit, and failure-handling controls are documented design recommendations rather than claims about features verified in the original implementation.

## A concrete example

An employee dataset has structural identifiers, identity fields, work information, and financial fields. Two fictional countries, Aster and Boreal, apply different sharing rules.

| Recipient | Permitted countries | Identity fields | Work fields | Financial fields |
| --- | --- | --- | --- | --- |
| Operations analyst | Aster, Boreal | Synthetic values | Synthetic values | Omitted |
| Finance analyst | Aster | Synthetic values | Synthetic values | Synthetic values |
| Finance analyst | Boreal | Synthetic values | Synthetic values | Omitted by country rule |
| Partner developer | Aster only | Omitted | Synthetic values | Omitted |

The country rule narrows the finance team's permissions in Boreal. A team-level permission does not override that restriction.

For example, an Aster finance fixture includes annual salary and bonus:

~~~json
{
  "employee_id": "fin-as-0001",
  "country": "Aster",
  "display_name": "Morgan Example",
  "department": "Operations",
  "job_family": "Analyst",
  "annual_salary": 54000,
  "annual_bonus": 4000,
  "currency": "DEM"
}
~~~

The operations fixture contains different synthetic records and omits financial columns:

~~~json
{
  "employee_id": "ops-0001",
  "country": "Aster",
  "display_name": "Alex Example",
  "department": "Operations",
  "job_family": "Analyst"
}
~~~

DEM is a fictional currency marker. Neither example describes a real employee.

## Reference workflow

1. **Receive an API payload or file.** Validate the input contract and identify the dataset schema. Public fixtures use fabricated metadata only.
2. **Classify fields.** Associate each declared field with a category such as structural, identity, work, or financial. Unknown fields stop the export until classified.
3. **Resolve recipient scope.** Use trusted team membership, role, and requested country scope to select the applicable policy.
4. **Combine restrictions.** Intersect team, role, country, and dataset permissions. Apply explicit denials after that intersection.
5. **Generate permitted synthetic fields.** Use fabricated values and new identifiers; do not carry original names, salaries, keys, or rows into the output.
6. **Validate the result.** Check the exact output field list, allowed countries, types, and relationships before release.
7. **Package for the recipient.** Include a policy version and structural manifest. Output delivery itself still requires authenticated, authorized access.

Where country rules produce different schemas, the reference design creates separate country packages. This makes the omission of financial columns explicit rather than hiding restricted values behind nulls.

~~~mermaid
flowchart TD
  API["API input"] --> CONTRACT["Contract and classification"]
  FILE["File input"] --> CONTRACT
  CONTRACT --> POLICY["Recipient and country policy"]
  POLICY --> DECISION{"Scope valid?"}
  DECISION -->|No| STOP["Reject export"]
  DECISION -->|Yes| GENERATE["Generate permitted synthetic fields"]
  GENERATE --> VALIDATE["Validate output"]
  VALIDATE --> CHECK{"Checks pass?"}
  CHECK -->|No| STOP
  CHECK -->|Yes| PACKAGE["Recipient package"]
~~~

## Example configuration

The configuration describes allowed roles and field categories for each team. Country policies provide an additional boundary.

~~~json
{
  "team": "operations",
  "allowed_roles": ["operations_analyst"],
  "allowed_countries": ["Aster", "Boreal"],
  "allowed_categories": ["structural", "identity", "work"],
  "deny_fields": ["annual_salary", "annual_bonus", "currency"]
}
~~~

The complete example is in [policies.example.json](policies.example.json). It includes finance and partner policies, a country restriction, and defaults for unrecognized scope.

## Design controls

The reference design specifies:

- Denial when a team, role, country, dataset, or field classification is unknown.
- Authorization based on trusted identity context, rather than a caller choosing a more privileged role.
- Explicit financial-field omission for restricted recipients.
- Country restrictions that cannot be widened by a team permission.
- Synthetic identifiers scoped to each recipient package.
- Consistent parent-child identifiers within an exported package.
- Validation before an output can leave the generation boundary.
- Metadata-only audit events that avoid storing source rows or sensitive values.
- Reproducible fixture seeds for development, with no original identifiers used as seeds.

## What to inspect

| File | Purpose |
| --- | --- |
| [docs/reference-design.md](docs/reference-design.md) | Policy precedence, generation boundaries, failure behavior, and operational recommendations |
| [docs/acceptance-scenarios.md](docs/acceptance-scenarios.md) | Expected outcomes for allowed and denied scenarios |
| [policies.example.json](policies.example.json) | Illustrative team, role, country, and dataset policies |
| [examples/employee-schema.json](examples/employee-schema.json) | Fictional field classifications and data types |
| [examples/operations.json](examples/operations.json) | Operations output with financial columns absent |
| [examples/finance-aster.json](examples/finance-aster.json) | Finance output with fabricated financial fields |
| [examples/finance-boreal.json](examples/finance-boreal.json) | Finance output narrowed by the Boreal country policy |
| [examples/partner-aster.json](examples/partner-aster.json) | Partner output without identity or financial fields |
| [examples/expected-decisions.json](examples/expected-decisions.json) | Illustrative denial and field-selection decisions |
| [examples/export-manifest.example.json](examples/export-manifest.example.json) | A proposed export manifest without source rows |

## Scope and interpretation

All people, team labels, countries, field examples, amounts, and configurations in this repository are fictional. The material does not reproduce an employer's code, schema, access configuration, endpoints, or internal project names.

Country rules are fictional configuration examples. An implementation must also prevent copied source values, source-derived identifiers, and unintended disclosure through logs or data profiling.

**Author:** [Mahdi Hajj Hassan](https://github.com/MahdiHajjHassan)
