// src/core/pgUrl.js
// Encodes the password segment of a PostgreSQL connection URL so that
// special characters (!, @, #, $, spaces, etc.) are safe for the pg driver.
//
// This lets you write the raw password in .env.local without any URL-encoding:
//   DATABASE_URL="postgresql://postgres:Hnodri2529!@localhost:5432/mydb"
//
// How it works:
//   1. Regex captures three groups: everything before the password, the
//      raw password itself (between "user:" and "@host"), and everything after.
//   2. decodeURIComponent handles the case where the password is already
//      partially encoded (idempotent — safe to call twice).
//   3. encodeURIComponent then fully encodes every special character,
//      including ! % @ # $ & + , / : ; = ? and spaces.
//   4. The three groups are reassembled into a valid connection string.

export function buildSafePgUrl(rawUrl) {
  return String(rawUrl).replace(
    /^([\w+\-.]+:\/\/[^:@]*:)([^@]*)(@[\s\S]*)$/,
    (_, scheme, password, rest) =>
      scheme + encodeURIComponent(decodeURIComponent(password)) + rest
  );
}
