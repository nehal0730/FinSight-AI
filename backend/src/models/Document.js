const mongoose = require("mongoose");

const documentSchema = new mongoose.Schema(
  {
    fileName: { type: String, required: true },
    documentId: { type: String, required: true, unique: true }, // ID from AI service
    userId: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
    filePath: { type: String, default: null }, // Path to stored PDF on disk
    fileSize: { type: Number, default: null }, // File size in bytes
    uploaded_at: { type: Date, default: Date.now },
  },
  { timestamps: true }
);

module.exports = mongoose.model("Document", documentSchema);
