const fs = require("fs");

const deleteFile = (filePath) => {
  fs.unlink(filePath, (err) => {
    if (err) {
      console.error("Cleanup failed:", err.message);
    }
  });
};

module.exports = { deleteFile };
