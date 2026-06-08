# Prisma Setup Guide — K9 Crystal Pipeline

## 1. Create the database

Open PowerShell (Admin) and run:

```powershell
psql -U postgres -c "CREATE DATABASE \"k9-crystal-pipeline\";"
```

## 2. Set up your .env.local

Copy `.env.example` to `.env.local` and fill in your PostgreSQL password:

```
DATABASE_URL="postgresql://postgres:Hnodri2529%21@localhost:5432/k9-crystal-pipeline"
```

> Note: Special characters in the password must be URL-encoded.
> `!` → `%21`  `@` → `%40`  `#` → `%23`  `$` → `%24`

## 3. Push the schema to the database

```powershell
cd web
npx prisma db push
```

## 4. Create the admin user

```powershell
node prisma/seed.js
```

## 5. (Optional) Open Prisma Studio to inspect data

```powershell
npx prisma studio
```

This opens a browser UI at http://localhost:5555 where you can view and edit all tables.

## 6. After schema changes

If you modify `prisma/schema.prisma`, run again:

```powershell
npx prisma db push
npx prisma generate
```

## Tables

| Table        | Purpose                                     |
|--------------|---------------------------------------------|
| User         | Login accounts (username + hashed password) |
| Session      | NextAuth v5 sessions                        |
| ProcessRun   | History of pipeline runs per image          |
