require("dotenv").config(); //load environment variables from .env file

module.exports = {
  PORT: process.env.PORT || 5000,
  AI_SERVICE_URL: process.env.AI_SERVICE_URL,
  MAX_FILE_SIZE: Number(process.env.MAX_FILE_SIZE) || 52428800
};