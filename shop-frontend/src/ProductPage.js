import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

function ProductPage() {
    const { id } = useParams();
    const [product, setProduct] = useState(null);
    const [currentImg, setCurrentImg] = useState(0);

    useEffect(() => {
        fetch(`http://178.212.198.23:5000/api/product/${id}`)
            .then(res => res.json())
            .then(data => setProduct(data));
    }, [id]);

    if (!product) return <div>Загрузка...</div>;

    const images = product.images || [];

    const prevImg = () => setCurrentImg((currentImg - 1 + images.length) % images.length);
    const nextImg = () => setCurrentImg((currentImg + 1) % images.length);

    return (
        <div className="main-block">
            <Link to={-1} className="back-btn">← Назад</Link>
            <div className="slider-container">
                {images.length > 0 && (
                    <>
                        <button className="slider-arrow left" type="button" onClick={prevImg}>&#8592;</button>
                        <div className="product-slider">
                            <img src={`/static/pic/list/${images[currentImg]}`} alt={product.name} style={{ maxWidth: '300px', maxHeight: '300px' }} />
                        </div>
                        <button className="slider-arrow right" type="button" onClick={nextImg}>&#8594;</button>
                    </>
                )}
            </div>
            <div className="product-block name-block">
                <div className="product-name-list">{product.name} {product.art}</div>
            </div>
            <div className="product-block price-block">
                <div className="product-prices-list">
                    {product.old_price && <span className="old-price-list">{product.old_price} грн.</span>}
                    <span className="new-price-list">{product.new_price} грн.</span>
                    {product.sale && <span className="big-sale">-{product.sale}%</span>}
                </div>
            </div>
            {product.color_size_map && product.color_size_map.length > 0 && (
                <div className="meta-block">
                    <table style={{ width: '100%', textAlign: 'center', borderCollapse: 'collapse' }}>
                        <thead>
                            <tr>
                                <th>Цвет</th>
                                <th>Размер</th>
                            </tr>
                        </thead>
                        <tbody>
                            {product.color_size_map.map(cs => (
                                <tr key={cs.color}>
                                    <td>{cs.color}</td>
                                    <td>{cs.sizes.join(', ')}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

export default ProductPage; 