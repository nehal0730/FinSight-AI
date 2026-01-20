const multer = require("multer"); //for handling file uploads
const { MAX_FILE_SIZE } = require("../config/env");

const upload = multer({
  dest: "uploads/",
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