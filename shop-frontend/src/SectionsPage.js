import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const underwearOptions = [
    { url: '/underwear/underwear-woman', img: '/image/underwear-women.png', label: 'Женщина' },
    { url: '/underwear/underwear-men', img: '/image/underwear-men.png', label: 'Мужчина' },
    { url: '/underwear/underwear-boy', img: '/image/underwear-boy.png', label: 'Мальчик' },
    { url: '/underwear/underwear-girl', img: '/image/underwear-girl.png', label: 'Девочка' },
];

function SectionsPage({ sectionType, sectionVerbose }) {
    const [categories, setCategories] = useState([]);

    useEffect(() => {
        if (sectionType === 'women' || sectionType === 'men' || sectionType === 'kids') {
            fetch(`http://178.212.198.23:5000/api/categories?section=${sectionType}`)
                .then(res => res.json())
                .then(data => setCategories(data));
        }
    }, [sectionType]);

    return (
        <div className="main-block">
            <Link to="/" className="back-btn">← Назад</Link>
            <h3>{sectionVerbose}</h3>
            <div className={sectionType === 'underwear' ? 'sections' : 'sections-2'}>
                {sectionType === 'underwear' ? (
                    underwearOptions.map(opt => (
                        <Link className="section" key={opt.url} to={opt.url}>
                            <img src={opt.img} alt={opt.label} />
                            <div>{opt.label}</div>
                        </Link>
                    ))
                ) : (
                    categories.length > 0 ? (
                        categories.map(category => (
                            <Link
                                className="section-2"
                                key={category.raw}
                                to={`/${sectionType}/category/${category.raw}`}
                            >
                                <div>{category.pretty}</div>
                            </Link>
                        ))
                    ) : (
                        <div style={{ padding: '2em', textAlign: 'center', color: '#888' }}>Категории для раздела "{sectionVerbose}" появятся здесь</div>
                    )
                )}
            </div>
        </div>
    );
}

export default SectionsPage;