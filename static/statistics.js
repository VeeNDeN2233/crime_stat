document.addEventListener('DOMContentLoaded', () => {
    // Пример данных (замените их на реальные данные из базы)
    const crimeByDayData = {
        labels: ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
        data: [12, 19, 3, 5, 2, 3, 10] // Пример количества преступлений
    };

    const crimeByArticleData = {
        labels: ['Статья 115 УК РФ', 'Статья 158 УК РФ', 'Статья 161 УК РФ'],
        data: [20, 15, 10] // Пример количества преступлений
    };

    const crimeByDepartmentData = {
        labels: ['Отдел №1', 'Отдел №2', 'Отдел №3'],
        data: [25, 15, 10] // Пример количества преступлений
    };

    // Диаграмма 1: По дням недели
    const ctx1 = document.getElementById('crimeByDayChart').getContext('2d');
    new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: crimeByDayData.labels,
            datasets: [{
                label: 'Количество преступлений',
                data: crimeByDayData.data,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Диаграмма 2: По статьям УК РФ
    const ctx2 = document.getElementById('crimeByArticleChart').getContext('2d');
    new Chart(ctx2, {
        type: 'pie',
        data: {
            labels: crimeByArticleData.labels,
            datasets: [{
                label: 'Количество преступлений',
                data: crimeByArticleData.data,
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56'],
                hoverOffset: 4
            }]
        }
    });

    // Диаграмма 3: По отделам полиции
    const ctx3 = document.getElementById('crimeByDepartmentChart').getContext('2d');
    new Chart(ctx3, {
        type: 'line',
        data: {
            labels: crimeByDepartmentData.labels,
            datasets: [{
                label: 'Количество преступлений',
                data: crimeByDepartmentData.data,
                fill: false,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});