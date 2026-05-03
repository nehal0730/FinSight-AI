const express = require("express");
const cors = require("cors"); // browser cannot make requests to a different ports of frotend, backend, etc unless CORS is enabled
const cookieParser = require("cookie-parser");

const uploadRoutes = require("./routes/upload");
const healthRoutes = require("./routes/health");
const authRoutes = require("./routes/auth");
const queryRoutes = require("./routes/query");
const riskAnalysisRoutes = require("./routes/risk-analysis");
const errorHandler = require("./middleware/error");
const requestLogger = require("./middleware/request");

const app = express();

// Determine allowed origins based on environment
const allowedOrigins = [
  "http://localhost:5173",  // Local dev
  "http://localhost:3000",  // Local dev alternative
  process.env.FRONTEND_URL || "http://localhost:5173" // Production frontend
];

app.use(cors({ origin: allowedOrigins, credentials: false }));
app.use(express.json());
app.use(cookieParser());
app.use(requestLogger);

app.use("/auth", authRoutes);
app.use("/upload", uploadRoutes);
app.use("/query", queryRoutes);
app.use("/risk-analysis", riskAnalysisRoutes);
app.use("/health", healthRoutes);

app.use(errorHandler);

module.exports = app;