const express = require("express");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { body, validationResult } = require("express-validator");
const User = require("../models/User");
const auth = require("../middleware/auth");
const { JWT_SECRET, ADMIN_SECRET_KEY } = require("../config/env");

const router = express.Router();

const signToken = (user) => jwt.sign({ id: user._id, role: user.role }, JWT_SECRET, { expiresIn: "7d" });

router.post(
  "/register",
  [
    body("name").notEmpty().withMessage("Name is required"),
    body("email").isEmail().withMessage("Valid email is required"),
    body("password").isLength({ min: 6 }).withMessage("Password must be at least 6 characters"),
  ],
  async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    const { name, email, password, adminSecret } = req.body;

    try {
      const existing = await User.findOne({ email });
      if (existing) {
        return res.status(409).json({ error: "Email already registered" });
      }

      const isAdmin = Boolean(
        adminSecret && ADMIN_SECRET_KEY && adminSecret === ADMIN_SECRET_KEY
      );

      const hashed = await bcrypt.hash(password, 10);
      const user = await User.create({ 
        name, 
        email, 
        password: hashed,
        role: isAdmin ? 'admin' : 'user'
      });

      console.log(`✓ User registered: ${user.name}, Email: ${user.email}, Role: ${user.role}`);

      const token = signToken(user);
      return res.status(201).json({
        user: { id: user._id, name: user.name, email: user.email, role: user.role },
        token,
      });
    } catch (err) {
      console.error("Register error:", err.message);
      return res.status(500).json({ error: "Server error" });
    }
  }
);

router.post(
  "/login",
  [
    body("email").isEmail().withMessage("Valid email is required"),
    body("password").notEmpty().withMessage("Password is required"),
  ],
  async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }

    const { email, password } = req.body;

    try {
      const user = await User.findOne({ email });
      if (!user) {
        return res.status(401).json({ error: "Invalid credentials" });
      }

      const isMatch = await bcrypt.compare(password, user.password);
      if (!isMatch) {
        return res.status(401).json({ error: "Invalid credentials" });
      }

      console.log(`✓ User logged in: ${user.name}, Email: ${user.email}, Role: ${user.role}`);

      const token = signToken(user);
      return res.json({ user: { id: user._id, name: user.name, email: user.email, role: user.role }, token });
    } catch (err) {
      console.error("Login error:", err.message);
      return res.status(500).json({ error: "Server error" });
    }
  }
);

router.get("/me", auth, async (req, res) => {
  try {
    const user = await User.findById(req.user.id).select("name email");
    if (!user) return res.status(404).json({ error: "User not found" });
    return res.json({ user });
  } catch (err) {
    console.error("Me error:", err.message);
    return res.status(500).json({ error: "Server error" });
  }
});

module.exports = router;
