const express = require('express');
const router = express.Router();
const {
  createEvent,
  getEvents,
  getEventById,
  updateEvent,
  deleteEvent,
  registerForEvent,
  unregisterFromEvent
} = require('../controllers/eventController');
const { protect, isOrganiser } = require('../middleware/authMiddleware');

router.get('/', getEvents);
router.get('/:id', getEventById);
router.post('/', protect, isOrganiser, createEvent);
router.post('/:id/register', protect, registerForEvent);
router.put('/:id', protect, isOrganiser, updateEvent);
router.delete('/:id', protect, isOrganiser, deleteEvent);
router.delete('/:id/register', protect, unregisterFromEvent);

module.exports = router;