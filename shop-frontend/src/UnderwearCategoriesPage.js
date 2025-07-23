import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

function UnderwearCategoriesPage({ gender, sectionVerbose, backUrl }) {
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        fetch(`http://178.212.198.23:5000/api/underwear-categories?gender=${gender}`)
            .then(res => res.json())
            .then(data => setCategories(data));
    }, [gender]);

    // Определяем url для перехода к товарам
    const sectionUrl =
        gender === 'жiн' ? 'underwear-woman/category'
            : gender === 'чол' ? 'underwear-men/category'
                : gender === 'хлопч' ? 'underwear-boy/category'
                    : gender === 'дiвч' ? 'underwear-girl/category'
                        : '';

    return (
        <div className="main-block">
            <Link to={backUrl} className="back-btn">← Назад</Link>
            <h3>{sectionVerbose}</h3>
            <div className="sections-2">
                {categories.map(category => (
                    <Link
                        className="section-2"
                        key={category.raw}
                        to={`/underwear/${sectionUrl}/${category.raw}`}
                    >
                        <div>{category.pretty}</div>
                    </Link>
                ))}
            </div>
        </div>
    );
}

export default UnderwearCategoriesPage; 