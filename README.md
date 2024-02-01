# NTUST Bulletin 2

NTUST Bulletin 2 removes the following shites from the NTUST Bulletin and sends
the filtered version to your mailbox:

- Recurring announcements
- Emojis in titles

## Quick start

> **Security Note:** `NTUST Bulletin 2` uses an unencrypted connection to
> communicate with the mail server. Please be aware of potential security risks.

0. Star this repo (thanks 😉)
1. Fork this repo
2. Go to `Settings` > `Code and automation` > `Environments` > `New environment`
   1. Enter `production` for `Name *` and hit `Configure environment`
   2. `Environment secrets` > `Add secret`
      1. Enter `MAIL_USER` for `Name`
      2. Enter `your student id (BXXXXXXXX)` for `Value`
   3. `Environment secrets` > `Add secret`
      1. Enter `MAIL_PASSWORD` for `Name`
      2. Enter `your password mail account` for `Value`
   4. (Optional) `Environment variables` > `Add variable`
      1. Enter `RECIPIENT` for `Name`
      2. Enter `email address(es, seperated by comma)` for `Value`
