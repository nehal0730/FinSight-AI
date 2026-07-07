const express = require("express");
const axios = require("axios");
const auth = require("../middleware/auth");
const logger = require("../config/logger");
const { AI_SERVICE_URL } = require("../config/env");
const Document = require("../models/Document");
const RiskAnalysis = require("../models/RiskAnalysis");

const router = express.Router();

function normalizeErrorMessage(errorValue, fallback) {
  if (typeof errorValue === 'string') return errorValue;
  if (errorValue && typeof errorValue === 'object') {
    return errorValue.message || errorValue.detail || JSON.stringify(errorValue);
  }
  return fallback;
}

/**
 * Query indexed documents using RAG
 * POST /query
 * Body: { query: string, document_id: string, top_k?: number }
 */
router.post("/", auth, async (req, res, next) => {
  try {
    const { query, document_id, top_k } = req.body;

    if (!query || !query.trim()) {
      return res.status(400).json({ 
        success: false,
        error: "Query is required" 
      });
    }

    if (!document_id) {
      return res.status(400).json({ 
        success: false,
        error: "document_id is required" 
      });
    }

    // Validate user access to document
    const doc = await Document.findOne({ documentId: document_id });
    if (doc && req.user.role !== 'admin' && doc.userId.toString() !== req.user.id) {
      return res.status(403).json({
        success: false,
        error: "You don't have access to this document"
      });
    }

    logger.info(`Query request: "${query}" for document: ${document_id}`);

    try {
      // Forward query to AI service
      const aiResponse = await axios.post(
        `${AI_SERVICE_URL}/query/query`,
        {
          query,
          document_id,
          top_k: top_k || 5,
        },
        { timeout: 30000 }
      );

      logger.info(`Query completed for: ${document_id}`);

      return res.status(200).json({
        success: true,
        data: aiResponse.data,
        error: null,
      });
    } catch (aiErr) {
      const detail = normalizeErrorMessage(
        aiErr?.response?.data?.detail || aiErr?.response?.data?.error || aiErr?.message,
        "AI service unavailable"
      );
      logger.error(`AI query unavailable for ${document_id}. Detail: ${detail}`);

      return res.status(aiErr?.response?.status || 502).json({
        success: false,
        error: detail,
      });
    }

  } catch (err) {
    if (err.response) {
      // AI service returned an error
      logger.error(`AI service error: ${err.response.status} - ${JSON.stringify(err.response.data)}`);
      return res.status(err.response.status).json({
        success: false,
        error: normalizeErrorMessage(
          err.response.data?.detail || err.response.data?.error,
          "Query failed"
        )
      });
    }
    
    logger.error(`Query error: ${err.message}`);
    console.error("Full error:", err);
    next(err);
  }
});

/**
 * List indexed documents
 * GET /query/documents
 */
router.get("/documents", auth, async (req, res, next) => {
  try {
    logger.info(`📋 /documents endpoint - User: ${req.user.id}, Role: "${req.user.role}"`);
    
    let userDocuments = [];
    
    if (req.user.role === 'admin') {
      // Admin: Fetch all documents from MongoDB
      logger.info(`👑 ADMIN DETECTED - Fetching ALL documents from MongoDB`);
      userDocuments = await Document.find({}, 'documentId fileName uploaded_at filePath fileSize');
      logger.info(`✓ Found ${userDocuments.length} TOTAL documents in MongoDB`);
    } else {
      // Regular user: Fetch only their own documents from MongoDB
      logger.info(`👤 Regular user - Fetching only own documents`);
      userDocuments = await Document.find(
        { userId: req.user.id }, 
        'documentId fileName uploaded_at filePath fileSize'
      );
      logger.info(`✓ Found ${userDocuments.length} documents for this user`);
    }

    // Fallback: if no Document records exist, derive document IDs from saved risk analysis history.
    if (userDocuments.length === 0) {
      const historyFilter = req.user.role === "admin" ? {} : { userId: req.user.id };
      const history = await RiskAnalysis.find(historyFilter)
        .sort({ updatedAt: -1 })
        .lean();

      const fallbackDocs = [];
      for (const item of history) {
        const fromUpload = item?.uploadResponse?.data?.aiResponse?.storage_ref?.id;
        const fallbackId = fromUpload || item?.recordId;
        if (!fallbackId) continue;
        fallbackDocs.push({
          documentId: fallbackId,
          fileName: item?.fileName || "Demo document",
          uploaded_at: item?.updatedAt || item?.createdAt,
          fileSize: 0,
          filePath: null,
        });
      }

      // De-duplicate document IDs while preserving order.
      const seen = new Set();
      userDocuments = fallbackDocs.filter((doc) => {
        if (seen.has(doc.documentId)) return false;
        seen.add(doc.documentId);
        return true;
      });

      logger.info(`✓ Using ${userDocuments.length} fallback documents from risk history`);
    }

    // Return just the document IDs for the Chat page (backward compatibility)
    const documentIds = userDocuments.map((doc) => doc.documentId);

    // Also return full document data for dashboard usage
    const documentsWithMetadata = userDocuments.map((doc) => ({
      documentId: doc.documentId,
      fileName: doc.fileName,
      uploadedAt: doc.uploaded_at,
      fileSize: doc.fileSize,
      hasPdf: !!doc.filePath,
    }));
    
    logger.info(`✓ Returning ${documentIds.length} document IDs`);

    res.status(200).json({
      success: true,
      data: {
        documents: documentIds,
        documentsWithMetadata: documentsWithMetadata
      },
      error: null
    });

  } catch (err) {
    logger.error(`List documents error: ${err.message}`);
    next(err);
  }
});

module.exports = router;
