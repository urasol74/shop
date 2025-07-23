import React from 'react';
import { Link } from 'react-router-dom';
import './App.css';

function MainPage() {
    return (
        <div className="main-block">
            <h3 className="main-title">Benetton Одесса Дерибасовская</h3>
            <form action="/search" method="get" className="search-form">
                <input
                    type="text"
                    name="q"
                    className="search-input"
                    placeholder="Поиск по артикулу, названию, цвету, размеру..."
                />
                <button type="submit" className="search-btn">Найти</button>
            </form>
            <div className="sections">
                <Link className="section" to="/women">
                    <img src="/image/women.png" alt="Женщина" />
                    <div>Женщина</div>
                </Link>
                <Link className="section" to="/men">
                    <img src="/image/men.png" alt="Мужчина" />
                    <div>Мужчина</div>
                </Link>
                <Link className="section" to="/kids">
                    <img src="/image/kids.png" alt="Дети" />
                    <div>Дети</div>
                </Link>
                <Link className="section" to="/underwear">
                    <img src="/image/underwear.png" alt="Бельё" />
                    <div>Бельё</div>
                </Link>
            </div>
        </div>
    );
}

export default MainPage; 