const multer = require("multer"); //for handling file uploads
const { MAX_FILE_SIZE } = require("../config/env");

// Store files in memory (buffer) instead of disk for direct streaming to AI service
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: MAX_FILE_SIZE, // 50 MB
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype !== "application/pdf") {
      cb(new Error("Only PDF files are allowed"));
    } else {
      cb(null, true); //cb:callback, null → no error, true → file accepted
    }
  }
});

module.exports = upload;