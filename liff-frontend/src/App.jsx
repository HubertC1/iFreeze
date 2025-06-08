import React, { useEffect, useState } from 'react';
import './App.css';

// API base URL is now read from VITE_NGROK_URL_BASE in .env file
const API_BASE = import.meta.env.VITE_NGROK_URL_BASE || 'http://localhost:8000';
const API_URL = `${API_BASE}/fridge/foods`;
const IMAGE_PLACEHOLDER = '/app/static/images/api_20250607_194207_photo.jpg'; // Placeholder image path

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

function FoodCard({ food, onDetails }) {
  return (
    <div className="card">
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
        <div className="status">Status: <b>{food.status}</b></div>
        <button className="details-btn" onClick={() => onDetails(food)}>Details</button>
      </div>
    </div>
  );
}

function DetailsModal({ food, onClose }) {
  if (!food) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>{food.name}</h2>
        <img src={IMAGE_PLACEHOLDER} alt={food.name} style={{width: '100%', borderRadius: '10px', marginBottom: '1rem'}} />
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
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  // Polling for live updates
  useEffect(() => {
    let isMounted = true;
    const fetchFoods = () => {
      console.log('Fetching from:', API_URL);
      fetch(API_URL)
        .then(res => {
          console.log('Response status:', res.status);
          if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
          }
          return res.json();
        })
        .then(data => {
          console.log('Received data:', data);
          if (isMounted) {
            setFoods(data);
            setLoading(false);
          }
        })
        .catch(error => {
          console.error('Error fetching foods:', error);
          if (isMounted) {
            setLoading(false);
          }
        });
    };
    fetchFoods();
    const interval = setInterval(fetchFoods, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="container">
      <h1>Fridge Contents</h1>
      {loading ? <div>Loading...</div> : (
        <div className="card-grid">
          {foods.map(food => (
            <FoodCard key={food.id} food={food} onDetails={setSelected} />
          ))}
        </div>
      )}
      <DetailsModal food={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

export default App;
