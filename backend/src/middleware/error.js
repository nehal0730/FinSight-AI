module.exports = ((err, req, res, next) => {
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