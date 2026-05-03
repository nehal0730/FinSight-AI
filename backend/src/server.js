const app = require("./app");
const { PORT } = require("./config/env");
const connectDB = require("./config/db");

connectDB().then((dbConnected) => {
  if (!dbConnected) {
    console.warn("[WARN] Starting backend in degraded mode (database unavailable)");
  }
  app.listen(PORT, () => {
    console.log(`Node backend running on port ${PORT}`);
  });
});
