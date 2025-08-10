document.addEventListener('DOMContentLoaded', () => {
    // Инициализация Telegram Web App
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    // Получаем данные пользователя из Telegram
    let userData = null;
    
    console.log('Telegram Web App данные:', {
        initData: tg.initData,
        initDataUnsafe: tg.initDataUnsafe,
        user: tg.initDataUnsafe?.user
    });
    
    if (tg.initData) {
        // Парсим initData для получения информации о пользователе
        const urlParams = new URLSearchParams(tg.initData);
        const user = tg.initDataUnsafe?.user;
        
        console.log('Парсинг initData:', {
            urlParams: urlParams.toString(),
            user: user
        });
        
        if (user) {
            userData = {
                id: user.id,
                first_name: user.first_name,
                last_name: user.last_name,
                username: user.username,
                language_code: user.language_code
            };
            
            console.log('Создан объект userData:', userData);
            
            // Сохраняем в localStorage для использования на других страницах
            localStorage.setItem('telegramUser', JSON.stringify(userData));
            
            // Отправляем данные на сервер для авторизации
            sendUserDataToServer(userData);
        } else {
            console.log('Пользователь не найден в initDataUnsafe');
        }
    } else {
        console.log('initData отсутствует, пробуем получить из localStorage');
        // Если нет initData, пробуем получить из localStorage
        const savedUser = localStorage.getItem('telegramUser');
        if (savedUser) {
            userData = JSON.parse(savedUser);
            console.log('Получены данные из localStorage:', userData);
            
            // Проверяем, есть ли флаг авторизации
            const isAuth = localStorage.getItem('isAuthenticated');
            console.log('Флаг авторизации:', isAuth);
            
            if (isAuth === 'true') {
                console.log('Пользователь уже авторизован, обновляем интерфейс');
                // Обновляем интерфейс после загрузки данных
                setTimeout(() => {
                    refreshUserData();
                    updateUserInterface();
                }, 100);
            }
        } else {
            console.log('Данные в localStorage отсутствуют');
        }
    }

    // Функция для отправки данных пользователя на сервер
    async function sendUserDataToServer(userData) {
        try {
            console.log('Отправляем данные пользователя на сервер:', userData);
            const response = await fetch('/api/auth/telegram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userData.id,
                    first_name: userData.first_name,
                    last_name: userData.last_name,
                    username: userData.username,
                    language_code: userData.language_code,
                    init_data: tg.initData
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Ответ сервера:', result);
                if (result.success) {
                    console.log('Пользователь авторизован:', result.user_id);
                    // Устанавливаем флаг авторизации
                    localStorage.setItem('isAuthenticated', 'true');
                    
                    // Обновляем userData с сервера
                    if (result.user_id) {
                        userData.id = result.user_id;
                        console.log('Обновлен userData.id:', userData.id);
                        
                        // Пересохраняем в localStorage
                        localStorage.setItem('telegramUser', JSON.stringify(userData));
                        
                        // Обновляем интерфейс
                        updateUserInterface();
                    } else {
                        console.log('user_id не найден в ответе сервера');
                        console.log('Полный ответ сервера:', result);
                        
                        // Пробуем использовать ID из userData, если он есть
                        if (userData && userData.id) {
                            console.log('Используем ID из userData:', userData.id);
                            updateUserInterface();
                        } else {
                            console.log('ID не найден ни в ответе сервера, ни в userData');
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Ошибка авторизации:', error);
        }
    }

    // Функция для проверки авторизации
    function isUserAuthenticated() {
        return localStorage.getItem('isAuthenticated') === 'true';
    }

    // Функция для получения ID пользователя
    function getUserId() {
        if (userData) return userData.id;
        const savedUser = localStorage.getItem('telegramUser');
        return savedUser ? JSON.parse(savedUser).id : null;
    }
    
    // Функция для обновления userData из localStorage
    function refreshUserData() {
        const savedUser = localStorage.getItem('telegramUser');
        if (savedUser) {
            userData = JSON.parse(savedUser);
            console.log('userData обновлен из localStorage:', userData);
        }
    }

    // Показываем информацию о пользователе в интерфейсе
    function updateUserInterface() {
        const userInfo = document.getElementById('userInfo');
        const userName = document.getElementById('userName');
        const logoutBtn = document.getElementById('logoutBtn');
        const adminLink = document.getElementById('adminLink');
        
        console.log('updateUserInterface вызвана с:', {
            userData: userData,
            userInfo: userInfo,
            userName: userName,
            adminLink: adminLink
        });
        
        if (userData && userInfo && userName) {
            const displayName = userData.first_name || userData.username || 'Пользователь';
            userName.textContent = displayName;
            userInfo.style.display = 'block';
            
            // Проверяем, является ли пользователь администратором
            if (adminLink) {
                // ID администраторов (должны совпадать с ADMIN_USER_IDS в app.py)
                const ADMIN_USER_IDS = [1023307031, 631457244];
                const currentId = Number(userData.id);
                console.log('Проверка прав администратора:');
                console.log('ID пользователя:', currentId);
                console.log('ID администраторов:', ADMIN_USER_IDS);
                console.log('Тип ID пользователя:', typeof currentId);
                
                if (ADMIN_USER_IDS.includes(currentId)) {
                    console.log('Пользователь является администратором - показываем кнопку');
                    adminLink.style.display = 'inline-block';
                    
                    // Дополнительная отладка кнопки
                    console.log('Свойства кнопки админ-панели:');
                    console.log('href:', adminLink.href);
                    console.log('display:', adminLink.style.display);
                    console.log('visibility:', adminLink.style.visibility);
                    console.log('opacity:', adminLink.style.opacity);
                    console.log('pointer-events:', adminLink.style.pointerEvents);
                    
                    // Проверяем, что кнопка действительно кликабельна
                    adminLink.style.pointerEvents = 'auto';
                    adminLink.style.cursor = 'pointer';
                    
                } else {
                    console.log('Пользователь НЕ является администратором - скрываем кнопку');
                    adminLink.style.display = 'none';
                }
            } else {
                console.log('Элемент adminLink не найден!');
            }
            
            // Обработчик для кнопки выхода
            if (logoutBtn) {
                logoutBtn.addEventListener('click', async () => {
                    try {
                        const response = await fetch('/api/auth/logout');
                        if (response.ok) {
                            // Очищаем localStorage
                            localStorage.removeItem('telegramUser');
                            localStorage.removeItem('isAuthenticated');
                            
                            // Скрываем информацию о пользователе
                            userInfo.style.display = 'none';
                            
                            // Обновляем состояние
                            userData = null;
                            
                            console.log('Пользователь вышел из системы');
                        }
                    } catch (error) {
                        console.error('Ошибка при выходе:', error);
                    }
                });
            }
            
        }
    }

    // Обработчик для кнопки админ-панели — передаём init_data, чтобы сервер мог создать сессию во фрейме
    if (adminLink) {
        console.log('Настройка обработчика для кнопки админ-панели');
        adminLink.addEventListener('click', function(e) {
            console.log('Клик по кнопке админ-панели');
            const tg = window.Telegram?.WebApp;
            if (tg && tg.initData) {
                const url = '/admin?init_data=' + encodeURIComponent(tg.initData);
                console.log('Переход с init_data:', url);
                window.location.href = url;
            } else {
                console.log('init_data отсутствует, обычный переход на /admin');
                window.location.href = '/admin';
            }
        });
        console.log('Обработчик для кнопки админ-панели установлен');
    }

    // Показать ID-кнопку вместо админ-панели для не-админа
    const idLink = document.getElementById('idLink');
    if (idLink && adminLink) {
        // при обновлении интерфейса уже есть логика определения админа.
        // здесь дублируем: если админ — показываем adminLink, иначе — idLink.
        const showRoleButtons = () => {
            const savedUser = localStorage.getItem('telegramUser');
            const data = savedUser ? JSON.parse(savedUser) : null;
            const ADMIN_USER_IDS = [1023307031, 631457244];
            const isAdmin = !!(data && ADMIN_USER_IDS.includes(Number(data.id)));
            if (isAdmin) {
                adminLink.style.display = 'inline-flex';
                idLink.style.display = 'none';
            } else {
                adminLink.style.display = 'none';
                idLink.style.display = 'inline-flex';
            }
        };
        // вызов сразу и на таймере (на случай поздней авторизации)
        showRoleButtons();
        setTimeout(showRoleButtons, 300);
    }

    // Обновляем интерфейс
    console.log('Вызываем updateUserInterface...');
    console.log('Текущий userData перед вызовом:', userData);
    
    // Обновляем userData из localStorage перед обновлением интерфейса
    refreshUserData();
    
    updateUserInterface();

    const menuBtn = document.getElementById('menuBtn');
    const sideMenu = document.getElementById('sideMenu');
    const menuOverlay = document.getElementById('menuOverlay');
    const cartBtn = document.getElementById('cartBtn');
    // элементы каталога (главная) — больше не используются (переход на /gender)
    const openCatalogBtn = null;
    const catalogSheet = null;
    const catalogOverlay = null;
    const catalogClose = null;
    const catalogList = null;

    function openMenu() {
        if (!sideMenu || !menuOverlay) return;
        sideMenu.classList.add('open');
        menuOverlay.classList.add('show');
    }

    function closeMenu() {
        if (!sideMenu || !menuOverlay) return;
        sideMenu.classList.remove('open');
        menuOverlay.classList.remove('show');
    }

    if (menuBtn) menuBtn.addEventListener('click', openMenu);
    if (menuOverlay) menuOverlay.addEventListener('click', closeMenu);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMenu();
    });

    if (cartBtn) {
        cartBtn.addEventListener('click', () => {
            if (isUserAuthenticated()) {
                alert('Корзина в разработке');
            } else {
                alert('Необходимо авторизоваться');
            }
        });
    }

    // Раньше здесь был локальный bottom-sheet каталога. Теперь ссылка ведёт на /gender.
    
    // Функция для отслеживания активности пользователя
    function trackUserActivity(action) {
        const userId = getUserId();
        if (!userId) return;
        
        const userData = JSON.parse(localStorage.getItem('telegramUser') || '{}');
        
        fetch('/api/admin/user-activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                action: action,
                first_name: userData.first_name || '',
                last_name: userData.last_name || '',
                username: userData.username || ''
            })
        }).catch(error => {
            console.error('Ошибка отслеживания активности:', error);
        });
    }

    // Отслеживаем основные действия пользователя
    trackUserActivity('Загрузка страницы');
    
    // Отслеживаем клики по кнопкам
    document.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            const buttonText = e.target.textContent || e.target.closest('button')?.textContent || 'Клик по кнопке';
            trackUserActivity(`Клик: ${buttonText}`);
        }
    });

    // Экспортируем функции для использования в других скриптах
    window.TelegramAuth = {
        isUserAuthenticated,
        getUserId,
        userData,
        trackUserActivity
    };
});

