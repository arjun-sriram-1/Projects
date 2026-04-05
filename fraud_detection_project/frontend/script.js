let chart;

// PREDICT FUNCTION
async function predict() {
    const amount = document.getElementById('amount').value;
    const oldbalance = document.getElementById('oldbalance').value;
    const newbalance = document.getElementById('newbalance').value;

    const response = await fetch('http://127.0.0.1:5000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, oldbalance, newbalance })
    });

    const data = await response.json();

    document.getElementById('result').innerText =
        "Result: " + data.prediction + " | Risk: " + data.risk + "%";

    loadStats();
    loadHistory();
    loadTopTransactions();
}

// LOAD STATS
async function loadStats() {
    const res = await fetch('http://127.0.0.1:5000/stats');
    const data = await res.json();

    document.getElementById('total').innerText = data.total;
    document.getElementById('fraud').innerText = data.fraud;
    document.getElementById('legit').innerText = data.legit;

    let rate = data.total > 0 ? ((data.fraud / data.total) * 100).toFixed(2) : 0;
    document.getElementById('rate').innerText = rate + "%";

    const ctx = document.getElementById('chart').getContext('2d');

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Fraud', 'Not Fraud'],
            datasets: [{
                data: [data.fraud, data.legit],
                backgroundColor: ['#ef4444', '#22c55e']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// LOAD HISTORY
async function loadHistory() {
    const res = await fetch('http://127.0.0.1:5000/transactions');
    const data = await res.json();

    const table = document.getElementById('historyTable');
    table.innerHTML = `
        <tr>
            <th>ID</th>
            <th>Amount</th>
            <th>Old</th>
            <th>New</th>
            <th>Status</th>
            <th>Risk %</th>
        </tr>
    `;

    data.forEach(row => {
        table.innerHTML += `
            <tr>
                <td>${row.id}</td>
                <td>${row.amount}</td>
                <td>${row.oldbalance}</td>
                <td>${row.newbalance}</td>
                <td>${row.prediction}</td>
                <td>${row.risk}</td>
            </tr>
        `;
    });
}

// LOAD TOP RISKY
async function loadTopTransactions() {
    const res = await fetch('http://127.0.0.1:5000/top-transactions');
    const data = await res.json();

    const table = document.getElementById('topTable');
    table.innerHTML = `
        <tr>
            <th>ID</th>
            <th>Amount</th>
            <th>Risk %</th>
        </tr>
    `;

    data.forEach(row => {
        table.innerHTML += `
            <tr>
                <td>${row.id}</td>
                <td>${row.amount}</td>
                <td>${row.risk}</td>
            </tr>
        `;
    });
}

// LOAD EVERYTHING
loadStats();
loadHistory();
loadTopTransactions();