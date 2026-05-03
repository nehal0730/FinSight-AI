const mongoose = require("mongoose");
const { MONGODB_URI } = require("./env");

async function connectDB() {
  try {
    if (!MONGODB_URI) {
      throw new Error("MONGODB_URI is missing in environment variables");
    }
    await mongoose.connect(MONGODB_URI);
    console.log("MongoDB connected");
    return true;
  } catch (err) {
    console.error("MongoDB connection error:", err.message);
    return false;
  }
}

module.exports = connectDB;
