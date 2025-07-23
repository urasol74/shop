import React, { useEffect, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';

function ProductsByCategory() {
    const { sectionType, categoryRaw } = useParams();
    const [products, setProducts] = useState([]);
    const [sort, setSort] = useState('asc');
    const [genders, setGenders] = useState([]);
    const [activeGender, setActiveGender] = useState('all');
    const [searchParams, setSearchParams] = useSearchParams();

    useEffect(() => {
        const sortParam = searchParams.get('sort') || 'asc';
        setSort(sortParam);
        fetch(`http://178.212.198.23:5000/api/products?section=${sectionType}&category=${categoryRaw}&sort=${sortParam}`)
            .then(res => res.json())
            .then(data => {
                setProducts(data.products || data); // поддержка старого и нового API
                setGenders(data.genders || []);
            });
    }, [sectionType, categoryRaw, searchParams]);

    // Фильтрация по полу
    const filteredProducts = activeGender === 'all' ? products : products.filter(p => p.gender === activeGender);

    // Оставляем только по одному товару на артикул
    const uniqueProducts = [];
    const seenArts = new Set();
    for (const p of filteredProducts) {
        if (!seenArts.has(p.art)) {
            uniqueProducts.push(p);
            seenArts.add(p.art);
        }
    }

    return (
        <div className="main-block" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
            <Link to={`/${sectionType}`} className="back-btn">← Назад</Link>
            <h3>{sectionType.charAt(0).toUpperCase() + sectionType.slice(1)} {categoryRaw}</h3>
            {/* Сортировка */}
            <div className="sort-block">
                <button className={`sort-btn${sort === 'asc' ? ' active' : ''}`} onClick={() => setSearchParams({ sort: 'asc' })}>От низкой цены</button>
                <button className={`sort-btn${sort === 'desc' ? ' active' : ''}`} onClick={() => setSearchParams({ sort: 'desc' })}>От высокой цены</button>
            </div>
            {/* Фильтр по полу */}
            {genders && genders.length > 0 && (
                <div className="gender-filters-wrapper">
                    <div className="gender-filters">
                        <button className={`gender-btn${activeGender === 'all' ? ' active' : ''}`} onClick={() => setActiveGender('all')}>Все</button>
                        {genders.map(gender => (
                            <button key={gender} className={`gender-btn${activeGender === gender ? ' active' : ''}`} onClick={() => setActiveGender(gender)}>{gender}</button>
                        ))}
                    </div>
                </div>
            )}
            {/* Сетка товаров */}
            <div className="products-list">
                {uniqueProducts.length === 0 && <div>Нет товаров</div>}
                {uniqueProducts.map(product => (
                    <div className="product-card" key={product.id} data-gender={product.gender}>
                        <Link to={`/product/${product.id}`}>
                            <img
                                className="product-img"
                                src={`http://178.212.198.23:5000/static/pic/cat/${product.art}.jpg`}
                                alt={product.name}
                                onError={e => { e.target.onerror = null; e.target.src = '/image/no-image.png'; }}
                            />
                            <div className="product-name">{product.name} {product.art}</div>
                            <div className="product-prices">
                                {product.old_price && <span className="old-price">{product.old_price} грн.</span>}
                                <span className="new-price">{product.price} грн.</span>
                                {product.sale && <span className="sale">-{product.sale}%</span>}
                            </div>
                        </Link>
                    </div>
                ))}
            </div>
            <Link to={`/${sectionType}`} className="back-bottom">← Назад к категориям</Link>
        </div>
    );
}

export default ProductsByCategory;