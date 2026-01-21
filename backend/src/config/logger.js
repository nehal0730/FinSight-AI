const fs = require("fs");
const path = require("path");

// Ensure logs directory exists
const logDir = path.join(__dirname, "../../logs");
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir);
}

const logFile = path.join(logDir, "app.log");

const log = (level, message) => {
  const entry = `[${new Date().toISOString()}] [${level}] ${message}\n`;
  fs.appendFileSync(logFile, entry);
};

module.exports = {
  info: (msg) => log("INFO", msg),
  error: (msg) => log("ERROR", msg)
};
