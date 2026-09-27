-- Owner decision 27-09-2026: Workshop uses a single ADMIN role; the former OWNER account becomes ADMIN.
ALTER TABLE "users" ALTER COLUMN "role" DROP DEFAULT;
ALTER TYPE "UserRole" RENAME TO "UserRole_old";
CREATE TYPE "UserRole" AS ENUM ('ADMIN');
ALTER TABLE "users" ALTER COLUMN "role" TYPE "UserRole" USING ('ADMIN'::"UserRole");
ALTER TABLE "users" ALTER COLUMN "role" SET DEFAULT 'ADMIN';
DROP TYPE "UserRole_old";
