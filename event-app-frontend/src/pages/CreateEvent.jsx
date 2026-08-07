import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

function CreateEvent() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState('');
  const [location, setLocation] = useState('');
  const [maxAttendees, setMaxAttendees] = useState(100);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!title || !description || !date || !location) {
      setError('All fields are required');
      return;
    }

    try {
      await axios.post(
        `${import.meta.env.VITE_API_URL}/api/events`,
        { title, description, date, location, maxAttendees },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create event');
    }
  };

  return (
    <div className="p-8 max-w-lg mx-auto">
      <h2 className="text-2xl font-bold mb-4">Create Event</h2>
      {error && <p className="text-red-600 mb-3">{error}</p>}
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="text"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="border rounded p-2"
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="border rounded p-2"
        />
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="border rounded p-2"
        />
        <input
          type="text"
          placeholder="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="border rounded p-2"
        />
        <input
          type="number"
          placeholder="Max Attendees"
          value={maxAttendees}
          onChange={(e) => setMaxAttendees(e.target.value)}
          className="border rounded p-2"
        />
        <button type="submit" className="bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
          Create Event
        </button>
      </form>
    </div>
  );
}

export default CreateEvent;