Work In Progress....

PyVault
---
## AWS configuration
```
[default]
region = eu-west-1
output = yaml

[profile mfa-login]
mfa_serial = arn:aws:iam::XXXXXXXXXXXX:mfa/dgorohov

[profile test-ro]
source_profile  = mfa-login
include_profile = mfa-login
role_arn = arn:aws:iam::XXXXXXXXXXXX:role/RO

[profile test-ro-vault]
credential_process = pyvault exec --profile=test-ro --ui

#
# SSO account's profiles
#

[profile sso-power-user]
sso_start_url = https://yourname.awsapps.com/start
sso_region = eu-west-1
sso_role_name = PowerUser

[profile sso-stage-power-user]
sso_account_id = XXXXXXXXXXXX
include_profile = sso-power-user
source_profile = sso-power-user
```

## Usage

```
# pyvault exec --profile=test-ro -- aws s3 ls
```
