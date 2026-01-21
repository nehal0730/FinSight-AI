const app = require("./app");
const { PORT } = require("./config/env");
const connectDB = require("./config/db");

connectDB().then(() => {
  app.listen(PORT, () => {
    console.log(`Node backend running on port ${PORT}`);
  });
});
