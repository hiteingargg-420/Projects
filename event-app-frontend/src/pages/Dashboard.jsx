import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getGoogleCalendarLink } from '../utils/calendarLink';
import axios from 'axios';

function Dashboard() {
  const role = localStorage.getItem('role');
  const token = localStorage.getItem('token');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const fetchEvents = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/events`);
      setEvents(res.data);
    } catch (err) {
      setError('Failed to load events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const handleRegister = async (eventId) => {
    setMessage('');
    try {
      const res = await axios.post(
        `${import.meta.env.VITE_API_URL}/api/events/${eventId}/register`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessage(res.data.message);
      fetchEvents();
    } catch (err) {
      setMessage(err.response?.data?.message || 'Registration failed');
    }
  };

  if (loading) return <p className="p-8">Loading events...</p>;
  if (error) return <p className="p-8 text-red-600">{error}</p>;

  return (
    <div className="p-8">
      <h2 className="text-3xl font-bold text-blue-600 mb-2">Dashboard</h2>
      <p className="text-gray-600 mb-4">Logged in as: {role}</p>

      <div className="flex gap-2 mb-4">
  <button
    onClick={handleLogout}
    className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
  >
    Logout
  </button>

  {role === 'organiser' && (
    <a href="/create-event" className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
      + Create Event
    </a>
  )}
  {role === 'organiser' && (
    <a href="/manage-events" className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-800">
      Manage My Events
    </a>
  )}
</div>

      {message && <p className="text-green-600 mb-4">{message}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {events.map((event) => (
          <div key={event._id} className="border rounded-lg p-4 shadow hover:shadow-md transition">
            <h3 className="text-xl font-semibold">{event.title}</h3>
            <p className="text-gray-500 text-sm">{new Date(event.date).toDateString()}</p>
            <p className="text-gray-700 mt-2">{event.description}</p>
            <p className="text-sm text-gray-500 mt-2">📍 {event.location}</p>
            <p className="text-sm text-gray-500">
              {event.attendees.length} / {event.maxAttendees} registered
            </p>

            {role === 'student' && (
              <button
                onClick={() => handleRegister(event._id)}
                className="mt-3 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Register
              </button>
            )}

            <a
              href={getGoogleCalendarLink(event)}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 block text-blue-600 underline text-sm"
            >
              Add to Calendar
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;