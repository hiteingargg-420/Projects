import { useState, useEffect } from 'react';
import axios from 'axios';

function ManageEvents() {
  const userId = localStorage.getItem('userId');
  const token = localStorage.getItem('token');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [attendees, setAttendees] = useState([]);

  const fetchMyEvents = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/events`);
      const mine = res.data.filter((event) => event.organiser._id === userId);
      setEvents(mine);
    } catch (err) {
      setMessage('Failed to load events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyEvents();
  }, []);

  const handleDelete = async (eventId) => {
    setMessage('');
    try {
      await axios.delete(`${import.meta.env.VITE_API_URL}/api/events/${eventId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMessage('Event deleted');
      fetchMyEvents();
    } catch (err) {
      setMessage(err.response?.data?.message || 'Delete failed');
    }
  };

  const toggleAttendees = async (eventId) => {
    if (expandedEvent === eventId) {
      setExpandedEvent(null);
      return;
    }
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/events/${eventId}`);
      setAttendees(res.data.attendees);
      setExpandedEvent(eventId);
    } catch (err) {
      setMessage('Failed to load attendees');
    }
  };

  if (loading) return <p className="p-8">Loading your events...</p>;

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-4">Manage My Events</h2>
      {message && <p className="text-green-600 mb-3">{message}</p>}

      {events.length === 0 && <p className="text-gray-500">You haven't created any events yet.</p>}

      <div className="flex flex-col gap-4">
        {events.map((event) => (
          <div key={event._id} className="border rounded-lg p-4 shadow">
            <h3 className="text-xl font-semibold">{event.title}</h3>
            <p className="text-gray-500 text-sm">{new Date(event.date).toDateString()}</p>
            <p className="text-sm text-gray-500 mt-1">
              {event.attendees.length} / {event.maxAttendees} registered
            </p>

            <div className="flex flex-wrap gap-2 mt-3">
  <button
    onClick={() => toggleAttendees(event._id)}
    className="flex-1 bg-gray-700 text-white px-3 py-2 rounded hover:bg-gray-800 text-sm"
  >
    {expandedEvent === event._id ? 'Hide Attendees' : 'View Attendees'}
  </button>
  <button
    onClick={() => handleDelete(event._id)}
    className="flex-1 bg-red-600 text-white px-3 py-2 rounded hover:bg-red-700 text-sm"
  >
    Delete
  </button>
</div>

            {expandedEvent === event._id && (
              <div className="mt-3 border-t pt-3">
                {attendees.length === 0 ? (
                  <p className="text-gray-500 text-sm">No one has registered yet.</p>
                ) : (
                  <ul className="text-sm text-gray-700">
                    {attendees.map((a) => (
                      <li key={a._id}>{a.name} — {a.email}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ManageEvents;