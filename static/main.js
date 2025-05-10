ymaps.ready(() => {
    const map = new ymaps.Map('map', {
        center: [51.672046, 39.184302], // Координаты центра Воронежа
        zoom: 12
    });

    const placemark = new ymaps.Placemark([51.672046, 39.184302], {
        balloonContent: 'Пример метки'
    });
    map.geoObjects.add(placemark);
});