/**
 * MongoDB GridFS Storage - Replace local disk storage
 * Stores PDFs directly in MongoDB using GridFS
 */

const mongoose = require("mongoose");
const logger = require("../config/logger");

let bucket = null;

/**
 * Initialize GridFS bucket (call once at app startup)
 */
function initGridFS() {
  try {
    bucket = new mongoose.mongo.GridFSBucket(mongoose.connection.db, {
      bucketName: "pdfs"
    });
    logger.info("✓ MongoDB GridFS initialized");
    return bucket;
  } catch (err) {
    logger.error(`Failed to initialize GridFS: ${err.message}`);
    return null;
  }
}

/**
 * Upload PDF to MongoDB GridFS
 * 
 * @param {Buffer} fileBuffer - PDF file content
 * @param {string} fileName - Safe filename (e.g., "doc123.pdf")
 * @param {Object} metadata - File metadata (originalName, uploadedBy, etc.)
 * @returns {Promise<{success: boolean, fileId?: string, error?: string}>}
 */
async function uploadPDF(fileBuffer, fileName, metadata = {}) {
  if (!bucket) {
    logger.error("GridFS not initialized");
    return { success: false, error: "Storage not available" };
  }

  try {
    return new Promise((resolve, reject) => {
      const uploadStream = bucket.openUploadStream(fileName, {
        metadata: {
          uploadedAt: new Date(),
          ...metadata
        }
      });

      uploadStream.on("error", (err) => {
        logger.error(`GridFS upload error: ${err.message}`);
        reject(err);
      });

      uploadStream.on("finish", () => {
        const fileId = uploadStream.id.toString();
        logger.info(`✓ PDF uploaded to GridFS: ${fileName} (ID: ${fileId})`);
        resolve({ success: true, fileId });
      });

      uploadStream.end(fileBuffer);
    });
  } catch (err) {
    logger.error(`GridFS upload failed: ${err.message}`);
    return { success: false, error: err.message };
  }
}

/**
 * Download PDF from MongoDB GridFS
 * 
 * @param {string} fileId - MongoDB GridFS file ID
 * @returns {Promise<{success: boolean, data?: Buffer, error?: string}>}
 */
async function downloadPDF(fileId) {
  if (!bucket) {
    return { success: false, error: "Storage not available" };
  }

  try {
    return new Promise((resolve, reject) => {
      const chunks = [];
      const downloadStream = bucket.openDownloadStream(
        mongoose.Types.ObjectId(fileId)
      );

      downloadStream.on("error", (err) => {
        logger.error(`GridFS download error: ${err.message}`);
        reject(err);
      });

      downloadStream.on("data", (chunk) => {
        chunks.push(chunk);
      });

      downloadStream.on("end", () => {
        const data = Buffer.concat(chunks);
        logger.info(`✓ PDF downloaded from GridFS: ${fileId}`);
        resolve({ success: true, data });
      });
    });
  } catch (err) {
    logger.error(`GridFS download failed: ${err.message}`);
    return { success: false, error: err.message };
  }
}

/**
 * Delete PDF from MongoDB GridFS
 * 
 * @param {string} fileId - MongoDB GridFS file ID
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function deletePDF(fileId) {
  if (!bucket) {
    return { success: false, error: "Storage not available" };
  }

  try {
    await bucket.delete(mongoose.Types.ObjectId(fileId));
    logger.info(`✓ PDF deleted from GridFS: ${fileId}`);
    return { success: true };
  } catch (err) {
    logger.error(`GridFS delete failed: ${err.message}`);
    return { success: false, error: err.message };
  }
}

/**
 * Get file info from GridFS
 * 
 * @param {string} fileId - MongoDB GridFS file ID
 * @returns {Promise<{success: boolean, info?: Object, error?: string}>}
 */
async function getFileInfo(fileId) {
  if (!bucket) {
    return { success: false, error: "Storage not available" };
  }

  try {
    const files = await mongoose.connection.db
      .collection("pdfs.files")
      .find({ _id: mongoose.Types.ObjectId(fileId) })
      .toArray();

    if (files.length === 0) {
      return { success: false, error: "File not found" };
    }

    return { success: true, info: files[0] };
  } catch (err) {
    logger.error(`GridFS info failed: ${err.message}`);
    return { success: false, error: err.message };
  }
}

module.exports = {
  initGridFS,
  uploadPDF,
  downloadPDF,
  deletePDF,
  getFileInfo,
};
