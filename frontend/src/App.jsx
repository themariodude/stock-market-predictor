import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import StockDetail from "./pages/StockDetail";

// BrowserRouter enables client-side navigation without full page reloads.
function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Main page */}
        <Route path="/" element={<Home />} />
        {/* Grid of all tracked defense stocks */}
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Shows the data for an individual stock */}
        <Route path="/stocks/:ticker" element={<StockDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;