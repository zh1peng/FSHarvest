# Security policy

## Reporting

Please report suspected vulnerabilities privately to the project maintainers before public disclosure. Include the affected version, a minimal reproduction, and the potential impact. Do not include patient data, subject reconstructions, credentials, or licensed FreeSurfer files.

## Scope

FSHarvest treats input FreeSurfer subject directories as read-only unless `--export-to-freesurfer` is explicitly supplied. Output directories and atlas bundles should be writable only by trusted users. FSHarvest does not support multiple independent processes writing to the same output directory at the same time.

