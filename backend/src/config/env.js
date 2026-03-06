  require("dotenv").config();

module.exports = {
  PORT: process.env.PORT || 5000,
  AI_SERVICE_URL: process.env.AI_SERVICE_URL,
  MAX_FILE_SIZE: Number(process.env.MAX_FILE_SIZE) || 52428800,
  MONGODB_URI: process.env.MONGODB_URI,
  JWT_SECRET: process.env.JWT_SECRET || "fallback-secret",
  ADMIN_SECRET_KEY: process.env.ADMIN_SECRET_KEY,
};