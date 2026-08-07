const Event = require('../models/Event');
const sendEmail = require('../utils/sendEmail');

// Create event — organiser only
const createEvent = async (req, res) => {
  try {
    const { title, description, date, location, maxAttendees } = req.body;

    const event = await Event.create({
      title,
      description,
      date,
      location,
      maxAttendees,
      organiser: req.user._id
    });

    res.status(201).json(event);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Get all events — public
const getEvents = async (req, res) => {
  try {
    const events = await Event.find().populate('organiser', 'name email');
    res.json(events);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Get single event — public
const getEventById = async (req, res) => {
  try {
    const event = await Event.findById(req.params.id).populate('organiser', 'name email')
    .populate('attendees', 'name email');
    if (!event) {
      return res.status(404).json({ message: 'Event not found' });
    }
    res.json(event);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Update event — organiser only, and only their own event
const updateEvent = async (req, res) => {
  try {
    const event = await Event.findById(req.params.id);
    if (!event) {
      return res.status(404).json({ message: 'Event not found' });
    }

    if (event.organiser.toString() !== req.user._id.toString()) {
      return res.status(403).json({ message: 'Not authorized to edit this event' });
    }

    const updatedEvent = await Event.findByIdAndUpdate(req.params.id, req.body, {
      new: true,
      runValidators: true
    });

    res.json(updatedEvent);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Delete event — organiser only, and only their own event
const deleteEvent = async (req, res) => {
  try {
    const event = await Event.findById(req.params.id);
    if (!event) {
      return res.status(404).json({ message: 'Event not found' });
    }

    if (event.organiser.toString() !== req.user._id.toString()) {
      return res.status(403).json({ message: 'Not authorized to delete this event' });
    }

    await event.deleteOne();
    res.json({ message: 'Event removed' });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};
// Register for an event — logged-in users only
const registerForEvent = async (req, res) => {
  try {
    const event = await Event.findById(req.params.id);
    if (!event) {
      return res.status(404).json({ message: 'Event not found' });
    }

    // Prevent duplicate registration
    const alreadyRegistered = event.attendees.some(
      (attendeeId) => attendeeId.toString() === req.user._id.toString()
    );
    if (alreadyRegistered) {
      return res.status(400).json({ message: 'Already registered for this event' });
    }

    // Prevent overbooking
    if (event.attendees.length >= event.maxAttendees) {
      return res.status(400).json({ message: 'Event is full' });
    }

    event.attendees.push(req.user._id);
    await event.save();
    await sendEmail(
  req.user.email,
  'Event Registration Confirmed',
  `You have successfully registered for ${event.title} on ${event.date.toDateString()}.`
);

    res.json({
      message: 'Successfully registered',
      attendeeCount: event.attendees.length,
      maxAttendees: event.maxAttendees
    });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};
const unregisterFromEvent = async (req, res) => {
  try {
    const event = await Event.findById(req.params.id);
    if (!event) {
      return res.status(404).json({ message: 'Event not found' });
    }

    event.attendees = event.attendees.filter(
      (attendeeId) => attendeeId.toString() !== req.user._id.toString()
    );
    await event.save();

    res.json({
      message: 'Successfully unregistered',
      attendeeCount: event.attendees.length
    });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};
module.exports = { createEvent, getEvents, getEventById, updateEvent, deleteEvent, registerForEvent, unregisterFromEvent };