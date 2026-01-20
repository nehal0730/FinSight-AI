const express = require("express");
const cors = require("cors"); //Browsers block requests between different ports by default, CORS allows frontend (5173) to talk to backend (5000)

const uploadRoutes = require("./routes/upload");
const healthRoutes = require("./routes/health");
const errorHandler = require("./middleware/error");

const app = express();

app.use(cors({ origin: "http://localhost:5173" }));

app.use("/upload", uploadRoutes);
app.use("/health", healthRoutes);

app.use(errorHandler);

module.exports = app;