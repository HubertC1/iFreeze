import React, { useEffect, useState } from 'react';
import './App.css';

// API base URL is now read from VITE_NGROK_URL_BASE in .env file
const API_BASE = import.meta.env.VITE_NGROK_URL_BASE || 'http://localhost:8000';
console.log('API_BASE:', API_BASE);
const API_URL = `${API_BASE}/fridge/foods`;
const IMAGE_PLACEHOLDER = `${API_BASE}/api/images/placeholder.jpg`; // Placeholder image path

const categoryIcons = {
  Food: '🍕',
  Transportation: '🚗',
  Supplies: '🧻',
  Entertainment: '🧸',
  Education: '📚',
  Medical: '💊',
  Clothing: '👚',
  Housing: '🏠',
  Social: '🧑‍🤝‍🧑',
  OtherExpense: '💸',
};

const statusColors = {
  spoiled: '#FFE5E5',    // Light red
  spoiling: '#FFF4E5',   // Light orange
  fresh: '#E5FFE5'       // Light green
};

function FoodCard({ food, onDetails }) {
  const statusColor = statusColors[food.status.toLowerCase()] || '#FFFFFF';
  
  return (
    <div className="card" style={{ backgroundColor: statusColor }}>
      <div className="card-header">
        <span className="category-icon">{categoryIcons[food.category] || '🍽️'}</span>
        <span className="category-title">{food.category}</span>
      </div>
      <div className="card-body">
        <h3>{food.name}</h3>
        <div className="dates">
          <span>Added: {food.added_date}</span><br/>
          {food.expiry_date && <span>Expiry: {food.expiry_date}</span>}
        </div>
        <div className="status">
          Status: <b>{food.status}</b>
        </div>
        <button className="details-btn" onClick={() => onDetails(food)}>Details</button>
      </div>
    </div>
  );
}

function DetailsModal({ food, onClose }) {
  if (!food) return null;
  const statusColor = statusColors[food.status.toLowerCase()] || '#FFFFFF';
  const imgUrl = food.temp_object_id !== undefined && food.temp_object_id !== null
    ? `${API_BASE}/static/ind_images/object_${food.temp_object_id}.png`
    : IMAGE_PLACEHOLDER;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ backgroundColor: statusColor }}>
        <h2>{food.name}</h2>
        <img src={imgUrl} alt={food.name} style={{width: '100%', borderRadius: '10px', marginBottom: '1rem'}} />
        <p><b>Category:</b> {food.category}</p>
        <p><b>Added:</b> {food.added_date}</p>
        {food.expiry_date && <p><b>Expiry:</b> {food.expiry_date}</p>}
        <p><b>Status:</b> {food.status}</p>
        <button onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function App() {
  const [foods, setFoods] = useState([]);
  const [selectedFood, setSelectedFood] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchFoods = async () => {
      try {
        const response = await fetch(API_URL);
        if (!response.ok) {
          throw new Error('Failed to fetch foods');
        }
        const data = await response.json();
        
        // Sort foods by status priority (spoiled -> spoiling -> fresh)
        const statusPriority = { spoiled: 0, spoiling: 1, fresh: 2 };
        const sortedFoods = data.sort((a, b) => 
          statusPriority[a.status.toLowerCase()] - statusPriority[b.status.toLowerCase()]
        );
        
        setFoods(sortedFoods);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchFoods();
  }, []);

  return (
    <div className="container">
      <h1>Fridge Contents</h1>
      {loading ? <div>Loading...</div> : (
        <div className="card-grid">
          {foods.map(food => (
            <FoodCard key={food.id} food={food} onDetails={setSelectedFood} />
          ))}
        </div>
      )}
      <DetailsModal food={selectedFood} onClose={() => setSelectedFood(null)} />
    </div>
  );
}

export default App;
