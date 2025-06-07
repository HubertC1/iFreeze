import React, { useEffect, useState } from 'react';
import './App.css';

// const API_URL = 'http://localhost:8000/fridge/foods'; // Change to your ngrok URL for production
const API_URL = 'https://516d-140-112-25-29.ngrok-free.app/fridge/foods'

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

  useEffect(() => {
    fetch(API_URL)
      .then(res => res.json())
      .then(data => {
        setFoods(data);
        setLoading(false);
      });
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
