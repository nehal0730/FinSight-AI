const app = require("./app");
const { PORT } = require("./config/env");
const connectDB = require("./config/db");
const { initGridFS } = require("./utils/mongoStorage");

connectDB().then((dbConnected) => {
  if (!dbConnected) {
    console.warn("[WARN] Starting backend in degraded mode (database unavailable)");
  } else {
    // Initialize GridFS for PDF storage
    initGridFS();
  }
  app.listen(PORT, () => {
    console.log(`Node backend running on port ${PORT}`);
  });
});
