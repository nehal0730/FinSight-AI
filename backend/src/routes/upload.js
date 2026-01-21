const express = require("express");
const axios = require("axios"); //for making HTTP requests
const fs = require("fs"); //for file system operations
const FormData = require("form-data"); //to create form data for file upload
const upload = require("../middleware/upload.js");
const auth = require("../middleware/auth");
const { generateSafeFilename } = require("../utils/file");
const { deleteFile } = require("../utils/cleanup");
const logger = require("../config/logger");
const { AI_SERVICE_URL } = require("../config/env");

const router = express.Router();

router.post("/", auth, upload.single("file"), async (req, res, next) => {
  let newPath;
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }
    
    const safeFilename = generateSafeFilename(req.file.originalname);
    newPath = `uploads/${safeFilename}`;

    fs.renameSync(req.file.path, newPath);

    const formData = new FormData(); 
    formData.append(
      "file",
      fs.createReadStream(newPath),
      req.file.originalname
    );

    // Node sends file to FastAPI, FastAPI analyzes file, Returns result
    const aiResponse = await axios.post(
      `${AI_SERVICE_URL}/analyze`,
      formData,
      { headers: formData.getHeaders() }
    );

    logger.info(`File processed: ${safeFilename}`);

    res.status(200).json({
      success: true,
      data: {
        originalFilename: req.file.originalname,
        storedFilename: safeFilename,
        aiResponse: aiResponse.data
      },
      error: null
    });

  } catch (err) {
    logger.error(err.message);
    next(err);
    // console.error(err.message);

    // return res.status(500).json({
    //   success: false,
    //   data: null,
    //   error: {
    //     code: "UPLOAD_FAILED",
    //     message: "File processing failed"
    //   }
    // });
  } finally {
    if (newPath) {
      deleteFile(newPath);
    }
  }
});

module.exports = router;