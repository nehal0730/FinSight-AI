require("dotenv").config(); //load environment variables from .env file

const express = require("express");
const multer = require("multer"); //for handling file uploads
const axios = require("axios"); //for making HTTP requests
const cors = require("cors"); //Browsers block requests between different ports by default, CORS allows frontend (5173) to talk to backend (5000)
const fs = require("fs"); //for file system operations
const FormData = require("form-data"); //to create form data for file upload

const app = express();
app.use(cors({ origin: "http://localhost:5173" }));

const path = require("path");

const upload = multer({
  dest: "uploads/",
  limits: {
    fileSize: parseInt(process.env.MAX_FILE_SIZE), // 50 MB
  },
  fileFilter: (req, file, cb) => {
    if (file.mimetype !== "application/pdf") {
      cb(new Error("Only PDF files are allowed"));
    } else {
      cb(null, true); //cb:callback, null → no error, true → file accepted
    }
  }
});

const generateSafeFilename = (originalName) => {
  const timestamp = Date.now();
  const safeName = originalName.replace(/\s+/g, "_"); //replace spaces with underscores
  return `${timestamp}_${safeName}`;
};



app.post("/upload", upload.single("file"), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }
    
    const safeFilename = generateSafeFilename(req.file.originalname);
    const newPath = `uploads/${safeFilename}`;

    fs.renameSync(req.file.path, newPath);

    const formData = new FormData(); 
    formData.append(
      "file",
      fs.createReadStream(newPath),
      req.file.originalname
    );

    // Node sends file to FastAPI, FastAPI analyzes file, Returns result
    const response = await axios.post(
      `${process.env.AI_SERVICE_URL}/analyze`,
      formData,
      { headers: formData.getHeaders() }
    );

    res.status(200).json({
      success: true,
      data: {
        originalFilename: req.file.originalname,
        storedFilename: safeFilename,
        aiResponse: response.data
      },
      error: null
    });

  } catch (err) {
    console.error(err.message);

    return res.status(500).json({
      success: false,
      data: null,
      error: {
        code: "UPLOAD_FAILED",
        message: "File processing failed"
      }
    });
  }
});

app.use((err, req, res, next) => {
  console.error(err.message);

  res.status(400).json({
    success: false,
    data: null,
    error: {
      code: "BAD_REQUEST",
      message: err.message
    }
  });
});


app.get("/health", (req, res) => {
  res.status(200).json({
    status: "UP",
    service: "Node Backend",
    timestamp: new Date().toISOString()
  });
});



const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Node backend running on port ${PORT}`);
});

