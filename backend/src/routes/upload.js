const express = require("express");
const axios = require("axios"); //for making HTTP requests
const FormData = require("form-data"); //to create form data for file upload
const { Readable } = require("stream");
const path = require("path");
const fs = require("fs");
const upload = require("../middleware/upload.js");
const auth = require("../middleware/auth");
const logger = require("../config/logger");
const { AI_SERVICE_URL } = require("../config/env");
const Document = require("../models/Document");

const PDF_STORAGE_DIR = path.join(__dirname, "..", "..", "uploads", "pdfs");

// Ensure upload directory exists
if (!fs.existsSync(PDF_STORAGE_DIR)) {
  fs.mkdirSync(PDF_STORAGE_DIR, { recursive: true });
}

const router = express.Router();

router.post("/", auth, upload.single("file"), async (req, res, next) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }

    // Stream file directly from memory buffer (no disk write)
    const formData = new FormData();
    const bufferStream = Readable.from(req.file.buffer);
    formData.append("file", bufferStream, req.file.originalname);

    // Node sends file stream to FastAPI, FastAPI analyzes file, Returns result
    const aiResponse = await axios.post(
      `${AI_SERVICE_URL}/analyze`,
      formData,
      { headers: formData.getHeaders() }
    );

    logger.info(`File processed: ${req.file.originalname}`);

    // Store document metadata in MongoDB with user ID
    // Extract unique document ID from storage_ref (has timestamp + random hash)
    const documentId = aiResponse.data?.storage_ref?.id || req.file.originalname;
    logger.info(`Saving to MongoDB - fileName: ${req.file.originalname}, documentId: ${documentId}, userId: ${req.user.id}`);
    
    // Save PDF to disk
    const safeFileName = `${documentId}.pdf`;
    const filePath = path.join(PDF_STORAGE_DIR, safeFileName);
    fs.writeFileSync(filePath, req.file.buffer);
    logger.info(`PDF saved to disk: ${filePath}`);

    await Document.create({
      fileName: req.file.originalname,
      documentId: documentId,
      userId: req.user.id,
      filePath: safeFileName,
      fileSize: req.file.size,
    });

    logger.info(`Document saved successfully to MongoDB`);

    res.status(200).json({
      success: true,
      data: {
        originalFilename: req.file.originalname,
        aiResponse: aiResponse.data
      },
      error: null
    });

  } catch (err) {
    // Handle MongoDB duplicate key error specifically
    if (err.code === 11000) {
      logger.error(`Duplicate document ID: ${err.message}`);
      return res.status(409).json({ 
        success: false,
        error: "This document has already been uploaded. Please wait a moment and try again." 
      });
    }
    logger.error(err.message);
    next(err);
  }
});

/**
 * Download/view an uploaded PDF
 * GET /upload/pdf/:documentId
 * Query: ?action=download (force download) or default inline view
 */
router.get("/pdf/:documentId", async (req, res, next) => {
  try {
    const { documentId } = req.params;

    // Support auth via header or query param (for opening in new tab)
    const header = req.headers.authorization || "";
    const headerToken = header.startsWith("Bearer ") ? header.substring(7) : null;
    const token = headerToken || req.query.token;

    if (!token) {
      return res.status(401).json({ success: false, error: "Authorization required" });
    }

    const jwt = require("jsonwebtoken");
    const { JWT_SECRET } = require("../config/env");
    let user;
    try {
      user = jwt.verify(token, JWT_SECRET);
    } catch {
      return res.status(401).json({ success: false, error: "Invalid or expired token" });
    }

    const doc = await Document.findOne({ documentId });

    if (!doc) {
      return res.status(404).json({ success: false, error: "Document not found" });
    }

    // Access control: only owner or admin
    if (user.role !== 'admin' && doc.userId.toString() !== user.id) {
      return res.status(403).json({ success: false, error: "Access denied" });
    }

    if (!doc.filePath) {
      return res.status(404).json({ success: false, error: "PDF file not available (uploaded before PDF storage was enabled)" });
    }

    const filePath = path.join(PDF_STORAGE_DIR, doc.filePath);
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ success: false, error: "PDF file not found on disk" });
    }

    const disposition = req.query.action === 'download' ? 'attachment' : 'inline';
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `${disposition}; filename="${encodeURIComponent(doc.fileName)}"`);
    fs.createReadStream(filePath).pipe(res);
  } catch (err) {
    logger.error(`PDF serve error: ${err.message}`);
    next(err);
  }
});

module.exports = router;