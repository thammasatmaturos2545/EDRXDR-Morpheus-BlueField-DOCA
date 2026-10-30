# BERT v4 audit-key provenance — 2026-10-31

Operator-reported config-only checks; no model execution.

## Verified scope

Zenodo record 18861762, scenario 2 archives:
- cron SHA256: b2026121bdb035628b7536a042f01c3e92e36852b65cac9d69fd05c31ba98791
- rootkit SHA256: 1ba8950cdbc7912e0c10094792e3e5affc90f55cf56d2ad4786883c58a190936

Read only videoserver/configs/etc/audit/{audit.rules,rules.d/audit.rules}.
Both scenarios have matching hashes for corresponding config files:
- audit.rules: 3b6c02f729274fcdb6266f2c44b54d6a2b859e8674c3fa8e43ffb577bd4c3e8c
- rules.d/audit.rules: d82256a200c73cab1269d6edf12ff77d536bcff2634997338c72c1addb7123e8

Each file has 212 active lines and 49 lines matching the reviewed audit key.
Within each scenario, active-rule token multisets are identical between files.
Matching lines include watch rules and syscall-filter rules, with condition
fields arch, auid, euid, path and perm. No matching line mentions sshd.

## Interpretation and limits

The reviewed technique-named key exists in archived collection configuration.
Its name alone is not independent event-level attack ground truth.
No explicit sshd text does not exclude a rule matching an sshd operation.
The exact loaded rule and causal match for an observed event remain unverified.
These checks do not prove label leakage, model reliance or its absence.

Do not automatically remove keys, expand token budgets or alter frozen data.
Any sanitization experiment needs a separate frozen development-only protocol.
Family 6 remains protected. No training, GPU, threshold, runtime, offset,
label or dataset changes; no staging or commit performed by this command.

References:
- https://zenodo.org/records/18861762
- https://github.com/linux-audit/audit-userspace/blob/master/docs/auditctl.8
