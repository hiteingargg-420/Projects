import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import CreateEvent from './pages/CreateEvent';
import ManageEvents from './pages/ManageEvents';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Dashboard />
            </ProtectedRoute>} /> 
            <Route path="/create-event"
            element={
              <ProtectedRoute>
                <CreateEvent />
                </ProtectedRoute>
            }  />
            <Route
  path="/manage-events"
  element={
    <ProtectedRoute>
      <ManageEvents />
    </ProtectedRoute>
  }
/>   </Routes>
    </BrowserRouter>
  );
}

export default App;