const express = require("express");
const cors = require("cors"); // browser cannot make requests to a different ports of frotend, backend, etc unless CORS is enabled
const cookieParser = require("cookie-parser");

const uploadRoutes = require("./routes/upload");
const healthRoutes = require("./routes/health");
const authRoutes = require("./routes/auth");
const queryRoutes = require("./routes/query");
const errorHandler = require("./middleware/error");
const requestLogger = require("./middleware/request");

const app = express();

app.use(cors({ origin: "http://localhost:5173", credentials: false }));
app.use(express.json());
app.use(cookieParser());
app.use(requestLogger);

app.use("/auth", authRoutes);
app.use("/upload", uploadRoutes);
app.use("/query", queryRoutes);
app.use("/health", healthRoutes);

app.use(errorHandler);

module.exports = app;