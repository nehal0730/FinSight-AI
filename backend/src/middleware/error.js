const logger = require("../config/logger");

module.exports = ((err, req, res, next) => {
  logger.error(err.message);

  res.status(400).json({
    success: false,
    data: null,
    error: {
      code: "BAD_REQUEST",
      message: err.message
    }
  });
});