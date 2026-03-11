const mongoose = require("mongoose");

const riskAnalysisSchema = new mongoose.Schema(
  {
    recordId: { type: String, required: true, unique: true },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    fileName: { type: String, required: true },
    uploadResponse: { type: mongoose.Schema.Types.Mixed, default: null },
    riskResponse: { type: mongoose.Schema.Types.Mixed, default: null },
  },
  { timestamps: true }
);

riskAnalysisSchema.index({ userId: 1, createdAt: -1 });

module.exports = mongoose.model("RiskAnalysis", riskAnalysisSchema);
