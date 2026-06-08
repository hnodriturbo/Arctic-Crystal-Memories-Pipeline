// prisma/seed.js
// Creates the initial admin user in the database.
// Run from web/ folder: node prisma/seed.js

require("dotenv").config({ path: require("path").resolve(__dirname, "../.env.local") });

const { PrismaClient } = require("@prisma/client");
const { PrismaPg } = require("@prisma/adapter-pg");
const bcrypt = require("bcryptjs");

const adapter = new PrismaPg({ connectionString: String(process.env.DATABASE_URL || "") });
const prisma = new PrismaClient({ adapter });

async function main() {
  const username = "hnodri";
  const email = "hreidar1987@gmail.com";
  const password = "Hnodri2529!";
  const role = "admin";

  const existing = await prisma.user.findUnique({ where: { username } });
  if (existing) {
    console.log(`User '${username}' already exists. Skipping.`);
    return;
  }

  const hashed = await bcrypt.hash(password, 12);
  const user = await prisma.user.create({
    data: { username, email, password: hashed, role },
  });

  console.log(`Admin user created: ${user.username} (${user.email})`);
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
