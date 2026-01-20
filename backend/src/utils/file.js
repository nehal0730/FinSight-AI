const generateSafeFilename = (originalName) => {
  const timestamp = Date.now();
  return `${timestamp}_${originalName.replace(/\s+/g, "_")}`; //replace spaces with underscores
};

module.exports = { generateSafeFilename };
