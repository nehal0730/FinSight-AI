const express = require("express");
const axios = require("axios");
const auth = require("../middleware/auth");
const logger = require("../config/logger");
const { AI_SERVICE_URL } = require("../config/env");
const RiskAnalysis = require("../models/RiskAnalysis");

const router = express.Router();

/**
 * Get risk analysis history for the current user (admins get all)
 * GET /risk-analysis/history
 */
router.get("/history", auth, async (req, res, next) => {
  try {
    const filter = req.user.role === "admin" ? {} : { userId: req.user.id };
    const records = await RiskAnalysis.find(filter)
      .sort({ createdAt: -1 })
      .lean();

    const data = records.map((r) => ({
      id: r.recordId,
      userId: r.userId,
      createdAt: r.createdAt,
      fileName: r.fileName,
      uploadResponse: r.uploadResponse,
      riskResponse: r.riskResponse,
    }));

    res.json({ success: true, data, error: null });
  } catch (err) {
    logger.error(`Failed to fetch risk history: ${err.message}`);
    next(err);
  }
});

/**
 * Save a risk analysis record
 * POST /risk-analysis
 */
router.post("/", auth, async (req, res, next) => {
  try {
    const { id, fileName, uploadResponse, riskResponse } = req.body;

    if (!id || !fileName) {
      return res.status(400).json({
        success: false,
        error: "id and fileName are required",
      });
    }

    const record = await RiskAnalysis.findOneAndUpdate(
      { recordId: id },
      {
        recordId: id,
        userId: req.user.id,
        fileName,
        uploadResponse: uploadResponse || null,
        riskResponse: riskResponse || null,
      },
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    logger.info(`Risk analysis saved: ${id} by user ${req.user.id}`);

    res.json({
      success: true,
      data: {
        id: record.recordId,
        userId: record.userId,
        createdAt: record.createdAt,
        fileName: record.fileName,
      },
      error: null,
    });
  } catch (err) {
    logger.error(`Failed to save risk analysis: ${err.message}`);
    next(err);
  }
});

/**
 * Delete risk history for the current user (admins clear all)
 * DELETE /risk-analysis/history
 */
router.delete("/history", auth, async (req, res, next) => {
  try {
    const filter = req.user.role === "admin" ? {} : { userId: req.user.id };
    const result = await RiskAnalysis.deleteMany(filter);
    logger.info(
      `Risk history cleared: ${result.deletedCount} records by user ${req.user.id}`
    );
    res.json({ success: true, data: { deleted: result.deletedCount }, error: null });
  } catch (err) {
    logger.error(`Failed to clear risk history: ${err.message}`);
    next(err);
  }
});

/**
 * Regenerate risk analysis with LLM enabled
 * POST /risk-analysis/regenerate
 * Body: { documentId: string, analysisId: string }
 */
router.post("/regenerate", auth, async (req, res, next) => {
  try {
    const { documentId, analysisId } = req.body;

    if (!documentId) {
      return res.status(400).json({
        success: false,
        error: "documentId is required"
      });
    }

    if (!analysisId) {
      return res.status(400).json({
        success: false,
        error: "analysisId is required"
      });
    }

    logger.info(`Regenerating analysis with LLM - documentId: ${documentId}, analysisId: ${analysisId}`);

    // Call AI service to regenerate with LLM enabled
    // The AI service should support re-analyzing an already uploaded document
    const aiResponse = await axios.post(
      `${AI_SERVICE_URL}/risk-analysis/regenerate`,
      {
        document_id: documentId,
        use_llm: true
      },
      {
        timeout: 300000 // 5 minute timeout for LLM processing
      }
    );

    logger.info(`Risk analysis regenerated successfully for: ${documentId}`);

    res.status(200).json({
      success: true,
      data: {
        riskResponse: aiResponse.data
      },
      error: null
    });

  } catch (err) {
    if (err.response) {
      // AI service returned an error
      logger.error(`AI service error: ${err.response.status} - ${JSON.stringify(err.response.data)}`);
      const errorMsg = err.response.data?.detail || err.response.data?.error || "Regeneration failed";
      
      // Check if it's a 404 (endpoint not found) and provide helpful message
      if (err.response.status === 404) {
        return res.status(400).json({
          success: false,
          error: "The AI service doesn't support regenerating existing analyses. Please re-upload the document with the 'AI Summary' option enabled on the Upload page."
        });
      }

      return res.status(err.response.status).json({
        success: false,
        error: errorMsg
      });
    }

    if (err.code === 'ECONNABORTED') {
      logger.error(`Regeneration timeout: ${err.message}`);
      return res.status(504).json({
        success: false,
        error: "Analysis generation timed out. This can happen with large documents. Please try again."
      });
    }

    if (err.code === 'ECONNREFUSED') {
      logger.error(`AI service connection refused: ${err.message}`);
      return res.status(503).json({
        success: false,
        error: "The AI service is currently unavailable. Please try again later."
      });
    }

    logger.error(`Regeneration error: ${err.message}`);
    next(err);
  }
});

module.exports = router;

