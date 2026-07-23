# صندوقچی Security Specification


## Secrets

هیچ:

- API Key
- Token
- Password

نباید داخل Git باشد.


## Authentication

User:

- Telegram Login
- JWT


Admin:

- JWT
- Role Based Access


## Data Safety

- Backup Database
- Audit Actions
- Mask Sensitive Data


## AI Safety

AI نباید:

- وعده سود دهد
- توصیه قطعی مالی بدهد
- خارج از حوزه پاسخ دهد


## Production

نیازمند:

- HTTPS
- Firewall
- Monitoring
- Backup
