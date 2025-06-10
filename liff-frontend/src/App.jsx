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

function FoodCard({ food, onDetails, onDelete }) {
  const statusColor = statusColors[food.status.toLowerCase()] || '#FFFFFF';
  const imgUrl = food.temp_object_id !== undefined && food.temp_object_id !== null
    ? `${API_BASE}/static/ind_images/object_${food.temp_object_id}.png`
    : IMAGE_PLACEHOLDER;

  const handleDragStart = (e) => {
    e.dataTransfer.setData('text/plain', food.id.toString());
    e.dataTransfer.effectAllowed = 'move';
    // Add visual feedback during drag
    setTimeout(() => {
      e.target.classList.add('dragging');
    }, 0);
  };

  const handleDragEnd = (e) => {
    e.target.classList.remove('dragging');
  };

  return (
    <div
      className={`card status-${food.status.toLowerCase()}`}
      onClick={() => onDetails(food)}
      draggable={true}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="card-status-bar"></div>
      <div className="card-content">
        <div className="category-badge">
          <span>{categoryIcons[food.category] || '🍽️'}</span>
          <span>{food.category}</span>
        </div>
        <div className="food-thumb-box">
          <img src={imgUrl} alt={food.name} className="food-thumb" />
        </div>
        <h3>{food.name}</h3>
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
      <div className="modal" onClick={e => e.stopPropagation()} style={{ backgroundColor: statusColor, position: 'relative' }}>
        <button className="modal-close-btn" onClick={onClose} title="Close">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 6L16 16M16 6L6 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
        <h2>{food.name}</h2>
        <p><b>Category:</b> {food.category}</p>
        <p><b>Added:</b> {food.added_date}</p>
        {food.expiry_date && <p><b>Expiry:</b> {food.expiry_date}</p>}
        <p><b>Status:</b> {food.status}</p>
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <img src={imgUrl} alt={food.name} style={{ maxWidth: '100%', borderRadius: '10px', background: '#f0f0f0' }} />
        </div>
      </div>
    </div>
  );
}

function RecipeSection({ foods }) {
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recipe, setRecipe] = useState(null);
  const [error, setError] = useState(null);

  const handleToggle = (id) => {
    setSelected(sel => sel.includes(id) ? sel.filter(i => i !== id) : [...sel, id]);
  };

  const handleGetRecipe = async () => {
    setLoading(true);
    setError(null);
    setRecipe(null);
    try {
      const selectedFoods = foods.filter(f => selected.includes(f.id));
      const ingredientNames = selectedFoods.map(f => f.name);
      const response = await fetch('/find_recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ingredients: ingredientNames })
      });
      if (!response.ok) throw new Error('Failed to fetch recipe');
      const data = await response.json();
      setRecipe(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="recipe-section">
      <h2>Get a Recipe</h2>
      <div className="ingredient-list">
        {foods.map(food => (
          <label
            key={food.id}
            className={`ingredient-checkbox${selected.includes(food.id) ? ' selected' : ''}`}
            onClick={() => handleToggle(food.id)}
          >
            <input
              type="checkbox"
              checked={selected.includes(food.id)}
              onChange={() => handleToggle(food.id)}
              style={{ display: 'none' }}
            />
            {food.name}
          </label>
        ))}
      </div>
      <button className="recipe-btn" onClick={handleGetRecipe} disabled={loading || selected.length === 0}>
        {loading ? 'Finding Recipe...' : 'Get Recipe'}
      </button>
      {error && <div style={{ color: 'red', marginBottom: '1rem' }}>{error}</div>}
      {recipe && (
        <div className="recipe-card">
          <h3>{recipe.title}</h3>
          {recipe.url && recipe.url !== 'N/A' && <div className="recipe-meta"><a href={recipe.url} target="_blank" rel="noopener noreferrer">Source</a></div>}
          <div className="recipe-meta">{recipe.summary}</div>
          <div><b>Ingredients:</b>
            <ul>{recipe.ingredients.map((ing, i) => <li key={i}>{ing}</li>)}</ul>
          </div>
          <div><b>Instructions:</b>
            <ol>{recipe.instructions.split('\n').map((step, i) => <li key={i}>{step}</li>)}</ol>
          </div>
        </div>
      )}
    </div>
  );
}

function TrashBin({ onDrop, isDragOver }) {
  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const foodId = parseInt(e.dataTransfer.getData('text/plain'));
    onDrop(foodId);
  };

  return (
    <div 
      className={`trash-bin ${isDragOver ? 'drag-over' : ''}`}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div className="trash-bin-icon">
        🗑️
      </div>
      <div className="trash-bin-text">
        {isDragOver ? 'Drop to Delete' : 'Drag items here to delete'}
      </div>
    </div>
  );
}

function App() {
  const [foods, setFoods] = useState([]);
  const [selectedFood, setSelectedFood] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

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

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this food item?')) return;
    try {
      const response = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete');
      setFoods(foods => foods.filter(f => f.id !== id));
    } catch (err) {
      alert('Error deleting: ' + err.message);
    }
  };

  const handleTrashDrop = (foodId) => {
    handleDelete(foodId);
    setIsDragOver(false);
  };

  const handleDragEnter = () => {
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    // Only set dragOver to false if we're leaving the trash bin area completely
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setIsDragOver(false);
    }
  };

  return (
    <div className="container">
      <h1>Fridge Contents</h1>
      {loading ? <div>Loading...</div> : (
        <>
          <div className="card-grid">
            {foods.map(food => (
              <FoodCard key={food.id} food={food} onDetails={setSelectedFood} onDelete={handleDelete} />
            ))}
          </div>
          <div 
            className="trash-bin-container"
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
          >
            <TrashBin onDrop={handleTrashDrop} isDragOver={isDragOver} />
          </div>
        </>
      )}
      <DetailsModal food={selectedFood} onClose={() => setSelectedFood(null)} />
      <RecipeSection foods={foods.filter(f => f.status.toLowerCase() !== 'spoiled')} />
    </div>
  );
}

export default App;
