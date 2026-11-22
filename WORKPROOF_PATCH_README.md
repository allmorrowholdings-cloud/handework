# WorkProof patch

Copy these paths over the matching handEwork project root, then run the backend migration:

```bash
cd backend
flask --app handework db upgrade
```

No sample workers or invented WorkProof records are included. Outside-work submissions begin as `pending` and affect a public score only after an admin independently marks the evidence `verified`.
