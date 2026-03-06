const express = require("express");
const axios = require("axios"); //for making HTTP requests
const FormData = require("form-data"); //to create form data for file upload
const { Readable } = require("stream");
const upload = require("../middleware/upload.js");
const auth = require("../middleware/auth");
const logger = require("../config/logger");
const { AI_SERVICE_URL } = require("../config/env");
const Document = require("../models/Document");

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
    
    await Document.create({
      fileName: req.file.originalname,
      documentId: documentId,
      userId: req.user.id,
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

module.exports = router;