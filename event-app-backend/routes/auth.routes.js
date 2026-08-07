const express = require('express');
const router = express.Router();
const { registerUser, loginUser } = require('../controllers/authController');
const { protect, isOrganiser } = require('../middleware/authMiddleware');

router.post('/register', registerUser);
router.post('/login', loginUser);

router.get('/profile', protect, (req, res) => {
  res.json({ message: 'You are logged in', user: req.user });
});

router.get('/organiser-only', protect, isOrganiser, (req, res) => {
  res.json({ message: 'Welcome, organiser' });
});

module.exports = router;