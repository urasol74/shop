import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainPage from './MainPage';
import SectionsPage from './SectionsPage';
import ProductPage from './ProductPage';
import ProductsByCategory from './ProductsByCategory';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<MainPage />} />
                <Route path="/women" element={<SectionsPage sectionType="women" sectionVerbose="Женщина" />} />
                <Route path="/men" element={<SectionsPage sectionType="men" sectionVerbose="Мужчина" />} />
                <Route path="/kids" element={<SectionsPage sectionType="kids" sectionVerbose="Дети" />} />
                <Route path="/underwear" element={<SectionsPage sectionType="underwear" sectionVerbose="Бельё" />} />
                <Route path="/product/:id" element={<ProductPage />} />
                <Route path="/:sectionType/category/:categoryRaw" element={<ProductsByCategory />} />
            </Routes>
        </Router>
    );
}

export default App; 