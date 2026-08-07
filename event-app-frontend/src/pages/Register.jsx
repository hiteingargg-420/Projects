import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';

function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/register`, { name, email, password, role });
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.message || 'Registration failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-sm bg-white p-6 rounded-lg shadow">
        <h2 className="text-2xl font-bold mb-4 text-center">Register</h2>
        {error && <p className="text-red-600 text-sm mb-3 text-center">{error}</p>}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border rounded p-2 w-full"
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border rounded p-2 w-full"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border rounded p-2 w-full"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="border rounded p-2 w-full"
          >
            <option value="student">Student</option>
            <option value="organiser">Organiser</option>
          </select>
          <button type="submit" className="bg-blue-600 text-white p-2 rounded hover:bg-blue-700">
            Register
          </button>
        </form>
        <p className="text-sm text-center mt-4 text-gray-600">
          Already have an account? <Link to="/login" className="text-blue-600 underline">Login</Link>
        </p>
      </div>
    </div>
  );
}

export default Register;